"""T1 (the spec, §5.2): no package of the checkout names a tag the registry holds with other
content. The same comparison as publishing's T2 and T3, run before the merge."""
import sys

from . import repo as repo_mod
from .publish import differs, published, registry_from


def run(root, args):
    repo = repo_mod.load(root)
    registry = registry_from(args)
    problems, published_count = [], 0
    for pkg in repo.packages:
        labels = published(registry, args.namespace, pkg)
        if labels is None:
            continue
        published_count += 1
        why = differs(repo, pkg, labels)
        if why:
            problems.append(f"T1 {pkg.rel}/package.yaml: {why.split(' ', 1)[1]}")
    for p in problems:
        print(p, file=sys.stderr)
    print(f"tags: {len(repo.packages)} package(s), {published_count} already published, {len(problems)} problem(s)")
    return 1 if problems else 0
