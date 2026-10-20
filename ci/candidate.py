"""The highest OpenClinic release or release candidate published, and whether it is above the
pinned one (the spec, §9). Writes `image`, `version` and `newer` to $GITHUB_OUTPUT when set."""
import os
import sys

from . import docker
from .registry import Registry, split_image
from .semver import Version


def highest(tags):
    versions = []
    for t in tags:
        try:
            versions.append(Version.parse(t))
        except ValueError:
            pass   # sha-…, latest and the like
    return max(versions) if versions else None


def main(root, args):
    pinned = docker.pinned_image(root)
    host, name, tag = split_image(pinned)
    repo_host, _, repo_name = args.repository.partition("/")
    top = highest(Registry(repo_host).tags(repo_name))
    if top is None:
        print(f"candidate: {args.repository} has no version tag", file=sys.stderr)
        return 1
    image = f"{args.repository}:{top}"
    try:
        newer = (repo_host, repo_name) != (host, name) or top > Version.parse(tag)
    except ValueError:
        newer = True
    print(f"candidate: pinned {pinned}; the highest published is {image}" + ("" if newer else ", the pinned one or below"))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"image={image}\nversion={top}\nnewer={'true' if newer else 'false'}\n")
    return 0
