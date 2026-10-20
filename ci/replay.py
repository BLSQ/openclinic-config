"""The replay on the release candidate (the spec, §7): every stack of the repository applied twice
to a fresh database of the pinned image, as the chart would apply it, and exported against itself
in between when the image has `config export` (the round trip, §7.4)."""
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

from . import docker, repo as repo_mod, stacks as stacks_mod
from .semver import Range, Version

MARIADB = os.environ.get("OC_REPLAY_MARIADB", "mariadb:11.8")
APP_USER = """CREATE USER IF NOT EXISTS 'openclinic'@'%' IDENTIFIED BY '0pen';
GRANT ALL PRIVILEGES ON `ocadmin_dbo`.* TO 'openclinic'@'%';
GRANT ALL PRIVILEGES ON `openclinic_dbo`.* TO 'openclinic'@'%';
GRANT ALL PRIVILEGES ON `ocstats_dbo`.* TO 'openclinic'@'%';
GRANT ALL PRIVILEGES ON `ikirezi`.* TO 'openclinic'@'%';
FLUSH PRIVILEGES;
"""
SEED = "/opt/openclinic/seed/openclinic.sql.gz"


def slug(name):
    return re.sub(r"[^a-z0-9.-]+", "-", name.lower()).strip("-")


class Database:
    """A MariaDB server on a network of its own, its data in a volume, and a snapshot volume taken
    once the seed is loaded and migrated (the spec, §7.1)."""

    def __init__(self, image, work):
        self.image, self.work = image, work
        tag = f"ocreplay-{os.getpid()}"
        self.network, self.container = tag, tag + "-db"
        self.data, self.snapshot = tag + "-data", tag + "-snapshot"

    def _sql_ready(self, query):
        r = docker.run(["exec", self.container, "mariadb", "-h", "127.0.0.1", "-uroot", "-proot", "-N", "-e", query],
                       check=False, capture=True, quiet=True)
        return r.returncode == 0

    def _wait(self, query, seconds, what):
        deadline = time.time() + seconds
        while time.time() < deadline:
            if self._sql_ready(query):
                return
            state = docker.run(["inspect", "-f", "{{.State.Running}}", self.container], check=False, capture=True, quiet=True).stdout.strip()
            if state == "false":
                break
            time.sleep(2)
        logs = docker.run(["logs", "--tail", "40", self.container], check=False, capture=True, quiet=True)
        raise RuntimeError(f"the database did not become ready ({what}):\n{logs.stdout}{logs.stderr}")

    def create(self):
        initdb = os.path.join(self.work, "initdb")
        os.makedirs(initdb)
        with open(os.path.join(initdb, "00-create-app-user.sql"), "w") as f:
            f.write(APP_USER)
        with open(os.path.join(initdb, "01-seed.sql.gz"), "wb") as f:
            subprocess.run(["docker", "run", "--rm", "--entrypoint", "cat", self.image, SEED], stdout=f, check=True)
        stacks_mod.readable(initdb)
        docker.run(["network", "create", self.network], capture=True)
        docker.run(["volume", "create", self.data], capture=True)
        docker.run(["volume", "create", self.snapshot], capture=True)
        docker.run(["run", "-d", "--name", self.container, "--network", self.network, "--network-alias", "db",
                    "-e", "MARIADB_ROOT_PASSWORD=root", "-v", f"{self.data}:/var/lib/mysql",
                    "-v", f"{initdb}:/docker-entrypoint-initdb.d:ro", MARIADB,
                    "--lower-case-table-names=1", "--sql-mode=ANSI", "--max-connections=1000"], capture=True)
        self._wait("SELECT 1 FROM ocadmin_dbo.users LIMIT 1", 900, "the seed loading")
        r = docker.run(["run", "--rm", "--network", self.network] + self.env() + [self.image, "migrate"],
                       check=False, capture=True)
        if r.returncode != 0:
            raise RuntimeError(f"migrate failed:\n{r.stdout[-4000:]}{r.stderr[-4000:]}")
        docker.run(["stop", "-t", "60", self.container], capture=True)
        self._copy(self.data, self.snapshot)

    def env(self):
        return ["-e", "DB_HOST=db", "-e", "DB_USER=openclinic", "-e", "DB_PASSWORD=0pen"]

    def _copy(self, src, dst):
        docker.run(["run", "--rm", "--entrypoint", "sh", "-v", f"{src}:/from", "-v", f"{dst}:/to", MARIADB, "-c",
                    "find /to -mindepth 1 -delete && cp -a /from/. /to/"], capture=True, quiet=True)

    def fresh(self):
        """The server started on a copy of the snapshot."""
        self._copy(self.snapshot, self.data)
        docker.run(["start", self.container], capture=True, quiet=True)
        self._wait("SELECT 1 FROM openclinic_dbo.oc_config_packages LIMIT 1", 300, "a restart on the snapshot")

    def stop(self):
        docker.run(["stop", "-t", "60", self.container], check=False, capture=True, quiet=True)

    def destroy(self):
        docker.run(["rm", "-f", self.container], check=False, capture=True, quiet=True)
        docker.run(["volume", "rm", "-f", self.data, self.snapshot], check=False, capture=True, quiet=True)
        docker.run(["network", "rm", self.network], check=False, capture=True, quiet=True)


def outcome(report_file):
    try:
        with open(report_file, encoding="utf-8") as f:
            report = json.load(f)
    except (OSError, ValueError):
        return None, {}
    return report.get("run", {}).get("outcome"), report


def explain(report):
    lines = [f"    {report.get('run', {}).get('message') or ''}".rstrip()]
    for p in report.get("problems", [])[:20]:
        lines.append(f"    {p.get('package')} {p.get('file')} {p.get('path')}: {p.get('message')}")
    written = {k: v for k, v in (report.get("written") or {}).items() if v}
    if written:
        lines.append(f"    written: {written}")
    return "\n".join(l for l in lines if l.strip())


def export_available(returncode, output):
    """`config export` with no option is a usage error (exit 2) on an image that has it, and an
    unknown command on one built before SP4, which exits 2 too (the spec, §7.4)."""
    return returncode == 2 and "unknown command" not in output


def has_export(image):
    r = docker.run(["run", "--rm", "-e", "DB_HOST=db", "-e", "DB_USER=openclinic", "-e", "DB_PASSWORD=0pen",
                    image, "config", "export"], check=False, capture=True, quiet=True)
    docker.check_config_command(image, r)
    return export_available(r.returncode, r.stdout + r.stderr)


def probe_name(stack):
    """The name the round trip exports under: a site package's, and one the stack does not hold,
    since an export leaves the package of its own name out of the reference."""
    names = {p.name for p in stack.packages()}
    return next(n for n in ("round-trip" + (f"-{i}" if i else "") for i in itertools.count()) if n not in names)


def round_trip_verdict(returncode, report, exported_dir):
    """@return None when the export of a stack against itself gave nothing back, or why it did.
    What it names for a reason of its own (a seed's codeless row, a half-on module) is not the
    stack's doing; a value another level set and the database does not hold is."""
    got = report.get("run", {}).get("outcome")
    if returncode != 0 or got != "written":
        return f"the round trip: config export exit {returncode}, outcome {got}, expected exit 0 and written\n{explain(report)}"
    files = (report.get("package") or {}).get("files") or {}
    disagree = [n for n in report.get("named") or [] if n.get("reason") == "another level"]
    if not files and not disagree:
        return None
    lines = ["the round trip: the stack exported against itself is not empty: the database holds what the stack does not say"]
    for name, count in sorted(files.items()):
        lines.append(f"    {name}: {count} element(s)")
        try:
            with open(os.path.join(exported_dir, name), encoding="utf-8", errors="replace") as f:
                content = f.read().splitlines()
        except OSError:
            continue
        lines += [f"      {l}" for l in content[:20]] + ([f"      … {len(content) - 20} more line(s)"] if len(content) > 20 else [])
    for n in disagree[:20]:
        lines.append(f"    {n.get('kind')} {n.get('element')} {n.get('field')}: the database holds '{n.get('value')}' — {n.get('detail')}")
    return "\n".join(lines)


def round_trip(db, image, version, stage, reports, stack):
    """The spec's §7.4: after the first run, `config export` of the stack against itself, which must
    give back nothing: what the packages say came back unchanged."""
    probe = probe_name(stack)
    # created here, open to every user: the container (uid 1000, umask 077) would create them 0700,
    # which the runner, another uid, can neither copy with --keep nor delete; inside a directory the
    # runner owns, the tool's chmod fails quietly and the files it writes stay removable
    exported = os.path.join(reports, "round-trip", probe)
    os.makedirs(exported)
    for d in (os.path.dirname(exported), exported):
        os.chmod(d, 0o777)
    r = docker.run(["run", "--rm", "--network", db.network] + db.env()
                   + ["-e", f"OPENCLINIC_VERSION={version}", "-v", f"{stage}:/packages:ro", "-v", f"{reports}:/report",
                      image, "config", "export", "--name", probe, "--level", "site", "--version", "0.0.0",
                      "--out", "/report/round-trip", "--report", "/report/round-trip.json", "/packages"],
                   check=False, capture=True, quiet=True)
    with open(os.path.join(reports, "round-trip.log"), "w") as f:
        f.write(r.stdout + r.stderr)
    _, report = outcome(os.path.join(reports, "round-trip.json"))
    return round_trip_verdict(r.returncode, report, exported)


def apply_twice(db, image, version, root, stack, out, index=0, export=False):
    """@return None when the stack passes, or why it fails. With `export`, the round trip runs
    between the two runs."""
    work = tempfile.mkdtemp(prefix="stack-", dir=db.work)
    stage, reports = os.path.join(work, "packages"), os.path.join(work, "reports")
    stacks_mod.stage(root, stack, stage)
    os.makedirs(reports)
    # writable by the container's uid 1000; no sticky bit, or the runner, another uid, could not
    # delete the reports the container wrote when the work directory is cleaned up
    os.chmod(reports, 0o777)
    db.fresh()
    try:
        for run, expected in (("first", "applied"), ("second", "unchanged")):
            r = docker.run(["run", "--rm", "--network", db.network] + db.env()
                           + ["-e", f"OPENCLINIC_VERSION={version}", "-v", f"{stage}:/packages:ro", "-v", f"{reports}:/report",
                              image, "config", "apply", "--report", f"/report/{run}.json", "/packages"],
                           check=False, capture=True, quiet=True)
            docker.check_config_command(image, r)
            with open(os.path.join(reports, f"{run}.log"), "w") as f:
                f.write(r.stdout + r.stderr)
            got, report = outcome(os.path.join(reports, f"{run}.json"))
            if r.returncode != 0 or got != expected:
                return f"the {run} run: exit {r.returncode}, outcome {got}, expected exit 0 and {expected}\n{explain(report)}"
            if run == "second" and any((report.get("written") or {}).values()):
                return f"the second run wrote fields: {report.get('written')}\n{explain(report)}"
            if run == "first" and export:
                why = round_trip(db, image, version, stage, reports, stack)
                if why:
                    return why
        return None
    finally:
        db.stop()
        if out:
            shutil.copytree(reports, os.path.join(out, f"{index:02d}-{slug(stack.name)}"), dirs_exist_ok=True)


def run(root, image, keep=None):
    r = repo_mod.load(root)
    if r.problems:
        for p in r.problems:
            print(p.line(), file=sys.stderr)
        return 1
    if not r.packages:
        print("replay: no package in the repository, nothing to replay")
        return 0
    docker.ensure(image)
    candidate = docker.env_of(image).get("OPENCLINIC_VERSION")
    if not candidate:
        print(f"replay: the image {image} sets no OPENCLINIC_VERSION", file=sys.stderr)
        return 1
    release = Version.parse(candidate).release()
    # the spec's §7.3: requires is checked against the release the candidate becomes
    eligible, waiting = {}, []
    for p in r.packages:
        try:
            ok = p.requires is None or Range.parse(p.requires).includes(release)
        except ValueError:
            ok = True    # missing or malformed: config apply refuses it, with its own words
        eligible[p.name] = ok
        if not ok:
            waiting.append(f"{p.name} {p.version_text} requires {p.requires}: not replayed on {release} (candidate {candidate})")
    planned = [s.restrict(lambda p: eligible[p.name]) for s in stacks_mod.plan(r)]
    planned = [s for s in planned if s is not None]
    for w in waiting:
        print("replay: " + w)
    if not planned:
        print(f"replay: no stack to replay on {image}")
        return 0
    print(f"replay: {len(planned)} stack(s) on {image}, requires checked against {release}")
    export = has_export(image)
    print("replay: the round trip, every stack exported against itself after its first run" if export
          else f"replay: the round trip awaits a release with config export (SP4): {image} has none")
    failures = 0
    with tempfile.TemporaryDirectory(prefix="openclinic-config-replay-", ignore_cleanup_errors=True) as work:
        os.chmod(work, 0o755)
        db = Database(image, work)
        try:
            started = time.time()
            db.create()
            print(f"replay: the seed loaded and migrated in {time.time() - started:.0f} s")
            for i, s in enumerate(planned, 1):
                t = time.time()
                why = apply_twice(db, image, str(release), root, s, keep, i, export)
                status = "ok" if why is None else "FAILED"
                print(f"replay: {status:6} {s.name}  [{s.describe()}]  {time.time() - t:.0f} s")
                if why:
                    failures += 1
                    print(why)
        finally:
            db.destroy()
    print(f"replay: {len(planned)} stack(s), {failures} failed")
    return 1 if failures else 0
