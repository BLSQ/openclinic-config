"""The version rules V1 to V5 (the spec, §5.1): a pull request against its base branch, package by
package, by name. A package's content is its files, byte for byte."""
import atexit
import io
import shutil
import subprocess
import tarfile
import tempfile

from . import repo as repo_mod
from .repo import Problem


def compare(base, head):
    """@return (problems, notes): the refusals, and what a reader of the pull request should know."""
    problems, notes = [], []
    for p in head.packages:
        where = p.rel + "/package.yaml"
        before = base.by_name(p.name)
        if before is None:
            notes.append(f"{p.name}: new, {p.version_text}")
            continue
        try:
            new, old = p.version, before.version
        except ValueError:
            continue   # unreadable: the layout's problem already
        changed = p.files != before.files
        if new == old:
            if changed:
                problems.append(Problem("V1", where, f"its files changed and its version is still {p.version_text}: "
                                        f"the tag {p.name}:{p.version_text} is published, a new version gets a new tag"))
            continue
        if new < old:
            problems.append(Problem("V2", where, f"its version goes down, from {before.version_text} to {p.version_text}"))
            continue
        notes.append(f"{p.name}: {before.version_text} -> {p.version_text}")
    # V3: a country that moves makes each of its types move (the type's image holds its country)
    for country in head.countries():
        before = base.by_name(country.name)
        if before is None or before.level != "country" or before.version_text == country.version_text:
            continue
        for t in head.types_of(country.name):
            tb = base.by_name(t.name)
            if tb is not None and tb.version_text == t.version_text:
                problems.append(Problem("V3", t.rel + "/package.yaml",
                                        f"its country {country.name} moves from {before.version_text} to {country.version_text}, "
                                        f"and the type stays at {t.version_text}: its image holds its country, so the type "
                                        f"takes a new version in the same pull request"))
    # V4, V5: removals are said, never refused; a rename is a removal and an addition
    for p in base.packages:
        if head.by_name(p.name) is None:
            notes.append(f"{p.name}: removed from the repository; its published tags stay, up to {p.version_text}")
    return problems, notes


def load_ref(git_dir, ref):
    """The repository as it stands at a git ref, read from `git archive` into a temporary directory."""
    tar = subprocess.run(["git", "-C", git_dir, "archive", "--format=tar", ref],
                         check=True, capture_output=True).stdout
    tmp = tempfile.mkdtemp(prefix="openclinic-config-base-")
    atexit.register(shutil.rmtree, tmp, True)
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        try:
            t.extractall(tmp, filter="data")
        except TypeError:   # a Python without extraction filters (before 3.12)
            t.extractall(tmp)
    return repo_mod.load(tmp)
