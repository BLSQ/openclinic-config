"""Fixture repositories written into a temporary directory, one package at a time."""
import os
import tempfile

import yaml


def manifest(name, level, version="1.0.0", base=None, country=None, requires=">=0.1.0", title=None, instance=None):
    m = {"apiVersion": "openclinic/v1alpha1", "kind": "Package", "name": name,
         "title": title or f"{name}, a test package", "version": version, "level": level}
    if base:
        m["base"] = base
    if country:
        m["country"] = country
    if instance:
        m["instance"] = instance
    m["requires"] = {"openclinic": requires}
    return m


def write_package(root, where, name, level, files=None, **fields):
    """`where` is the package's parent, relative to the repository: `countries/mr` or `shared`."""
    d = os.path.join(root, where, name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "package.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest(name, level, **fields), f, sort_keys=False, allow_unicode=True)
    for rel, content in (files or {}).items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(content if isinstance(content, bytes) else content.encode("utf-8"))
    return d


def config(keys):
    lines = ["apiVersion: openclinic/v1alpha1", "kind: Config", "keys:"]
    lines += [f"  {k}: {yaml.safe_dump(v, default_flow_style=True).strip().removesuffix('...').strip()}" for k, v in keys.items()]
    return "\n".join(lines) + "\n"


class TempRepo:
    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        return self._tmp.name

    def __exit__(self, *exc):
        self._tmp.cleanup()
