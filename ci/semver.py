"""Semantic versions and `requires.openclinic` ranges, as `config apply` reads them.

The same grammar and precedence as OpenClinic's `tools/config` (`Version`, `VersionRange`): a
release is above its pre-releases, numeric identifiers come before alphanumeric ones, and
`0.0.0-dev` is in every range.
"""
import re
from functools import total_ordering

_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z.-]+))?$")
_RANGE = re.compile(r"^>=(\S+)(?:\s+<(\S+))?$")


@total_ordering
class Version:
    __slots__ = ("major", "minor", "patch", "pre")

    def __init__(self, major, minor, patch, pre=()):
        self.major, self.minor, self.patch, self.pre = major, minor, patch, tuple(pre)

    @classmethod
    def parse(cls, text):
        m = _SEMVER.match(text.strip() if isinstance(text, str) else "")
        if not m:
            raise ValueError(f"'{text}' is not a semantic version (MAJOR.MINOR.PATCH, optionally -pre.release)")
        pre = tuple(m.group(4).split(".")) if m.group(4) else ()
        if any(p == "" for p in pre):
            raise ValueError(f"'{text}' has an empty pre-release identifier")
        return cls(int(m.group(1)), int(m.group(2)), int(m.group(3)), pre)

    def release(self):
        """The release this version precedes or is: its pre-release part dropped."""
        return Version(self.major, self.minor, self.patch)

    def is_dev(self):
        return self == DEV

    def _key(self):
        return (self.major, self.minor, self.patch)

    def __eq__(self, other):
        return isinstance(other, Version) and self._key() == other._key() and self.pre == other.pre

    def __hash__(self):
        return hash((self._key(), self.pre))

    def __lt__(self, other):
        if self._key() != other._key():
            return self._key() < other._key()
        if not self.pre or not other.pre:
            # a release is above any of its pre-releases
            return bool(self.pre) and not other.pre
        for a, b in zip(self.pre, other.pre):
            if a == b:
                continue
            an, bn = a.isdigit(), b.isdigit()
            if an and bn:
                return int(a) < int(b)
            if an != bn:
                return an   # numeric identifiers come before alphanumeric ones
            return a < b
        return len(self.pre) < len(other.pre)

    def __str__(self):
        s = f"{self.major}.{self.minor}.{self.patch}"
        return s + ("-" + ".".join(self.pre) if self.pre else "")

    __repr__ = __str__


DEV = Version(0, 0, 0, ("dev",))


class Range:
    """`>=X.Y.Z`, optionally followed by ` <X.Y.Z`; the upper bound is exclusive."""

    def __init__(self, low, below=None):
        self.low, self.below = low, below

    @classmethod
    def parse(cls, text):
        m = _RANGE.match(text.strip() if isinstance(text, str) else "")
        if not m:
            raise ValueError(f"'{text}' is not a version range: '>=X.Y.Z', optionally followed by ' <X.Y.Z'")
        low = Version.parse(m.group(1))
        below = Version.parse(m.group(2)) if m.group(2) else None
        if below is not None and below <= low:
            raise ValueError(f"'{text}' is empty: the upper bound is not above the lower one")
        return cls(low, below)

    def includes(self, version):
        if version.is_dev():
            return True
        return version >= self.low and (self.below is None or version < self.below)

    def __str__(self):
        return f">={self.low}" + (f" <{self.below}" if self.below else "")
