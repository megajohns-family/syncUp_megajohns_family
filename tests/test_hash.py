"""Tests for app.hash (argon2 password hashing helpers)."""
import unittest

from tests.conftest import *  # noqa: F401,F403  (ensure sys.path is set)

from app.hash import hash_password, verify_password


class TestHashPassword(unittest.TestCase):
    def test_returns_string(self):
        self.assertIsInstance(hash_password("secret"), str)

    def test_not_plaintext(self):
        self.assertNotEqual(hash_password("secret"), "secret")

    def test_different_salt_each_call(self):
        # argon2 uses a random salt — two hashes of the same password must differ
        self.assertNotEqual(hash_password("secret"), hash_password("secret"))

    def test_hash_nonempty(self):
        self.assertGreater(len(hash_password("x")), 0)


class TestVerifyPassword(unittest.TestCase):
    def setUp(self):
        self.password = "myPassword123"
        self.hashed = hash_password(self.password)

    def test_correct_password(self):
        self.assertTrue(verify_password(self.password, self.hashed))

    def test_wrong_password(self):
        self.assertFalse(verify_password("wrongPassword", self.hashed))

    def test_empty_password_against_hash(self):
        self.assertFalse(verify_password("", self.hashed))

    def test_invalid_hash_returns_false(self):
        self.assertFalse(verify_password("secret", "not-a-valid-hash"))

    def test_empty_hash_returns_false(self):
        self.assertFalse(verify_password("secret", ""))

    def test_different_passwords_same_hash_fails(self):
        other = hash_password("other")
        self.assertFalse(verify_password(self.password, other))


if __name__ == "__main__":
    unittest.main()
