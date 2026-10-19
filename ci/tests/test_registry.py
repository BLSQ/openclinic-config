import unittest

from ci.registry import Registry, Unknown, split_image
from ci.tests.fake_registry import FakeRegistry


class RegistryTest(unittest.TestCase):

    def setUp(self):
        self.fake = FakeRegistry()
        self.fake.put_image("blsq/openclinic-config/mr", "1.2.0", {"be.openclinic.package.contenthash": "abc"})
        self.reg = Registry(self.fake.host, insecure=True)

    def tearDown(self):
        self.fake.close()

    def test_a_tag_that_exists_through_the_token_challenge(self):
        self.assertTrue(self.reg.exists("blsq/openclinic-config/mr", "1.2.0"))

    def test_a_tag_that_does_not(self):
        self.assertFalse(self.reg.exists("blsq/openclinic-config/mr", "1.3.0"))
        self.assertFalse(self.reg.exists("blsq/openclinic-config/never", "1.0.0"))

    def test_labels_are_read_through_the_index(self):
        self.assertEqual("abc", self.reg.labels("blsq/openclinic-config/mr", "1.2.0")["be.openclinic.package.contenthash"])

    def test_platforms(self):
        self.assertEqual(["linux/amd64", "linux/arm64"], self.reg.platforms("blsq/openclinic-config/mr", "1.2.0"))

    def test_tags(self):
        self.assertEqual(["1.2.0"], self.reg.tags("blsq/openclinic-config/mr"))

    def test_split_image(self):
        self.assertEqual(("ghcr.io", "blsq/openclinic", "0.2.0-rc.1"), split_image("ghcr.io/blsq/openclinic:0.2.0-rc.1"))
        self.assertEqual(("localhost:5000", "a/b", "1"), split_image("localhost:5000/a/b:1"))
        self.assertRaises(ValueError, split_image, "ghcr.io/blsq/openclinic")


class AnonymousTest(unittest.TestCase):
    """ghcr.io refuses an anonymous token for a repository never published as for a private one."""

    def setUp(self):
        self.fake = FakeRegistry(deny_anonymous_token=True)
        self.fake.put_image("blsq/openclinic-config/mr", "1.2.0", {})

    def tearDown(self):
        self.fake.close()

    def test_an_anonymous_caller_cannot_tell(self):
        self.assertRaises(Unknown, Registry(self.fake.host, insecure=True).exists, "blsq/openclinic-config/mr", "1.2.0")

    def test_a_caller_with_a_token_can(self):
        reg = Registry(self.fake.host, user="x", password="secret", insecure=True)
        self.assertTrue(reg.exists("blsq/openclinic-config/mr", "1.2.0"))
        self.assertFalse(reg.anonymous_pull("blsq/openclinic-config/mr", "1.2.0"), "private, as far as a site can tell")


if __name__ == "__main__":
    unittest.main()
