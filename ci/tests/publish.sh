#!/bin/sh
# Publishing end to end (the spec, §8 and §11): a local registry and a BuildKit builder, the fixture
# repository ci/tests/repos/good published, then read back through the registry's API. Needs Docker
# with buildx; pulls registry:2 and moby/buildkit.
set -eu
cd "$(dirname "$0")/../.."
port="${OC_TEST_REGISTRY_PORT:-5555}"
reg="localhost:$port"
ns="test/openclinic-config"
tag="ocpub-$$"
work=$(mktemp -d)
cleanup() {
  docker buildx rm "$tag" >/dev/null 2>&1 || true
  docker rm -f "$tag-registry" >/dev/null 2>&1 || true
  rm -rf "$work"
}
trap cleanup EXIT
fail() { echo "publish.sh: $1" >&2; cat "$work/log" >&2 2>/dev/null || true; exit 1; }
publish() { python3 -m ci --root "$work/repo" publish --registry "$reg" --insecure --no-public-check --namespace "${NS:-$ns}"; }

docker pull -q registry:2 >/dev/null
docker run -d --name "$tag-registry" -p "127.0.0.1:$port:5000" registry:2 >/dev/null
printf '[registry."%s"]\n  http = true\n  insecure = true\n' "$reg" > "$work/buildkitd.toml"
docker buildx create --name "$tag" --driver docker-container --driver-opt network=host --buildkitd-config "$work/buildkitd.toml" --bootstrap >/dev/null 2>&1
export BUILDX_BUILDER="$tag"
cp -r ci/tests/repos/good "$work/repo"
git -C "$work/repo" init -q && git -C "$work/repo" add -A && git -C "$work/repo" -c user.name=t -c user.email=t@t commit -qm fixture

# 1. Everything built, countries first, and read back with the content hash it carries.
publish > "$work/log" 2>&1 || fail "the first publish failed"
[ "$(grep -c '^publish: build ' "$work/log")" = 6 ] || fail "six packages to build expected"
grep -q '^publish: build   xa:1.0.0' "$work/log" || fail "the country first"

# 2. Both architectures in each index; the type's image holds its country's directory and its own.
python3 - "$reg" "$ns" <<'PY' || fail "the images read back wrong"
import gzip, io, json, sys, tarfile
from ci.registry import Registry
reg, ns = Registry(sys.argv[1], insecure=True), sys.argv[2]
for name, tag in (("xa", "1.0.0"), ("xa-cs", "0.3.1"), ("cnam", "1.0.0")):
    assert reg.platforms(f"{ns}/{name}", tag) == ["linux/amd64", "linux/arm64"], (name, reg.platforms(f"{ns}/{name}", tag))
def paths(name, tag, platform):
    manifest, _ = reg.image(f"{ns}/{name}", tag, platform)
    out = set()
    for layer in manifest["layers"]:
        _, _, blob = reg._request("GET", f"{ns}/{name}", f"blobs/{layer['digest']}", "*/*")
        with tarfile.open(fileobj=io.BytesIO(blob)) as t:
            for m in t.getmembers():
                # readable by the container's uid 1000, the volume being read-only
                assert m.mode & 0o004 and (not m.isdir() or m.mode & 0o001), (m.name, oct(m.mode))
                out.add(m.name.split("/")[0])
    return out
for platform in ("linux/amd64", "linux/arm64"):
    assert paths("xa", "1.0.0", platform) == {"xa"}, paths("xa", "1.0.0", platform)
    assert paths("xa-cs", "0.3.1", platform) == {"xa", "xa-cs"}, paths("xa-cs", "0.3.1", platform)
labels = reg.labels(f"{ns}/xa-cs", "0.3.1")
assert labels["be.openclinic.package.base"] == "xa:1.0.0", labels
assert labels["be.openclinic.package.level"] == "type", labels
print("images read back: two platforms each, the type holding /xa/ and /xa-cs/, every file readable by all")
PY

# 3. A second run pushes nothing.
publish > "$work/log" 2>&1 || fail "the second publish failed"
grep -q '^publish: build' "$work/log" && fail "a second run built something"
[ "$(grep -c '^publish: skip ' "$work/log")" = 6 ] || fail "six packages to skip expected"

# 4. Reproducible: the same country published under another name gives the same digest.
NS="$ns-again" publish > "$work/log" 2>&1 || fail "the publish under another namespace failed"
python3 - "$reg" "$ns" <<'PY' || fail "the same files gave two digests"
import sys
from ci.registry import Registry
reg, ns = Registry(sys.argv[1], insecure=True), sys.argv[2]
def digest(n):
    s, h, _ = reg._request("HEAD", n, "manifests/1.0.0", "application/vnd.oci.image.index.v1+json")
    return h["Docker-Content-Digest"]
assert digest(f"{ns}/xa") == digest(f"{ns}-again/xa"), (digest(f"{ns}/xa"), digest(f"{ns}-again/xa"))
print("reproducible: one digest for the same files")
PY

# 5. A file changed under a published version: the pull request's check (T1) and publishing (T2) refuse it.
echo "  test.sp5.added: 'x'" >> "$work/repo/countries/xa/xa/config.yaml"
set +e; python3 -m ci --root "$work/repo" tags --registry "$reg" --insecure --namespace "$ns" > "$work/log" 2>&1; got=$?; set -e
[ "$got" = 1 ] || fail "tags: exit $got, expected 1"
grep -q '^T1 countries/xa/xa/package.yaml' "$work/log" || fail "T1 not named"
set +e; publish > "$work/log" 2>&1; got=$?; set -e
[ "$got" = 1 ] || fail "publish: exit $got, expected 1"
grep -q 'refuse  xa:1.0.0  T2' "$work/log" || fail "T2 not named"
grep -q 'nothing is built' "$work/log" || fail "a refusal must build nothing"
echo "publish.sh: 5 scenarios passed"
