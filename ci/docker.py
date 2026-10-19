"""The few docker commands the checks run, and the image they run them from."""
import json
import os
import subprocess
import sys

import yaml

PIN = "openclinic.yaml"
NO_CONFIG = 127   # the image's entrypoint execs an unknown command: "exec: config: not found"


class NoConfigCommand(Exception):
    pass


class ImageMissing(Exception):
    pass


def pinned_image(root):
    try:
        with open(os.path.join(root, PIN), encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raise ValueError(f"{PIN} is missing: it names the OpenClinic image the checks run on (or give --image)") from None
    image = doc.get("image")
    if not isinstance(image, str) or ":" not in image.rsplit("/", 1)[-1]:
        raise ValueError(f"{PIN}: 'image' names no image with a tag")
    return image


def run(args, check=True, capture=False, quiet=False, input=None):
    if not quiet:
        print("+ docker " + " ".join(args), file=sys.stderr, flush=True)
    r = subprocess.run(["docker"] + args, capture_output=capture, text=True, input=input)
    if check and r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, ["docker"] + args, r.stdout, r.stderr)
    return r


def ensure(image):
    """The image present locally, pulled when it is not."""
    if run(["image", "inspect", image], check=False, capture=True, quiet=True).returncode != 0:
        r = run(["pull", "-q", image], check=False, capture=True)
        if r.returncode != 0:
            raise ImageMissing(f"the image {image} cannot be pulled: {(r.stderr or r.stdout).strip()}. "
                               f"{PIN} must name a published OpenClinic release that carries the config command")


def env_of(image):
    out = run(["image", "inspect", image, "--format", "{{json .Config.Env}}"], capture=True, quiet=True).stdout
    return dict(e.split("=", 1) for e in json.loads(out) or [] if "=" in e)


def check_config_command(image, result):
    """Raises NoConfigCommand when a `docker run <image> config …` found no such command."""
    if result.returncode == NO_CONFIG and "config: not found" in (result.stderr or "") + (result.stdout or ""):
        raise NoConfigCommand(f"the image {image} has no 'config' command: openclinic.yaml must name a release "
                              f"of OpenClinic that carries config apply and config lint (SP1)")
