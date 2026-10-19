"""Publishing (the spec, §8): each package whose tag the registry lacks, built `FROM scratch` (a
type `FROM` its country at the repository's version), amd64 and arm64, reproducible, then read
back anonymously. A tag that exists is never pushed again; one whose content or base differs from
the repository refuses the whole run before anything is built (T2, T3)."""
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

from . import repo as repo_mod
from .registry import Registry, Unknown
from .stacks import readable

LABEL_HASH = "be.openclinic.package.contenthash"
LABEL_BASE = "be.openclinic.package.base"
SOURCE = os.environ.get("OC_SOURCE_URL", "https://github.com/BLSQ/openclinic-config")
PLATFORMS = "linux/amd64,linux/arm64"


@dataclass
class Action:
    package: object
    what: str            # skip, build, refuse
    reason: str = ""
    base: str = None     # a type's country, name:version

    def line(self):
        return f"{self.what:7} {self.package.name}:{self.package.version_text}" + (f"  {self.reason}" if self.reason else "")


def order(repo):
    rank = {"country": 0, "type": 1}
    return sorted(repo.packages, key=lambda p: (rank.get(p.level, 2), p.name))


def expected_base(repo, pkg):
    if pkg.level != "type":
        return None
    country = repo.by_name(pkg.base)
    return f"{country.name}:{country.version_text}" if country else None


def published(registry, namespace, pkg):
    """@return the labels of the package's published tag, or None when the tag is not published.
    An anonymous caller that cannot tell gets None too, and is told."""
    ref = f"{namespace}/{pkg.name}"
    try:
        if not registry.exists(ref, pkg.version_text):
            return None
    except Unknown as e:
        print(f"note: {e}; taken as not published", file=sys.stderr)
        return None
    return registry.labels(ref, pkg.version_text)


def differs(repo, pkg, labels):
    """Why a published tag is not this package, or None (T1, T2, T3)."""
    h = pkg.content_hash()
    if labels.get(LABEL_HASH) != h:
        return (f"T2 the tag {pkg.name}:{pkg.version_text} is published with other content "
                f"({labels.get(LABEL_HASH) or 'no content hash'}, the repository's is {h}): a new version gets a new tag")
    base = expected_base(repo, pkg)
    if base and labels.get(LABEL_BASE) != base:
        return (f"T3 the tag {pkg.name}:{pkg.version_text} is published on {labels.get(LABEL_BASE)}, and its country "
                f"is {base} in the repository: a type moves with its country (V3)")
    return None


def plan(repo, registry, namespace):
    actions = []
    for pkg in order(repo):
        labels = published(registry, namespace, pkg)
        if labels is None:
            actions.append(Action(pkg, "build", base=expected_base(repo, pkg)))
            continue
        why = differs(repo, pkg, labels)
        actions.append(Action(pkg, "refuse", why) if why else Action(pkg, "skip", "published"))
    return actions


def dockerfile(base_image):
    return "\n".join([f"FROM {base_image}" if base_image else "FROM scratch", "ARG NAME", "COPY ${NAME}/ /${NAME}/", ""])


def build(root, action, host, namespace, revision):
    pkg = action.package
    image = f"{host}/{namespace}/{pkg.name}:{pkg.version_text}"
    base_image = f"{host}/{namespace}/{action.base}" if action.base else None
    labels = {
        "org.opencontainers.image.title": pkg.name,
        "org.opencontainers.image.version": pkg.version_text,
        "org.opencontainers.image.description": pkg.title,
        "org.opencontainers.image.source": SOURCE,
        "org.opencontainers.image.revision": revision,
        "be.openclinic.package.name": pkg.name,
        "be.openclinic.package.level": pkg.level,
        LABEL_HASH: pkg.content_hash(),
    }
    if action.base:
        labels[LABEL_BASE] = action.base
    with tempfile.TemporaryDirectory(prefix="openclinic-config-image-") as ctx:
        shutil.copytree(os.path.join(root, pkg.rel), os.path.join(ctx, pkg.name))
        readable(ctx)
        with open(os.path.join(ctx, "Dockerfile"), "w") as f:
            f.write(dockerfile(base_image))
        cmd = ["docker", "buildx", "build", "--platform", PLATFORMS, "--provenance=false", "--sbom=false",
               "--build-arg", f"NAME={pkg.name}",
               "--output", f"type=image,name={image},push=true,rewrite-timestamp=true"]
        for k, v in labels.items():
            cmd += ["--label", f"{k}={v}"]
        cmd.append(ctx)
        print("+ " + " ".join(cmd), file=sys.stderr, flush=True)
        subprocess.run(cmd, check=True, env=dict(os.environ, SOURCE_DATE_EPOCH="0"))
    return image


def revision(root):
    r = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def registry_from(args):
    return Registry(args.registry, user=os.environ.get("REGISTRY_USER") or "x",
                    password=os.environ.get("REGISTRY_TOKEN"), insecure=args.insecure)


def main(root, args):
    repo = repo_mod.load(root)
    if repo.problems:
        for p in repo.problems:
            print(p.line(), file=sys.stderr)
        return 1
    registry = registry_from(args)
    actions = plan(repo, registry, args.namespace)
    for a in actions:
        print("publish: " + a.line())
    refused = [a for a in actions if a.what == "refuse"]
    if refused:
        print(f"publish: {len(refused)} package(s) refused; nothing is built", file=sys.stderr)
        return 1
    if args.dry_run:
        return 0
    rev = revision(root)
    private = []
    for a in actions:
        if a.what != "build":
            continue
        build(root, a, args.registry, args.namespace, rev)
        ref = f"{args.namespace}/{a.package.name}"
        registry.forget(ref)
        why = differs(repo, a.package, registry.labels(ref, a.package.version_text))
        if why:
            print(f"publish: {a.package.name}: pushed, and reads back wrong: {why}", file=sys.stderr)
            return 1
    # every package, the ones published by an earlier run included: a run that failed here once must
    # not pass the next time because the tag now exists
    for a in actions:
        if not args.no_public_check and not registry.anonymous_pull(f"{args.namespace}/{a.package.name}", a.package.version_text):
            private.append(a.package.name)
    if private:
        print("publish: pushed, and not pullable without a token, which is how every site pulls: "
              + ", ".join(private) + ". Make each package public on ghcr.io (the package's settings, "
              "'Change visibility'), once per package; the next run passes.", file=sys.stderr)
        return 1
    return 0
