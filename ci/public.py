"""Each package public on ghcr.io, by its settings page: `python3 -m ci make-public`.

A package a workflow pushes is private, and a site pulls without a token, so each package must be
made public once (the spec's §8 and O3). GitHub offers no API for a package's visibility, only the
package's settings page; this command drives that page in a browser the maintainer signs in to: for
every package of the repository that an anonymous caller cannot pull, "Change visibility", "Public",
the package's name typed, "I understand the consequences, change package visibility" — the steps of
GitHub's own documentation. What decides is the anonymous pull, checked after each package: a step
the page does not offer as expected is left to the maintainer in the open window, and the command
waits for them, then checks again.

Not for CI: it needs a person's session, an admin of the packages (GitHub may ask them to confirm
their password once, "Confirm access", which they do in the window). It needs Playwright:
`pip install playwright && python3 -m playwright install chromium`. The browser keeps its profile in
--profile, so the sign-in is asked once. Making a package public cannot be undone.
"""
import os
import re
import sys
import time
import urllib.parse

from . import repo as repo_mod
from .registry import Registry

LOGIN_TIMEOUT = 600          # seconds for the maintainer to sign in
PUBLIC_TIMEOUT = 30          # seconds for a visibility change to reach the registry


class Step(Exception):
    """A step the page did not offer as GitHub documents it."""


def targets(repo, readable, names=None):
    """The packages a site cannot pull anonymously, each once, in the repository's order: `readable`
    answers for a (name, version). `names` restricts to those, and names one the repository lacks."""
    wanted = set(names or [])
    unknown = sorted(wanted - {p.name for p in repo.packages})
    if unknown:
        raise ValueError("not in the repository: " + ", ".join(unknown))
    out = []
    for p in sorted(repo.packages, key=lambda p: p.name):
        if wanted and p.name not in wanted:
            continue
        if not readable(p.name, p.version_text):
            out.append(p)
    return out


def package_name(namespace, name):
    """`blsq/openclinic-config` and `bi` -> ('blsq', 'openclinic-config/bi'): the organisation, and
    the package's name as GitHub spells it (its repository path below the organisation)."""
    org, _, prefix = namespace.partition("/")
    return org, (f"{prefix}/{name}" if prefix else name)


def settings_url(github, org, full_name):
    return f"{github}/orgs/{org}/packages/container/{urllib.parse.quote(full_name, safe='')}/settings"


def confirmation(text, default):
    """What the dialog asks to be typed: its "type <name> to confirm", or the package's name."""
    m = re.search(r"type\s+[\"'“]?([A-Za-z0-9._/-]+?)[\"'”]?\s+to\s+confirm", text, re.I)
    return m.group(1) if m else default


def signed_in(page):
    meta = page.locator('meta[name="user-login"]')
    return meta.count() > 0 and bool((meta.first.get_attribute("content") or "").strip())


def sign_in(page, github, timeout=LOGIN_TIMEOUT):
    page.goto(github + "/")
    if signed_in(page):
        return
    page.goto(github + "/login")
    print("make-public: sign in to GitHub in the browser window (an admin of the packages)", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(2)
        try:
            if "/login" not in page.url and "/sessions" not in page.url and signed_in(page):
                return
        except Exception:
            pass                 # the page is navigating
    raise Step(f"not signed in after {timeout} s")


def change_visibility(page, url, full_name):
    """The documented steps on the package's settings page; raises Step naming the one missing."""
    response = page.goto(url)
    if response is not None and response.status == 404:
        raise Step("no such package, or not an admin of it (404)")
    # a <button> opening a <dialog>, or a <summary> opening a <details-dialog>: GitHub has used both
    button = page.locator("button, summary").filter(has_text=re.compile(r"change visibility", re.I))
    if button.count() == 0:
        raise Step("no 'Change visibility' button (an admin of the package sees it, under 'Danger Zone')")
    button.first.click()
    # the radios may be styled, the inputs themselves hidden: found by their element, not their role
    dialog = page.get_by_role("dialog").filter(has=page.locator('input[type="radio"]'))
    try:
        dialog.first.wait_for(state="visible", timeout=10000)
    except Exception:
        raise Step("no dialog with the visibility choices after 'Change visibility'") from None
    dialog = dialog.first
    public = dialog.locator('input[type="radio"][value="public" i]')
    if public.count() == 0:
        public = dialog.get_by_role("radio", name=re.compile(r"^\s*public\b", re.I))
    if public.count() == 0:
        raise Step("no 'Public' choice in the dialog")
    try:
        public.first.check(timeout=3000)
    except Exception:            # a hidden input: its label takes the click
        label = dialog.locator("label").filter(has_text=re.compile(r"^\s*public\b", re.I))
        if label.count() == 0:
            raise Step("the 'Public' choice could not be selected") from None
        label.first.click()
    if not public.first.is_checked():
        raise Step("the 'Public' choice could not be selected")
    box = dialog.get_by_role("textbox")
    if box.count() == 0:
        raise Step("no field to type the package's name in")
    box.first.fill(confirmation(dialog.inner_text(), full_name))
    submit = dialog.get_by_role("button", name=re.compile(r"i understand|change package visibility", re.I))
    if submit.count() == 0:
        raise Step("no 'I understand the consequences, change package visibility' button")
    try:
        with page.expect_navigation(timeout=15000):
            submit.last.click(timeout=10000)
    except Exception:            # a button still disabled, or a page that answers without navigating
        if not submit.last.is_enabled():
            raise Step("the confirmation button stays disabled: the name typed is not the one asked") from None
    page.wait_for_load_state("load")
    if "/sessions/sudo" in page.url or page.get_by_text(re.compile(r"confirm access", re.I)).count() > 0:
        raise Step("GitHub asks to confirm access: do it in the window")


def wait_public(readable, name, version, timeout=None):
    deadline = time.time() + (PUBLIC_TIMEOUT if timeout is None else timeout)
    while True:
        if readable(name, version):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(3)


def ask_person(message):
    """Hands a step to the maintainer: True once they press Enter, False without a terminal."""
    if not sys.stdin.isatty():
        print(f"make-public: {message} (no terminal to wait on: run it again once done)", file=sys.stderr)
        return False
    input(f"make-public: {message}, then press Enter here ")
    return True


def run(page, packages, namespace, github, readable, ask=ask_person):
    """Each package made public in turn; the names still private at the end."""
    left = []
    for p in packages:
        org, full = package_name(namespace, p.name)
        url = settings_url(github, org, full)
        print(f"make-public: {full} {p.version_text}", flush=True)
        try:
            change_visibility(page, url, full)
            done = wait_public(readable, p.name, p.version_text)
            why = None if done else "the page took the change, and the registry still refuses an anonymous pull"
        except Step as e:
            done, why = False, str(e)
        except Exception as e:     # a page GitHub changed: the person finishes, the pull decides
            if page.is_closed() or "closed" in type(e).__name__.lower():
                raise Step("the browser window was closed") from None
            done, why = False, f"the page did not go as documented ({type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''})"
        if not done:
            print(f"make-public: {full}: {why}", file=sys.stderr)
            if ask(f"make {full} public in the window ({url}: Change visibility, Public, its name, confirm)"):
                done = wait_public(readable, p.name, p.version_text)
        print(f"make-public: {full}: {'public' if done else 'STILL PRIVATE'}", flush=True)
        if not done:
            left.append(p.name)
    return left


def main(root, args):
    repo = repo_mod.load(root)
    if repo.problems:
        for p in repo.problems:
            print(p.line(), file=sys.stderr)
        return 1
    anonymous = Registry(args.registry)

    def readable(name, version):
        return anonymous.anonymous_pull(f"{args.namespace}/{name}", version)

    todo = targets(repo, readable, args.names)
    if not todo:
        print(f"make-public: every package is pullable without a token ({len(repo.packages)} checked)")
        return 0
    print("make-public: private: " + ", ".join(p.name for p in todo))
    if args.dry_run:
        return 0
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("make-public: needs Playwright: pip install playwright && python3 -m playwright install chromium",
              file=sys.stderr)
        return 1
    profile = os.path.expanduser(args.profile)
    os.makedirs(profile, exist_ok=True)
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            profile, headless=args.headless, executable_path=args.browser or None, channel=args.channel or None)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            sign_in(page, args.github)
            left = run(page, todo, args.namespace, args.github, readable)
        except Step as e:
            print(f"make-public: {e}", file=sys.stderr)
            return 1
        finally:
            context.close()
    if left:
        print(f"make-public: {len(left)} still private: " + ", ".join(left), file=sys.stderr)
        return 1
    print(f"make-public: {len(todo)} package(s) made public; the next run of Publish passes")
    return 0
