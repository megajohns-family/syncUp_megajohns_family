import unittest
from app.hash import hash_password, verify_password

class TestHashPassword(unittest.TestCase):
    def test_returns_string(self):
        result = hash_password("secret")
        self.assertIsInstance(result, str)

    def test_not_plaintext(self):
        result = hash_password("secret")
        self.assertNotEqual(result, "secret")

    def test_different_hashes_each_call(self):
        # argon2 uses a random salt, so two hashes of the same password differ
        h1 = hash_password("secret")
        h2 = hash_password("secret")
        self.assertNotEqual(h1, h2)

    def test_hash_nonempty(self):
        self.assertTrue(len(hash_password("x")) > 0)

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