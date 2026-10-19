import os
import tempfile
import unittest

from ci import repo, stacks
from ci.tests.helpers import TempRepo, write_package


def names(root):
    return [(s.name, s.describe()) for s in stacks.plan(repo.load(root))]


class StacksTest(unittest.TestCase):

    def test_the_table_of_the_spec(self):
        with TempRepo() as root:
            write_package(root, "countries/mr", "mr", "country")
            write_package(root, "countries/mr", "mr-cs", "type", base="mr")
            write_package(root, "countries/mr", "mr-hd", "type", base="mr")
            write_package(root, "countries/mr", "mr-pev", "layer", country="mr")
            write_package(root, "countries/mr", "teyarett", "site")
            write_package(root, "countries/mr", "mr-project", "project")
            write_package(root, "countries/bi", "bi", "country")
            write_package(root, "countries/bi", "bi-pev", "layer", country="bi")
            write_package(root, "shared", "cnam", "layer")
            write_package(root, "shared", "demo", "project")
            write_package(root, "shared", "lonely", "site")
            self.assertEqual([
                ("bi", "bi"),
                ("bi + its layers", "bi | bi-pev | cnam"),
                ("mr", "mr"),
                ("mr + its layers", "mr | mr-pev | cnam"),
                ("mr-cs", "mr + mr-cs"),
                ("mr-cs + its layers", "mr + mr-cs | mr-pev | cnam"),
                ("mr-hd", "mr + mr-hd"),
                ("mr-hd + its layers", "mr + mr-hd | mr-pev | cnam"),
                ("demo", "demo"),
                ("lonely", "lonely"),
                ("mr-project", "mr-project"),
                ("mr + mr-project", "mr | mr-project"),
                ("mr + teyarett", "mr | teyarett"),
            ], names(root))

    def test_a_repository_with_no_country(self):
        with TempRepo() as root:
            write_package(root, "shared", "cnam", "layer")
            write_package(root, "shared", "pev", "layer")
            self.assertEqual([("cnam", "cnam"), ("pev", "pev")], names(root))

    def test_restrict_drops_a_layer_and_skips_a_base(self):
        with TempRepo() as root:
            write_package(root, "countries/mr", "mr", "country")
            write_package(root, "countries/mr", "mr-pev", "layer", country="mr")
            write_package(root, "shared", "cnam", "layer")
            plan = stacks.plan(repo.load(root))
            wide = plan[1]
            self.assertEqual("mr | cnam", wide.restrict(lambda p: p.name != "mr-pev").describe())
            self.assertIsNone(wide.restrict(lambda p: p.name not in ("mr-pev", "cnam")))
            self.assertIsNone(plan[0].restrict(lambda p: p.name != "mr"))

    def test_stage_has_the_chart_s_layout(self):
        with TempRepo() as root, tempfile.TemporaryDirectory() as out:
            write_package(root, "countries/mr", "mr", "country", {"config.yaml": "x"})
            write_package(root, "countries/mr", "mr-cs", "type", base="mr")
            write_package(root, "shared", "cnam", "layer")
            r = repo.load(root)
            wide = [s for s in stacks.plan(r) if s.name == "mr-cs + its layers"][0]
            stacks.stage(root, wide, os.path.join(out, "p"))
            found = sorted(os.path.relpath(os.path.join(d, f), out) for d, _, fs in os.walk(out) for f in fs)
            self.assertEqual(["p/0/mr-cs/package.yaml", "p/0/mr/config.yaml", "p/0/mr/package.yaml", "p/1/cnam/package.yaml"], found)
            self.assertTrue(os.stat(os.path.join(out, "p/0/mr/config.yaml")).st_mode & 0o004)


if __name__ == "__main__":
    unittest.main()
