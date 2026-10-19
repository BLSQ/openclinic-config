import unittest

from ci.semver import DEV, Range, Version


class VersionTest(unittest.TestCase):
    """The cases of OpenClinic's tools/config VersionTest, so that both readers order alike."""

    def test_orders_as_semver(self):
        v = Version.parse
        self.assertLess(v("0.3.0-rc.1"), v("0.3.0"))
        self.assertLess(v("0.3.0-rc.1"), v("0.3.0-rc.2"))
        self.assertGreater(v("0.3.0-rc.10"), v("0.3.0-rc.9"))
        self.assertGreater(v("0.3.0"), v("0.2.9"))
        self.assertGreater(v("1.0.0"), v("0.99.99"))
        self.assertLess(v("0.3.0-alpha"), v("0.3.0-beta"))
        self.assertLess(v("0.3.0-1"), v("0.3.0-a"))
        self.assertLess(v("1.0.0-alpha"), v("1.0.0-alpha.1"))
        self.assertEqual(v("1.2.3"), v("1.2.3"))
        self.assertEqual("0.1.0-rc.4", str(v("0.1.0-rc.4")))

    def test_refuses_what_is_not_a_version(self):
        for text in ("1.2", "v1.2.3", "01.2.3", "1.2.3-", "", None, "1.2.3-a..b", "1.0.0-rc.01"):
            with self.subTest(text=text):
                self.assertRaises(ValueError, Version.parse, text)

    def test_the_release_of_a_candidate(self):
        self.assertEqual(Version.parse("0.2.0"), Version.parse("0.2.0-rc.1").release())
        self.assertEqual(Version.parse("0.2.0"), Version.parse("0.2.0").release())

    def test_the_development_version(self):
        self.assertTrue(Version.parse("0.0.0-dev").is_dev())
        self.assertFalse(Version.parse("0.0.0").is_dev())


class RangeTest(unittest.TestCase):

    def test_at_least_and_below(self):
        r = Range.parse(">=0.2.0 <0.3.0")
        self.assertTrue(r.includes(Version.parse("0.2.0")))
        self.assertTrue(r.includes(Version.parse("0.2.9")))
        self.assertFalse(r.includes(Version.parse("0.3.0")))
        self.assertFalse(r.includes(Version.parse("0.1.9")))
        self.assertTrue(r.includes(Version.parse("0.2.5-rc.1")))
        self.assertEqual(">=0.2.0 <0.3.0", str(r))

    def test_a_candidate_is_before_its_release(self):
        self.assertFalse(Range.parse(">=0.3.0").includes(Version.parse("0.3.0-rc.1")))
        self.assertTrue(Range.parse(">=0.3.0").includes(Version.parse("0.3.0-rc.1").release()))

    def test_the_development_version_is_in_every_range(self):
        self.assertTrue(Range.parse(">=9.0.0 <9.0.1").includes(DEV))

    def test_refuses_other_operators_and_empty_ranges(self):
        for text in ("0.2.0", "^0.2.0", ">=0.2.0 <=0.3.0", ">=0.3.0 <0.2.0", ">=0.3.0 <0.3.0"):
            with self.subTest(text=text):
                self.assertRaises(ValueError, Range.parse, text)


if __name__ == "__main__":
    unittest.main()
