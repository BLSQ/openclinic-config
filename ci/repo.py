"""A checkout of the packages repository, read as packages: where each lives, its six manifest
fields, its files and its content hash. Nothing else of a package is read here (the spec, §3)."""
import hashlib
import os
from dataclasses import dataclass, field

import yaml

from .semver import Version

MANIFEST = "package.yaml"
COUNTRIES = "countries"
SHARED = "shared"
# What is not searched for packages: git's own directory, and the tooling's fixtures (L1).
NOT_PACKAGES = (".git", "ci/tests")


@dataclass
class Problem:
    rule: str
    path: str
    message: str

    def line(self):
        return f"{self.rule} {self.path}: {self.message}"


@dataclass
class Package:
    name: str
    rel: str                      # its directory, relative to the repository, with '/'
    level: str
    version_text: str
    title: str = ""
    base: str = None
    country: str = None
    requires: str = None
    files: dict = field(default_factory=dict)   # relative path -> bytes

    @property
    def version(self):
        return Version.parse(self.version_text)

    @property
    def parts(self):
        return self.rel.split("/")

    @property
    def owner_country(self):
        """The country directory it lives under, or None under shared/."""
        p = self.parts
        return p[1] if len(p) == 3 and p[0] == COUNTRIES else None

    def content_hash(self):
        return content_hash(self.files)

    def __str__(self):
        return f"{self.name} {self.version_text} ({self.level})"


def content_hash(files):
    """`config apply`'s content hash (OpenClinic's PackageReader.contentHash): SHA-256 over the
    files in path order, each its path in UTF-8, a NUL, its bytes, a NUL. The paths are ordered as
    Java's String.compareTo orders them, by UTF-16 code unit."""
    sha = hashlib.sha256()
    for path in sorted(files, key=lambda p: p.encode("utf-16-be")):
        sha.update(path.encode("utf-8"))
        sha.update(b"\0")
        sha.update(files[path])
        sha.update(b"\0")
    return sha.hexdigest()


@dataclass
class Repo:
    root: str
    packages: list = field(default_factory=list)
    problems: list = field(default_factory=list)   # manifests that could not be read

    def by_name(self, name):
        for p in self.packages:
            if p.name == name:
                return p
        return None

    def countries(self):
        return [p for p in self.packages if p.level == "country"]

    def types_of(self, country):
        return [p for p in self.packages if p.level == "type" and p.base == country]


def _read_files(directory):
    files = {}
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames.sort()
        for d in dirnames:
            if os.path.islink(os.path.join(dirpath, d)):
                raise ValueError(f"{os.path.relpath(os.path.join(dirpath, d), directory)} is a symbolic link: a package holds files only")
        for f in sorted(filenames):
            full = os.path.join(dirpath, f)
            if os.path.islink(full):
                # config apply and the image would follow it, this hash would not; and it may point outside
                raise ValueError(f"{os.path.relpath(full, directory)} is a symbolic link: a package holds files only")
            if os.path.isfile(full):
                rel = os.path.relpath(full, directory).replace(os.sep, "/")
                with open(full, "rb") as fh:
                    files[rel] = fh.read()
    return files


def _text(doc, key):
    v = doc.get(key)
    return v if isinstance(v, str) and v else None


def read_package(root, rel):
    """One package directory; raises ValueError naming what is unreadable."""
    directory = os.path.join(root, rel)
    with open(os.path.join(directory, MANIFEST), "rb") as fh:
        try:
            doc = yaml.safe_load(fh)
        except yaml.YAMLError as e:
            raise ValueError(f"not readable as YAML: {e}".replace("\n", " "))
    if not isinstance(doc, dict):
        raise ValueError("the manifest is not a mapping")
    missing = [k for k in ("name", "version", "level") if not _text(doc, k)]
    if missing:
        raise ValueError("the manifest lacks " + ", ".join(missing))
    try:
        Version.parse(doc["version"])
    except ValueError as e:
        raise ValueError(str(e))
    requires = doc.get("requires")
    return Package(
        name=doc["name"], rel=rel, level=doc["level"], version_text=doc["version"],
        title=_text(doc, "title") or "", base=_text(doc, "base"), country=_text(doc, "country"),
        requires=requires.get("openclinic") if isinstance(requires, dict) else None,
        files=_read_files(directory))


def manifests(root):
    """Every package.yaml of the checkout, relative paths of their directories, fixtures excepted."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        dirnames[:] = sorted(d for d in dirnames
                             if (d if rel == "." else f"{rel}/{d}") not in NOT_PACKAGES)
        if rel == ".":
            continue
        if MANIFEST in filenames:
            found.append(rel)
    return sorted(found)


def load(root):
    repo = Repo(root=root)
    for rel in manifests(root):
        try:
            repo.packages.append(read_package(root, rel))
        except (ValueError, OSError) as e:
            repo.problems.append(Problem("L0", rel + "/" + MANIFEST, f"{e}; config lint says more"))
    return repo
