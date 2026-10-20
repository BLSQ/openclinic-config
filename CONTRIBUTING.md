# Contributing a package

1. **Choose its place** (README, L1-L8): a country's package at `countries/<c>/<c>/`; a facility
   type of it at `countries/<c>/<c>-<type>/` with `base: <c>`; a layer for one country beside them
   with `country: <c>`; a layer for every country, or a project several countries share, under
   `shared/`.
2. **Write its manifest**:

   ```yaml
   apiVersion: openclinic/v1alpha1
   kind: Package
   name: mr-cs
   title: Centres de santé de Mauritanie
   version: 0.3.1
   level: type
   base: mr
   requires:
     openclinic: ">=0.2.0 <0.3.0"
   ```

   and its kinds' files, as OpenClinic's configuration design describes them (§5.1). A package names
   what the business names, a service, a profile, a module, a key, never a table or a local number.
3. **Give it a version**: a new package any; a changed one a higher one than `main` holds (V1, V2); a
   country's new version comes with a new version of each of its types (V3).
4. **Open a pull request.** Its checks lint every package, merge every pair of layers, and apply every
   package twice to a fresh database of the release candidate. A package that a check refuses is
   explained in the job's log, and the replay's reports are the job's artifact.
5. **A code owner reviews it** (`.github/CODEOWNERS`): the country's reviewer for `countries/<c>/`.
   Once merged, the package is published as `ghcr.io/blsq/openclinic-config/<name>:<version>`.

A package that needs an OpenClinic version not yet released declares it in `requires`; it is not
replayed, and not applied by any site, before a release that accepts it.

Never in a package: a password, a token, a site's server id, or any key of OpenClinic's closed lists
(`config lint` refuses them).
