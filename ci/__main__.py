"""python3 -m ci <command>: the checks and the publisher, as the workflows run them.

  layout                  the layout rules L1-L8 (and the CODEOWNERS warning)
  versions --base <ref>   the version rules V1-V5 against a git ref
  tags                    T1: no changed package's version already in the registry
  lint                    config lint, from the pinned image
  replay [--keep <dir>] [--jobs <n>] [--changed-from <ref>]
                          every stack applied twice on the pinned image; n at a time; only the
                          stacks a change touches
  publish [--dry-run]     build and push what the registry lacks
  candidate               the highest OpenClinic tag, if above the pinned one

Every command takes --root <dir> (the checkout, `.` by default) and, where an image is used,
--image <ref> (openclinic.yaml's by default). Exit 0 passes, 1 is a problem found, 2 a usage error.
"""
import argparse
import os
import sys

from . import docker


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m ci", description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("layout")
    v = sub.add_parser("versions")
    v.add_argument("--base", required=True, help="the git ref the pull request merges into")
    t = sub.add_parser("tags")
    t.add_argument("--registry", default="ghcr.io")
    t.add_argument("--namespace", default="blsq/openclinic-config")
    t.add_argument("--insecure", action="store_true", help="plain HTTP, for a local registry")
    for name in ("lint", "replay"):
        c = sub.add_parser(name)
        c.add_argument("--image")
        if name == "replay":
            c.add_argument("--keep", help="a directory that receives every stack's reports and logs")
            c.add_argument("--jobs", type=int, default=1, help="stacks replayed at a time, each on a server of its own")
            c.add_argument("--changed-from", metavar="REF",
                           help="only the stacks holding a package changed against this git ref (a pull request's base)")
    p = sub.add_parser("publish")
    p.add_argument("--registry", default="ghcr.io")
    p.add_argument("--namespace", default="blsq/openclinic-config")
    p.add_argument("--insecure", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="say what would be built, build nothing")
    p.add_argument("--no-public-check", action="store_true", help="skip the anonymous pull after pushing (a local registry)")
    c = sub.add_parser("candidate")
    c.add_argument("--repository", default="ghcr.io/blsq/openclinic")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    try:
        if args.command == "layout":
            from . import layout, repo
            r = repo.load(root)
            problems = layout.check(r)
            co = os.path.join(root, ".github", "CODEOWNERS")
            for w in layout.warnings(r, open(co).read() if os.path.exists(co) else ""):
                print("warning: " + w)
            return report(problems, f"layout: {len(r.packages)} package(s)")
        if args.command == "versions":
            from . import repo, versions
            problems, notes = versions.compare(versions.load_ref(root, args.base), repo.load(root))
            for n in notes:
                print("versions: " + n)
            return report(problems, "versions")
        if args.command == "tags":
            from . import tags
            return tags.run(root, args)
        if args.command in ("lint", "replay"):
            image = args.image or docker.pinned_image(root)
            if args.command == "lint":
                from . import lint
                return lint.run(root, image)
            from . import replay
            return replay.run(root, image, keep=os.path.abspath(args.keep) if args.keep else None,
                              jobs=args.jobs, changed_from=args.changed_from)
        if args.command == "publish":
            from . import publish
            return publish.main(root, args)
        if args.command == "candidate":
            from . import candidate
            return candidate.main(root, args)
    except (docker.NoConfigCommand, docker.ImageMissing) as e:
        print(f"{args.command}: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"{args.command}: {e}", file=sys.stderr)
        return 2
    return 2


def report(problems, what):
    for p in problems:
        print(p.line(), file=sys.stderr)
    print(f"{what}: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
