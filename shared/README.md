# shared/

Packages no country owns: layers for every country (an insurer, a programme, no `country` field) and
projects that serve sites of several countries. A layer made for one country lives under
`countries/<c>/` instead.

The 116 project packages here at `1.0.0` were derived from the application's `web/projects/` by
`.ci/derive-project-packages.py` (the SP12 spec of `BLSQ/openclinicga`, §6) and imported whole. The
derivation reads no country: a project's directory says none. A country that takes one over moves it
under `countries/<c>/`, where its reviewer is that country's. The 31 directories the image keeps are not
here (`.ci/image-projects.txt` in `BLSQ/openclinicga`): the 24 per-country directories, most named like a
country package (L3), and the seven editions the application's own code names by their path.
