"""The layout rules L1 to L8 (the spec, §4): where a package lives, and what its place says."""
import re

from .repo import COUNTRIES, SHARED, Problem

LEVELS = ("country", "type", "layer", "project", "site")
RESERVED = (COUNTRIES, SHARED)


def check(repo):
    problems = list(repo.problems)
    names = {}
    for p in repo.packages:
        parts = p.parts
        where = p.rel + "/package.yaml"
        # L1: countries/<c>/<name>/ or shared/<name>/
        placed = (len(parts) == 3 and parts[0] == COUNTRIES) or (len(parts) == 2 and parts[0] == SHARED)
        if not placed:
            problems.append(Problem("L1", where, "a package lives at countries/<country>/<name>/ or shared/<name>/"))
            continue
        # L2: the directory is the name
        if parts[-1] != p.name:
            problems.append(Problem("L2", where, f"the directory is '{parts[-1]}' and the manifest's name '{p.name}': the two must agree"))
        # L3: unique, not reserved
        if p.name in names:
            problems.append(Problem("L3", where, f"the name '{p.name}' is also the package at {names[p.name]}: a name is unique in the repository"))
        else:
            names[p.name] = p.rel
        if p.name in RESERVED:
            problems.append(Problem("L3", where, f"'{p.name}' is a directory of the repository, not a package name"))
        if p.level not in LEVELS:
            continue   # the schema's to say; config lint names it
        c = p.owner_country
        if p.level == "country":
            # L4: a country lives at countries/<name>/<name>/
            if c != p.name:
                problems.append(Problem("L4", where, f"a country package lives at countries/{p.name}/{p.name}/"))
        elif p.level == "type":
            # L5: a type lives under its country
            if c is None:
                problems.append(Problem("L5", where, "a type lives under its country, at countries/<country>/<name>/"))
            elif p.base != c:
                problems.append(Problem("L5", where, f"a type under countries/{c}/ has 'base: {c}', not {p.base!r}"))
        elif p.level == "layer":
            # L6: a layer's country is its directory's
            if c is not None and p.country != c:
                problems.append(Problem("L6", where, f"a layer under countries/{c}/ names 'country: {c}', not {p.country!r}"))
            if c is None and p.country is not None:
                problems.append(Problem("L6", where, f"a layer for the country '{p.country}' lives under countries/{p.country}/, not under shared/"))
        # L7: projects and sites may live under either: nothing to check.
    # L4: a country directory holds its country package
    country_dirs = sorted({p.parts[1] for p in repo.packages if len(p.parts) == 3 and p.parts[0] == COUNTRIES})
    for c in country_dirs:
        pkg = repo.by_name(c)
        if pkg is None or pkg.level != "country" or pkg.rel != f"{COUNTRIES}/{c}/{c}":
            problems.append(Problem("L4", f"{COUNTRIES}/{c}/", f"holds no country package '{c}' at {COUNTRIES}/{c}/{c}/"))
    # L8: a type's base and a layer's country name a country of the repository
    countries = {p.name for p in repo.countries()}
    for p in repo.packages:
        ref = p.base if p.level == "type" else p.country if p.level == "layer" else None
        if ref is not None and ref not in countries:
            field = "base" if p.level == "type" else "country"
            problems.append(Problem("L8", p.rel + "/package.yaml", f"'{field}: {ref}' names no country package of the repository"))
    return problems


def warnings(repo, codeowners):
    """A country directory without its own CODEOWNERS line (the spec, §10): said, not refused."""
    lines = [l.split("#", 1)[0].split() for l in (codeowners or "").splitlines()]
    patterns = {l[0].strip("/") for l in lines if l}
    out = []
    for c in sorted({p.owner_country for p in repo.packages if p.owner_country}):
        if f"{COUNTRIES}/{c}" not in patterns:
            out.append(f"countries/{c}/ has no line of its own in .github/CODEOWNERS: its reviewer is the default owner")
    return out
