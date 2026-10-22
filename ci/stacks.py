"""The stacks the replay mounts (the spec, §7.2): every package in the smallest stack a site could
receive it in, and every base once more with all its layers. A stack is a list of ranks, each a
list of packages, mounted as the chart mounts them: `<dir>/<rank>/<package>/`."""
import os
import shutil
import stat
from dataclasses import dataclass


@dataclass
class Stack:
    name: str
    ranks: list            # [[Package]]
    target: object = None  # the package the stack exists for; None for a wide stack

    def packages(self):
        return [p for rank in self.ranks for p in rank]

    def restrict(self, eligible):
        """The stack without the packages `eligible` refuses, or None when what it tests is gone:
        a base, a project or a site refused, or a wide stack left with no layer."""
        bases = self.ranks[0]
        if any(not eligible(p) for p in bases) or (self.target is not None and not eligible(self.target)):
            return None
        rest = [[p for p in rank if eligible(p)] for rank in self.ranks[1:]]
        rest = [r for r in rest if r]
        if self.target is None and len(self.ranks) > 1 and not rest:
            return None
        return Stack(self.name, [bases] + rest, self.target)

    def describe(self):
        return " | ".join(" + ".join(p.name for p in rank) for rank in self.ranks)


def plan(repo):
    stacks = []
    countries = sorted(repo.countries(), key=lambda p: p.name)
    shared_layers = sorted((p for p in repo.packages if p.level == "layer" and p.country is None), key=lambda p: p.name)
    for c in countries:
        layers = sorted((p for p in repo.packages if p.level == "layer" and p.country == c.name), key=lambda p: p.name) + shared_layers
        bases = [(c.name, [c], c)] + [(t.name, [c, t], t) for t in sorted(repo.types_of(c.name), key=lambda p: p.name)]
        for name, rank, target in bases:
            stacks.append(Stack(name, [rank], target))
            if layers:
                stacks.append(Stack(name + " + its layers", [rank] + [[l] for l in layers]))
    if not countries:
        for l in shared_layers:
            stacks.append(Stack(l.name, [[l]], l))
    for p in sorted((p for p in repo.packages if p.level in ("project", "site")), key=lambda p: p.name):
        c = repo.by_name(p.owner_country) if p.owner_country else None
        if p.level == "project":
            stacks.append(Stack(p.name, [[p]], p))
        if c is not None and c.level == "country":
            stacks.append(Stack(f"{c.name} + {p.name}", [[c], [p]], p))
        elif p.level == "site":
            stacks.append(Stack(p.name, [[p]], p))
    # A central instance's base package is its stack's base alone (OpenClinic's level `instance`).
    for p in sorted((p for p in repo.packages if p.level == "instance"), key=lambda p: p.name):
        stacks.append(Stack(p.name, [[p]], p))
    return stacks


def stage(repo_root, stack, directory):
    """Copies the stack's packages to `<directory>/<rank>/<name>/`, readable by every user: the
    container runs as uid 1000 and mounts the directory read-only."""
    os.makedirs(directory, exist_ok=True)
    os.chmod(directory, 0o755)
    for i, rank in enumerate(stack.ranks):
        for p in rank:
            target = os.path.join(directory, str(i), p.name)
            shutil.copytree(os.path.join(repo_root, p.rel), target)
            readable(os.path.join(directory, str(i)))


def readable(top):
    """a+rX, u+w, on a directory tree."""
    for dirpath, dirnames, filenames in os.walk(top):
        os.chmod(dirpath, 0o755)
        for f in filenames:
            full = os.path.join(dirpath, f)
            os.chmod(full, (os.stat(full).st_mode | stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH) & 0o777)
