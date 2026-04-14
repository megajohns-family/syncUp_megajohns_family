# Tests for authentication functionality: token creation and validation
import unittest
from app.auth import create_access_token, get_current_user
from fastapi import HTTPException

# Test suite for auth-related functions
class TestAuth(unittest.TestCase):

    def test_create_access_token_returns_string(self):
        # Check if token is created and is a nonempty string
        token = create_access_token("user1")
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

    def test_get_current_user_valid_token(self):
        # verify that a valid token returns the correct username
        token = create_access_token("user1")
        username = get_current_user(token)
        self.assertEqual(username, "user1")

    def test_get_current_user_invalid_token(self):
        # Ensure invalid token raises HTTP 401 error
        with self.assertRaises(HTTPException) as context:
            get_current_user("invalid.token.here")

        self.assertEqual(context.exception.status_code, 401)

    def test_get_current_user_empty_token(self):
        # Ensure empty token also raises an exception
        with self.assertRaises(HTTPException):
            get_current_user("")

# Run tests when the file is executed directly
if __name__ == "__main__":
    unittest.main()