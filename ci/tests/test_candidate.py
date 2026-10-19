import unittest

from ci.candidate import highest
from ci.semver import Version


class CandidateTest(unittest.TestCase):

    def test_the_highest_by_precedence(self):
        self.assertEqual(Version.parse("0.2.0"), highest(["0.1.0-rc.4", "0.2.0-rc.10", "0.2.0", "0.2.0-rc.9", "latest", "sha-abc"]))
        self.assertEqual(Version.parse("0.2.0-rc.10"), highest(["0.2.0-rc.9", "0.2.0-rc.10"]))
        self.assertIsNone(highest(["latest"]))


if __name__ == "__main__":
    unittest.main()
