import html
import http.server
import os
import threading
import unittest
import urllib.parse

from ci import public, repo
from ci.tests.helpers import TempRepo, write_package

NS = "blsq/openclinic-config"


def fixture(root):
    write_package(root, "countries/mr", "mr", "country", version="1.2.0")
    write_package(root, "countries/mr", "mr-cs", "type", base="mr", version="0.3.1")
    write_package(root, "shared", "cnam", "layer")


class PlanTest(unittest.TestCase):

    def test_the_targets_are_the_packages_no_anonymous_caller_can_pull(self):
        with TempRepo() as root:
            fixture(root)
            asked = []

            def readable(name, version):
                asked.append((name, version))
                return name == "mr"
            got = public.targets(repo.load(root), readable)
        self.assertEqual(["cnam", "mr-cs"], [p.name for p in got])
        self.assertIn(("mr-cs", "0.3.1"), asked)

    def test_names_restrict_and_an_unknown_one_is_refused(self):
        with TempRepo() as root:
            fixture(root)
            r = repo.load(root)
            self.assertEqual(["cnam"], [p.name for p in public.targets(r, lambda n, v: False, ["cnam"])])
            with self.assertRaisesRegex(ValueError, "not in the repository: zz"):
                public.targets(r, lambda n, v: False, ["cnam", "zz"])

    def test_the_package_is_named_below_its_organisation(self):
        self.assertEqual(("blsq", "openclinic-config/bi"), public.package_name(NS, "bi"))
        self.assertEqual(("blsq", "bi"), public.package_name("blsq", "bi"))
        self.assertEqual("https://github.com/orgs/blsq/packages/container/openclinic-config%2Fbi/settings",
                         public.settings_url("https://github.com", "blsq", "openclinic-config/bi"))

    def test_the_confirmation_is_what_the_dialog_asks_for(self):
        self.assertEqual("openclinic-config/bi", public.confirmation(
            "Please type openclinic-config/bi to confirm.", "x"))
        self.assertEqual("openclinic-config/bi", public.confirmation(
            "To confirm, type “openclinic-config/bi” to confirm the change", "x"))
        self.assertEqual("fallback", public.confirmation("Change package visibility", "fallback"))


# -- the page, driven for real: a settings page laid out as GitHub documents it -------------------

PAGE = """<!doctype html><html><head><meta name="user-login" content="{user}"><title>{name}</title></head>
<body><h2>Danger Zone</h2>{danger}</body></html>"""
DANGER = """<button type="button" onclick="document.getElementById('v').showModal()">Change visibility</button>
<dialog id="v" aria-label="Change package visibility"><form method="post" action="{action}">
<label><input type="radio" name="visibility" value="public"> Public</label>
<label><input type="radio" name="visibility" value="private" checked> Private</label>
<p>Please type <strong>{name}</strong> to confirm.</p>
<input type="text" name="verify" aria-label="Type the package name">
<button type="submit">I understand the consequences, change package visibility.</button>
</form></dialog>"""


class FakeGitHub(http.server.ThreadingHTTPServer):
    """Each package's settings page; `missing` ones show no Danger Zone button (a page that changed)."""

    def __init__(self, missing=(), styled=False, anonymous=False):
        super().__init__(("127.0.0.1", 0), Handler)
        self.public, self.missing, self.posts, self.styled = set(), set(missing), [], styled
        self.user = "" if anonymous else "maintainer"       # anonymous: the pages name nobody
        self.url = f"http://127.0.0.1:{self.server_port}"
        threading.Thread(target=self.serve_forever, daemon=True).start()


class Handler(http.server.BaseHTTPRequestHandler):
    PREFIX = "/orgs/blsq/packages/container/"

    def log_message(self, *a):
        pass

    def full_name(self):
        rest = self.path[len(self.PREFIX):] if self.path.startswith(self.PREFIX) else ""
        return urllib.parse.unquote(rest.rsplit("/", 1)[0]) if "/" in rest else None

    def send(self, status, body=b"", location=None):
        self.send_response(status)
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        name = self.full_name()
        if self.path == "/":
            return self.send(200, PAGE.format(name="home", danger="", user=self.server.user).encode())
        if self.path == "/login":                              # GitHub's sign-in page names nobody
            return self.send(200, PAGE.format(name="Sign in", danger="", user="").encode())
        if name is None or not self.path.endswith("/settings"):
            return self.send(404)
        danger = "" if name in self.server.missing else DANGER.format(
            action=html.escape(self.path.replace("/settings", "/visibility")), name=html.escape(name))
        if self.server.styled:                                 # the inputs hidden, their labels drawn
            danger = danger.replace('type="radio"', 'type="radio" style="display:none"')
        self.send(200, PAGE.format(name=html.escape(name), danger=danger, user=self.server.user).encode())

    def do_POST(self):
        name = self.full_name()
        form = urllib.parse.parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
        self.server.posts.append((name, form))
        if form.get("visibility") == ["public"] and form.get("verify") == [name]:
            self.server.public.add(name.rsplit("/", 1)[-1])
        self.send(303, location=self.path.replace("/visibility", "/settings"))


def browser():
    """Playwright's Chromium, or the one this machine has; None when Playwright is not installed."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright, os.environ.get("OC_TEST_CHROMIUM") or None


@unittest.skipIf(browser() is None, "Playwright is not installed (pip install playwright)")
class PageTest(unittest.TestCase):

    def setUp(self):
        public.PUBLIC_TIMEOUT = 1

    def drive(self, github, packages, ask):
        sync_playwright, executable = browser()
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True, executable_path=executable)
            try:
                page = public.sign_in(b.new_context(), github.url, timeout=5)
                return public.run(page, packages, NS, github.url,
                                  lambda name, version: name in github.public, ask=ask)
            finally:
                b.close()

    def test_each_package_is_made_public_through_the_documented_steps(self):
        github = FakeGitHub()
        try:
            with TempRepo() as root:
                fixture(root)
                left = self.drive(github, repo.load(root).packages, ask=lambda m: self.fail("asked: " + m))
            self.assertEqual([], left)
            self.assertEqual({"mr", "mr-cs", "cnam"}, github.public)
            name, form = github.posts[0]
            self.assertEqual(["public"], form["visibility"])
            self.assertEqual([name], form["verify"])            # the name the dialog asked for
        finally:
            github.shutdown()
            github.server_close()

    def test_the_sign_in_is_github_s_cookie_whatever_the_page_shows(self):
        github = FakeGitHub(anonymous=True)
        sync_playwright, executable = browser()
        try:
            with sync_playwright() as pw:
                b = pw.chromium.launch(headless=True, executable_path=executable)
                try:
                    context = b.new_context()
                    with self.assertRaisesRegex(public.Step, "not signed in after 2 s"):
                        public.sign_in(context, github.url, timeout=2)
                    context.add_cookies([{"name": "logged_in", "value": "no", "url": github.url}])
                    with self.assertRaisesRegex(public.Step, "not signed in"):
                        public.sign_in(context, github.url, timeout=2)
                    # signed in in another tab: the cookie says so, the first tab still shows nobody
                    context.add_cookies([{"name": "logged_in", "value": "yes", "url": github.url}])
                    page = public.sign_in(context, github.url, timeout=2)
                    self.assertFalse(page.is_closed())
                finally:
                    b.close()
        finally:
            github.shutdown()
            github.server_close()

    def test_a_hidden_radio_is_chosen_through_its_label(self):
        github = FakeGitHub(styled=True)
        try:
            with TempRepo() as root:
                fixture(root)
                left = self.drive(github, [p for p in repo.load(root).packages if p.name == "cnam"],
                                  ask=lambda m: self.fail("asked: " + m))
            self.assertEqual([], left)
            self.assertEqual(["public"], github.posts[0][1]["visibility"])
        finally:
            github.shutdown()
            github.server_close()

    def test_a_page_that_changed_is_left_to_the_person_and_the_pull_decides(self):
        github = FakeGitHub(missing={"openclinic-config/mr-cs"})
        asked = []

        def person(message):                                   # does it by hand, for one of two
            asked.append(message)
            github.public.add("mr-cs")
            return True
        try:
            with TempRepo() as root:
                fixture(root)
                left = self.drive(github, [p for p in repo.load(root).packages if p.name in ("mr-cs", "cnam")], person)
            self.assertEqual([], left)
            self.assertEqual(1, len(asked))
            self.assertIn("openclinic-config/mr-cs", asked[0])
        finally:
            github.shutdown()
            github.server_close()

    def test_a_package_still_private_is_named(self):
        github = FakeGitHub(missing={"openclinic-config/cnam"})
        try:
            with TempRepo() as root:
                fixture(root)
                left = self.drive(github, [p for p in repo.load(root).packages if p.name == "cnam"], lambda m: False)
            self.assertEqual(["cnam"], left)
        finally:
            github.shutdown()
            github.server_close()


if __name__ == "__main__":
    unittest.main()
