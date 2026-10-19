import argparse
import unittest

from ci import publish, repo
from ci.registry import Registry
from ci.tests.fake_registry import FakeRegistry
from ci.tests.helpers import TempRepo, config, write_package

NS = "blsq/openclinic-config"


def fixture(root):
    write_package(root, "countries/mr", "mr", "country", {"config.yaml": config({"currency": "MRU"})}, version="1.2.0")
    write_package(root, "countries/mr", "mr-cs", "type", base="mr", version="0.3.1")
    write_package(root, "shared", "cnam", "layer")


class PlanTest(unittest.TestCase):

    def setUp(self):
        self.fake = FakeRegistry()
        self.reg = Registry(self.fake.host, insecure=True)

    def tearDown(self):
        self.fake.close()

    def plan(self, root):
        return [(a.package.name, a.what, a.reason.split(" ")[0] if a.reason else "") for a in publish.plan(repo.load(root), self.reg, NS)]

    def test_nothing_published_builds_countries_first(self):
        with TempRepo() as root:
            fixture(root)
            self.assertEqual([("mr", "build", ""), ("mr-cs", "build", ""), ("cnam", "build", "")], self.plan(root))
            self.assertEqual("mr:1.2.0", publish.plan(repo.load(root), self.reg, NS)[1].base)

    def test_published_with_the_same_content_is_skipped(self):
        with TempRepo() as root:
            fixture(root)
            r = repo.load(root)
            self.fake.put_image(f"{NS}/mr", "1.2.0", {publish.LABEL_HASH: r.by_name("mr").content_hash()})
            self.fake.put_image(f"{NS}/mr-cs", "0.3.1", {publish.LABEL_HASH: r.by_name("mr-cs").content_hash(), publish.LABEL_BASE: "mr:1.2.0"})
            self.assertEqual([("mr", "skip", "published"), ("mr-cs", "skip", "published"), ("cnam", "build", "")], self.plan(root))

    def test_T2_published_with_other_content(self):
        with TempRepo() as root:
            fixture(root)
            self.fake.put_image(f"{NS}/cnam", "1.0.0", {publish.LABEL_HASH: "0" * 64})
            self.assertIn(("cnam", "refuse", "T2"), self.plan(root))

    def test_T3_a_type_published_on_another_country_version(self):
        with TempRepo() as root:
            fixture(root)
            r = repo.load(root)
            self.fake.put_image(f"{NS}/mr-cs", "0.3.1", {publish.LABEL_HASH: r.by_name("mr-cs").content_hash(), publish.LABEL_BASE: "mr:1.1.0"})
            self.assertIn(("mr-cs", "refuse", "T3"), self.plan(root))

    def test_a_refusal_builds_nothing(self):
        with TempRepo() as root:
            fixture(root)
            self.fake.put_image(f"{NS}/cnam", "1.0.0", {publish.LABEL_HASH: "0" * 64})
            args = argparse.Namespace(registry=self.fake.host, namespace=NS, insecure=True, dry_run=False, no_public_check=True)
            built = []
            original = publish.build
            publish.build = lambda *a, **k: built.append(a)
            try:
                self.assertEqual(1, publish.main(root, args))
            finally:
                publish.build = original
            self.assertEqual([], built)

    def test_a_skipped_package_still_has_to_be_public(self):
        # a first run fails on a private package; the next one finds the tag and skips it, and must fail again
        with TempRepo() as root:
            fixture(root)
            r = repo.load(root)
            private = FakeRegistry(deny_anonymous_token=True)
            try:
                for p in r.packages:
                    labels = {publish.LABEL_HASH: p.content_hash()}
                    if p.level == "type":
                        labels[publish.LABEL_BASE] = "mr:1.2.0"
                    private.put_image(f"{NS}/{p.name}", p.version_text, labels)
                import os
                os.environ["REGISTRY_TOKEN"] = "secret"
                try:
                    args = argparse.Namespace(registry=private.host, namespace=NS, insecure=True, dry_run=False, no_public_check=False)
                    self.assertEqual(1, publish.main(root, args))
                    args.no_public_check = True
                    self.assertEqual(0, publish.main(root, args))
                finally:
                    del os.environ["REGISTRY_TOKEN"]
            finally:
                private.close()

    def test_the_dockerfile(self):
        self.assertEqual("FROM scratch\nARG NAME\nCOPY ${NAME}/ /${NAME}/\n", publish.dockerfile(None))
        self.assertTrue(publish.dockerfile("ghcr.io/x/mr:1.2.0").startswith("FROM ghcr.io/x/mr:1.2.0\n"))


if __name__ == "__main__":
    unittest.main()
