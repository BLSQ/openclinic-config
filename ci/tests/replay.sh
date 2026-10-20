#!/bin/sh
# The checks end to end on the fixture repositories of ci/tests/repos, with a real image: what
# config lint catches, what only the replay catches, and what is not replayed. Needs Docker and an
# OpenClinic image carrying config apply, lint and export (OC_TEST_IMAGE, openclinic.yaml's by default).
set -eu
cd "$(dirname "$0")/../.."
image="${OC_TEST_IMAGE:-$(python3 -c 'from ci import docker; print(docker.pinned_image("."))')}"
out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT
fail() { echo "replay.sh: $1" >&2; cat "$out/log" >&2 || true; exit 1; }
check() { # expected exit, command, the repository, then the command's own options
  want=$1; cmd=$2; repo=$3; shift 3
  set +e; python3 -m ci --root "ci/tests/repos/$repo" "$cmd" --image "$image" "$@" > "$out/log" 2>&1; got=$?; set -e
  [ "$got" = "$want" ] || fail "$cmd on $repo: exit $got, expected $want"
}
has() { grep -q -- "$1" "$out/log" || fail "expected in the output: $1"; }

# 1. Every level, both kinds the fixtures use: lint and the replay pass, every stack applied, exported
#    against itself with nothing given back (the round trip), then unchanged.
check 0 lint good
has "6 package(s) read, 3 pair(s) of layers merged, 0 problem(s)"
check 0 replay good --keep "$out/keep"
has "replay: 6 stack(s), 0 failed"
has "ok     xa-cs + its layers  \[xa + xa-cs | xa-pev | cnam\]"
has "replay: the round trip, every stack exported against itself after its first run"
trips=$(python3 -c 'import glob, json, sys; print(sum(json.load(open(f))["run"]["outcome"] == "written" for f in glob.glob(sys.argv[1] + "/*/round-trip.json")))' "$out/keep")
[ "$trips" = 6 ] || fail "the round trip ran on $trips stack(s), expected 6"

# 2. Two layers disagree: lint fails and names both.
check 1 lint disagree
has "two layers disagree"
has "cnam 1.0.0 sets 'CNAM', cnamgs 1.0.0 sets 'CNAMGS'"

# 3. A value the database cannot hold: lint passes, the replay refuses it.
check 0 lint charset
check 1 replay charset
has "the first run: exit 1, outcome refused"
has "character set"

# 4. A package for a release to come: not replayed, and the job passes.
check 0 replay later
has "requires >=9.0.0: not replayed on"

# 5. An image without the config command: one line that says so.
set +e; python3 -m ci --root ci/tests/repos/good lint --image ghcr.io/blsq/openclinic:0.1.0-rc.4 > "$out/log" 2>&1; got=$?; set -e
[ "$got" = 1 ] || fail "an image without config: exit $got, expected 1"
has "has no 'config' command"
echo "replay.sh: 5 scenarios passed on $image"
