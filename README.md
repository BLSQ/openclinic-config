# openclinic-config

The configuration packages of [OpenClinic GA](https://github.com/BLSQ/openclinicga): one directory per
package, checked on every pull request, and published on merge as an image a site mounts.

A package is a directory with a manifest, `package.yaml`, and the files of its kinds (`config.yaml`,
`modules.yaml`, and the kinds the following OpenClinic releases add). Its format, its levels and how a
site's stack of packages applies are OpenClinic's: read
[configuration in layers](https://github.com/BLSQ/openclinicga/blob/claude/configuration-in-layers/docs/superpowers/specs/2026-10-16-configuration-in-layers-design.md),
§5. This repository is its part SP5, specified in OpenClinic's
`docs/superpowers/specs/2026-10-19-packages-repository-design.md`.

## The layout

```text
openclinic.yaml          the OpenClinic release candidate every check runs on
countries/<c>/<c>/       a country package
countries/<c>/<name>/    its facility types, its layers, its sites' and projects' packages
shared/<name>/           layers for every country, and projects no country owns
ci/                      the tooling, and its tests
```

| | Rule |
|---|---|
| L0 | A manifest is readable, its version a semantic version (no leading zero in a numeric pre-release identifier), and a package holds files only, never a symbolic link. |
| L1 | A package lives at `countries/<c>/<name>/` or `shared/<name>/`; a `package.yaml` anywhere else, `ci/tests/` excepted, is refused. |
| L2 | Its directory is its `name`. |
| L3 | A name is unique in the repository, and is neither `countries` nor `shared`. |
| L4 | `countries/<c>/` holds the country package `c`, at `countries/<c>/<c>/`, and a country package lives nowhere else. |
| L5 | A type lives under its country: its `base` is `c`. |
| L6 | A layer under `countries/<c>/` names `country: c`; a layer under `shared/` names none. |
| L7 | A project or a site package lives under either. |
| L8 | A type's `base` and a layer's `country` name a country package of the repository. |

## Versions and tags

A package's version is its image's tag, `ghcr.io/blsq/openclinic-config/<name>:<version>`, and a
published tag never changes.

| | Rule |
|---|---|
| V1 | A package whose files change takes a new version. |
| V2 | A new version is greater than the previous one. |
| V3 | A country that takes a new version makes each of its types take one too, in the same pull request: a type's image is built `FROM` its country's, so a site never receives two versions of its country. |
| V4 | A package removed is said, not refused: its published tags stay. |
| V5 | A package renamed is a package removed and one added. |
| T1 | No package names a tag the registry holds with other content (its label `be.openclinic.package.contenthash`, `config apply`'s own hash). |
| T2, T3 | The same, checked again when publishing, and for a type its country's version (`be.openclinic.package.base`). |

## What a pull request runs

`.github/workflows/checks.yml`:

| Job | What |
|---|---|
| Layout, versions and tags | L1-L8, V1-V5 against the base branch, T1 against the registry |
| config lint | `config lint` from the pinned image: every package against its schemas and the closed lists, every pair of layers merged |
| Replay on the release candidate | every package applied twice to a fresh database of the pinned image, in the smallest stacks a site could receive it in and in each base with all its layers: the first run must apply, the second must change nothing; between the two, `config export` of the stack against itself must give nothing back (the round trip: what the packages say came back unchanged). A pull request replays the stacks holding a package it adds or changes, and every stack when it touches `openclinic.yaml`, `ci/` or `.github/`, or removes a package; `main` replays every stack before publishing. Four stacks at a time, each on a MariaDB server of its own started from one snapshot |
| The tooling's own tests | `ci/tests` |

On `main`, once all four are green, the job **Publish** builds and pushes each package whose tag the
registry lacks: amd64 and arm64, `FROM scratch` (a type `FROM` its country), reproducible (the same
files give the same digest), and then read back without a token, as every site pulls it.

`.github/workflows/release-candidate.yml` runs every morning: when OpenClinic has published a
version above the pinned one, every package is linted and replayed on it, and a failure opens an
issue. Moving the pin is then a pull request of one line.

**`requires.openclinic` is checked against the release the candidate becomes**: on
`0.2.0-rc.1`, a package `>=0.2.0` is replayed, with `OPENCLINIC_VERSION=0.2.0`. A package whose
range excludes even that is not replayed, and the job says so. A package replayed that way and
refused by the candidate itself is named too: a site *running* `0.2.0-rc.1` refuses `>=0.2.0`
(a candidate comes before its release, and `config apply` checks its own version), so a pilot on a
candidate needs `>=0.2.0-rc.1`, or the release.

## Running the checks

Python 3.10 or later with PyYAML (`pip install -r ci/requirements.txt`), and Docker for the last
four:

```sh
python3 -m ci layout
python3 -m ci versions --base origin/main
python3 -m ci tags
python3 -m ci lint                       # the image of openclinic.yaml, or --image <ref>
python3 -m ci replay --keep /tmp/reports # the seed, then about half a minute a stack
python3 -m ci replay --jobs 4 --changed-from origin/main   # what a pull request runs
python3 -m ci publish --dry-run          # what would be built
python3 -m unittest discover -s ci/tests -t .
ci/tests/publish.sh                      # a local registry and a BuildKit builder
ci/tests/replay.sh                       # OC_TEST_IMAGE=<an image with config apply, lint and export>
```

The tooling never reads what a package says: it places, versions, replays and publishes packages.
Everything a package means is `config lint`'s and `config apply`'s, in OpenClinic's image.

## Settings this repository needs

- **Branch protection on `main`**: the four jobs above required, a review by the code owners.
- **Each package public on ghcr.io**: a package a workflow creates is private until it is made public
  (its settings, *Change visibility*), once per package. Until then the job **Publish** fails after
  pushing it, naming it.
- **`openclinic.yaml` names an OpenClinic release that carries the `config` command** (OpenClinic's
  SP1); the checks say so in one line when it does not. Without `config export` (SP4) the replay
  says the round trip awaits a release that has it, and runs the rest.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
