import os
import unittest

from ci import layout, repo
from ci.tests.helpers import TempRepo, config, write_package


def rules(root):
    return sorted({p.rule for p in layout.check(repo.load(root))})


def good(root):
    write_package(root, "countries/mr", "mr", "country", {"config.yaml": config({"currency": "MRU"})})
    write_package(root, "countries/mr", "mr-cs", "type", base="mr")
    write_package(root, "countries/mr", "mr-pev", "layer", country="mr")
    write_package(root, "countries/mr", "teyarett", "site")
    write_package(root, "shared", "insurer-cnam", "layer")
    write_package(root, "shared", "demo", "project")


class LayoutTest(unittest.TestCase):

    def test_a_well_laid_out_repository_passes(self):
        with TempRepo() as root:
            good(root)
            self.assertEqual([], layout.check(repo.load(root)))

    def test_fixtures_under_ci_are_not_packages(self):
        with TempRepo() as root:
            good(root)
            write_package(root, "ci/tests/repos/x/countries/zz", "zz", "country")
            self.assertEqual(6, len(repo.load(root).packages))

    def test_L1_a_package_in_the_tooling_or_the_workflows(self):
        with TempRepo() as root:
            good(root)
            write_package(root, "ci", "x", "layer")
            write_package(root, ".github", "y", "layer")
            self.assertEqual(["L1"], rules(root))
            self.assertEqual(8, len(repo.load(root).packages))

    def test_a_symbolic_link_is_refused(self):
        with TempRepo() as root:
            good(root)
            os.symlink("../../../README.md", os.path.join(root, "shared", "demo", "notes.md"))
            problems = layout.check(repo.load(root))
            self.assertEqual(["L0"], [p.rule for p in problems])
            self.assertIn("symbolic link", problems[0].message)

    def test_L1_a_package_elsewhere(self):
        with TempRepo() as root:
            good(root)
            write_package(root, "packages", "bi", "country")
            write_package(root, "countries/mr/mr-cs", "nested", "layer")
            self.assertEqual(["L1"], rules(root))

    def test_L2_the_directory_is_the_name(self):
        with TempRepo() as root:
            good(root)
            d = write_package(root, "shared", "x", "layer")
            os.rename(d, os.path.join(root, "shared", "y"))
            self.assertEqual(["L2"], rules(root))

    def test_L3_a_name_is_unique(self):
        with TempRepo() as root:
            good(root)
            write_package(root, "countries/bi", "bi", "country")
            write_package(root, "countries/bi", "teyarett", "site")
            self.assertEqual(["L3"], rules(root))

    def test_L3_a_reserved_name(self):
        with TempRepo() as root:
            good(root)
            write_package(root, "shared", "shared", "layer")
            self.assertEqual(["L3"], rules(root))

    def test_L4_a_country_directory_holds_its_country(self):
        with TempRepo() as root:
            good(root)
            write_package(root, "countries/bi", "bi-cs", "type", base="mr")
            self.assertIn("L4", rules(root))

    def test_L4_a_country_lives_in_its_own_directory(self):
        with TempRepo() as root:
            good(root)
            write_package(root, "shared", "bi", "country")
            self.assertEqual(["L4"], rules(root))

    def test_L5_a_type_lives_under_its_country(self):
        with TempRepo() as root:
            good(root)
            write_package(root, "shared", "mr-hd", "type", base="mr")
            self.assertEqual(["L5"], rules(root))
        with TempRepo() as root:
            good(root)
            write_package(root, "countries/bi", "bi", "country")
            write_package(root, "countries/bi", "bi-cs", "type", base="mr")
            self.assertEqual(["L5"], rules(root))

    def test_L6_a_layer_names_its_directory_s_country(self):
        with TempRepo() as root:
            good(root)
            write_package(root, "countries/mr", "mr-vih", "layer")
            self.assertEqual(["L6"], rules(root))
        with TempRepo() as root:
            good(root)
            write_package(root, "shared", "mr-vih", "layer", country="mr")
            self.assertEqual(["L6"], rules(root))

    def test_L8_the_country_named_exists(self):
        with TempRepo() as root:
            good(root)
            write_package(root, "countries/mr", "mr-bad", "layer", country="mr")
            write_package(root, "countries/mr", "mr-hd", "type", base="mr")
            self.assertEqual([], rules(root))
            write_package(root, "countries/zz", "zz-cs", "type", base="zz")
            self.assertEqual(["L4", "L8"], rules(root))

    def test_an_unreadable_manifest_is_a_problem(self):
        with TempRepo() as root:
            good(root)
            d = write_package(root, "shared", "broken", "layer")
            with open(os.path.join(d, "package.yaml"), "w") as f:
                f.write("name: [unclosed\n")
            self.assertEqual(["L0"], rules(root))

    def test_a_country_without_its_own_owner_is_a_warning(self):
        with TempRepo() as root:
            good(root)
            r = repo.load(root)
            self.assertEqual(1, len(layout.warnings(r, "* @someone\n")))
            self.assertEqual([], layout.warnings(r, "* @someone\n/countries/mr/ @mr-reviewers\n"))


class ContentHashTest(unittest.TestCase):

    def test_the_hash_config_apply_computes(self):
        # Computed for these two files by OpenClinic's own PackageReader.contentHash, run from the
        # config.jar of an image built from the SP1/SP2 branch (2026-10-19): the value a site's
        # oc_config_packages.contenthash holds once it applied them.
        files = {"package.yaml": b"name: mr\n", "config.yaml": "currency: MRU # é\n".encode("utf-8")}
        self.assertEqual(EXPECTED, repo.content_hash(files))

    def test_the_path_is_part_of_the_hash(self):
        self.assertNotEqual(repo.content_hash({"a": b"x"}), repo.content_hash({"b": b"x"}))


EXPECTED = "76bbd3d503e4496413ef0364a39ca8392b886eb2307dd7096efd26cac5cb9b62"

if __name__ == "__main__":
    unittest.main()
