import os
import tempfile
import unittest

from ci import replay, repo, stacks
from ci.tests.helpers import TempRepo, write_package


def report(outcome="written", files=None, named=None):
    return {"run": {"command": "export", "outcome": outcome, "message": ""},
            "package": {"name": "round-trip", "level": "site", "version": "0.0.0", "files": files or {}},
            "named": named or [], "problems": []}


class EligibilityTest(unittest.TestCase):

    def packages(self, **requires):
        with TempRepo() as root:
            for name, req in requires.items():
                write_package(root, "shared", name, "layer", requires=req)
            return repo.load(root).packages

    def test_requires_is_checked_against_the_release_and_the_candidate_is_named(self):
        pkgs = self.packages(release=">=0.2.0", candidate=">=0.2.0-rc.2", later=">=0.3.0", older=">=0.1.0 <0.2.0")
        eligible, notes = replay.eligibility(pkgs, "0.2.0-rc.2")
        self.assertEqual({"release": True, "candidate": True, "later": False, "older": False}, eligible)
        self.assertEqual(["later 1.0.0 requires >=0.3.0: not replayed on 0.2.0 (candidate 0.2.0-rc.2)",
                          "older 1.0.0 requires >=0.1.0 <0.2.0: not replayed on 0.2.0 (candidate 0.2.0-rc.2)",
                          "release 1.0.0 requires >=0.2.0: replayed on 0.2.0; a site running the candidate 0.2.0-rc.2 refuses it"],
                         sorted(notes))

    def test_a_release_names_nothing_it_replays(self):
        eligible, notes = replay.eligibility(self.packages(release=">=0.2.0"), "0.2.0")
        self.assertEqual({"release": True}, eligible)
        self.assertEqual([], notes)


class RoundTripTest(unittest.TestCase):

    def test_export_is_told_from_an_image_without_it(self):
        # SP4's usage error, then SP1's unknown command: both exit 2
        self.assertTrue(replay.export_available(2, "config export: --name is missing\nusage: config apply …"))
        self.assertFalse(replay.export_available(2, "config: unknown command 'export'\nusage: config apply …"))
        self.assertFalse(replay.export_available(1, "openclinic: DB_HOST is required"))

    def test_the_probe_is_a_name_the_stack_does_not_hold(self):
        with TempRepo() as root:
            write_package(root, "countries/mr", "mr", "country")
            write_package(root, "countries/mr", "round-trip", "layer", country="mr")
            write_package(root, "countries/mr", "round-trip-1", "layer", country="mr")
            plan = stacks.plan(repo.load(root))
            self.assertEqual("round-trip", replay.probe_name(plan[0]))
            self.assertEqual("round-trip-2", replay.probe_name(plan[1]))

    def test_nothing_given_back_passes(self):
        named = [{"kind": "profiles", "element": "[\"admin\"]", "field": "", "value": "", "reason": "cannot name", "detail": "x"}]
        self.assertIsNone(replay.round_trip_verdict(0, report(named=named), "/nonexistent"))

    def test_a_file_given_back_fails_and_shows_it(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "config.yaml"), "w") as f:
                f.write("apiVersion: openclinic/v1alpha1\nkind: Config\nkeys:\n  test.sp5.country: Xanadu\n")
            why = replay.round_trip_verdict(0, report(files={"config.yaml": 1}), d)
        self.assertIn("is not empty", why)
        self.assertIn("config.yaml: 1 element(s)", why)
        self.assertIn("test.sp5.country: Xanadu", why)

    def test_a_value_the_database_does_not_hold_fails(self):
        named = [{"kind": "config", "element": "[\"test.sp5.country\"]", "field": "value", "value": "Xanadou",
                  "reason": "another level", "detail": "xa 1.0.0 sets 'Xanadu'"}]
        why = replay.round_trip_verdict(0, report(named=named), "/nonexistent")
        self.assertIn("the database holds 'Xanadou'", why)

    def test_a_refused_or_failed_export_fails(self):
        self.assertIn("exit 1, outcome refused", replay.round_trip_verdict(1, report(outcome="refused"), "/nonexistent"))
        self.assertIn("exit 3, outcome None", replay.round_trip_verdict(3, {}, "/nonexistent"))


if __name__ == "__main__":
    unittest.main()
