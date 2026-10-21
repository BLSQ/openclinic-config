"""`config lint` from the pinned image, on countries/, shared/ and instances/ alone (the spec, §6)."""
import os
import shutil
import sys
import tempfile

from . import docker, repo as repo_mod
from .repo import COUNTRIES, INSTANCES, SHARED
from .stacks import readable


def run(root, image):
    if not repo_mod.manifests(root):
        print("lint: no package in the repository, nothing to lint")
        return 0
    docker.ensure(image)
    with tempfile.TemporaryDirectory(prefix="openclinic-config-lint-") as stage:
        os.chmod(stage, 0o755)
        for d in (COUNTRIES, SHARED, INSTANCES):
            if os.path.isdir(os.path.join(root, d)):
                shutil.copytree(os.path.join(root, d), os.path.join(stage, d))
        readable(stage)
        r = docker.run(["run", "--rm", "--network", "none", "-v", f"{stage}:/repo:ro", image, "config", "lint", "/repo"],
                       check=False, capture=True)
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        docker.check_config_command(image, r)
        return 0 if r.returncode == 0 else 1
