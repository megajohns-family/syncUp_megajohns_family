"""Tests for app.auth (JWT token creation, validation, decoding)."""
import unittest
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from tests.conftest import *  # noqa: F401,F403

from app import auth
from app.auth import create_access_token, decode_token, get_current_user


class TestCreateAccessToken(unittest.TestCase):
    def test_returns_string(self):
        token = create_access_token("alice")
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)

    def test_token_contains_subject(self):
        token = create_access_token("alice")
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        self.assertEqual(payload["sub"], "alice")

    def test_token_has_expiry(self):
        token = create_access_token("alice")
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        self.assertIn("exp", payload)


class TestGetCurrentUser(unittest.TestCase):
    def test_valid_token_returns_username(self):
        token = create_access_token("alice")
        self.assertEqual(get_current_user(token), "alice")

    def test_invalid_token_raises_401(self):
        with self.assertRaises(HTTPException) as ctx:
            get_current_user("not.a.valid.token")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_empty_token_raises_401(self):
        with self.assertRaises(HTTPException) as ctx:
            get_current_user("")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_expired_token_raises_401(self):
        expired = jwt.encode(
            {"sub": "alice", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
            auth.SECRET_KEY,
            algorithm=auth.ALGORITHM,
        )
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(expired)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("expired", ctx.exception.detail.lower())

    def test_token_without_sub_raises_401(self):
        token = jwt.encode(
            {"exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            auth.SECRET_KEY,
            algorithm=auth.ALGORITHM,
        )
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(token)
        self.assertEqual(ctx.exception.status_code, 401)


class TestDecodeToken(unittest.TestCase):
    def test_valid_token_returns_subject(self):
        token = create_access_token("bob")
        self.assertEqual(decode_token(token), "bob")

    def test_invalid_token_returns_none(self):
        self.assertIsNone(decode_token("garbage"))

    def test_empty_token_returns_none(self):
        self.assertIsNone(decode_token(""))


if __name__ == "__main__":
    unittest.main()
