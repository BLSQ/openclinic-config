import os
import shutil
import subprocess
import unittest

from ci import repo, versions
from ci.tests.helpers import TempRepo, config, write_package


def base_repo(root):
    write_package(root, "countries/mr", "mr", "country", {"config.yaml": config({"currency": "MRU"})}, version="1.2.0")
    write_package(root, "countries/mr", "mr-cs", "type", base="mr", version="0.3.1")
    write_package(root, "countries/mr", "mr-hd", "type", base="mr", version="0.1.0")
    write_package(root, "shared", "cnam", "layer", {"config.yaml": config({"x": "1"})}, version="1.0.0")


def run(edit):
    with TempRepo() as a, TempRepo() as b:
        base_repo(a)
        base_repo(b)
        edit(b)
        problems, notes = versions.compare(repo.load(a), repo.load(b))
        return sorted(p.rule for p in problems), problems, notes


class VersionsTest(unittest.TestCase):

    def test_nothing_changed(self):
        self.assertEqual([], run(lambda b: None)[0])

    def test_V1_files_changed_without_a_new_version(self):
        rules, problems, _ = run(lambda b: write_package(b, "shared", "cnam", "layer", {"config.yaml": config({"x": "2"})}, version="1.0.0"))
        self.assertEqual(["V1"], rules)
        self.assertIn("cnam:1.0.0", problems[0].message)

    def test_a_new_version_with_new_files_passes(self):
        rules, _, notes = run(lambda b: write_package(b, "shared", "cnam", "layer", {"config.yaml": config({"x": "2"})}, version="1.1.0"))
        self.assertEqual([], rules)
        self.assertIn("cnam: 1.0.0 -> 1.1.0", notes)

    def test_V2_a_version_that_goes_down(self):
        self.assertEqual(["V2"], run(lambda b: write_package(b, "shared", "cnam", "layer", {"config.yaml": config({"x": "2"})}, version="1.0.0-rc.1"))[0])

    def test_V3_a_country_that_moves_alone(self):
        rules, problems, _ = run(lambda b: write_package(b, "countries/mr", "mr", "country", {"config.yaml": config({"currency": "MRU"})}, version="1.3.0"))
        self.assertEqual(["V3", "V3"], rules)
        self.assertEqual({"countries/mr/mr-cs/package.yaml", "countries/mr/mr-hd/package.yaml"}, {p.path for p in problems})

    def test_V3_a_country_that_moves_with_its_types(self):
        def edit(b):
            write_package(b, "countries/mr", "mr", "country", {"config.yaml": config({"currency": "MRU"})}, version="1.3.0")
            write_package(b, "countries/mr", "mr-cs", "type", base="mr", version="0.3.2")
            write_package(b, "countries/mr", "mr-hd", "type", base="mr", version="0.1.1")
        self.assertEqual([], run(edit)[0])

    def test_V4_a_package_removed_is_said(self):
        rules, _, notes = run(lambda b: shutil.rmtree(os.path.join(b, "shared", "cnam")))
        self.assertEqual([], rules)
        self.assertTrue(any("cnam: removed" in n for n in notes))

    def test_V5_a_rename_is_a_removal_and_an_addition(self):
        def edit(b):
            shutil.rmtree(os.path.join(b, "shared", "cnam"))
            write_package(b, "shared", "insurer-cnam", "layer", {"config.yaml": config({"x": "1"})}, version="1.0.0")
        rules, _, notes = run(edit)
        self.assertEqual([], rules)
        self.assertTrue(any("insurer-cnam: new" in n for n in notes))

    def test_a_new_package(self):
        self.assertEqual([], run(lambda b: write_package(b, "shared", "pev", "layer", version="0.0.1"))[0])

    def test_load_ref_reads_an_empty_commit(self):
        # the repository's first main is one empty commit: its archive is a tar of zero blocks, no entry
        with TempRepo() as root:
            git = ["git", "-C", root, "-c", "user.name=t", "-c", "user.email=t@t"]
            subprocess.run(git[:3] + ["init", "-q"], check=True)
            subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "empty"], check=True)
            self.assertEqual([], versions.load_ref(root, "HEAD").packages)

    def test_load_ref_reads_a_commit(self):
        with TempRepo() as root:
            base_repo(root)
            git = ["git", "-C", root, "-c", "user.name=t", "-c", "user.email=t@t"]
            subprocess.run(git[:3] + ["init", "-q"], check=True)
            subprocess.run(git + ["add", "-A"], check=True)
            subprocess.run(git + ["commit", "-qm", "base"], check=True)
            r = versions.load_ref(root, "HEAD")
            self.assertEqual({"mr", "mr-cs", "mr-hd", "cnam"}, {p.name for p in r.packages})


if __name__ == "__main__":
    unittest.main()
