import time
import unittest
from unittest.mock import MagicMock, patch

import app.database as db


def mock_response(status=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data or {}
    resp.raise_for_status.side_effect = None if status < 400 else Exception("HTTP error")
    return resp


class TestDatabase(unittest.TestCase):

    def setUp(self):
        db._cache.clear()

    def tearDown(self):
        db._cache.clear()

    def test_to_from_value_roundtrip(self):
        data = {
            "str": "hello",
            "int": 123,
            "float": 1.23,
            "bool": True,
            "none": None,
            "list": [1, "a", False],
            "dict": {"nested": 42},
        }

        firestore = db._dict_to_fields(data)
        result = db._fields_to_dict(firestore)

        self.assertEqual(result, data)

    @patch.object(db, "_session")
    def test_save_to_firestore(self, mock_session):
        mock_session.patch.return_value = mock_response()

        data = {"a": 1}
        db.save_to_firestore("doc1", data)

        self.assertIn("doc1", db._cache)
        cached_data, _ = db._cache["doc1"]
        self.assertEqual(cached_data, data)

        mock_session.patch.assert_called_once()

    @patch.object(db, "_session")
    def test_load_from_firestore_success(self, mock_session):
        firestore_response = {
            "fields": {
                "a": {"integerValue": "1"},
                "b": {"stringValue": "test"},
            }
        }

        mock_session.get.return_value = mock_response(json_data=firestore_response)

        result = db.load_from_firestore_raw("doc1")

        self.assertEqual(result, {"a": 1, "b": "test"})
        self.assertIn("doc1", db._cache)

    @patch.object(db, "_session")
    def test_load_from_firestore_404(self, mock_session):
        mock_session.get.return_value = mock_response(status=404)

        result = db.load_from_firestore_raw("missing")

        self.assertIsNone(result)
        self.assertIn("missing", db._cache)
        self.assertIsNone(db._cache["missing"][0])

    @patch.object(db, "_session")
    def test_cache_hit(self, mock_session):
        db._cache["doc1"] = ({"cached": True}, time.monotonic())

        result = db.load_from_firestore_raw("doc1")

        self.assertEqual(result, {"cached": True})
        mock_session.get.assert_not_called()

    @patch.object(db, "_session")
    def test_cache_expired(self, mock_session):
        db._cache["doc1"] = ({"old": True}, time.monotonic() - 10)

        firestore_response = {
            "fields": {"new": {"booleanValue": True}}
        }

        mock_session.get.return_value = mock_response(json_data=firestore_response)

        result = db.load_from_firestore_raw("doc1")

        self.assertEqual(result, {"new": True})
        mock_session.get.assert_called_once()

    def test_invalidate_cache(self):
        db._cache["doc1"] = ({"a": 1}, time.monotonic())

        db.invalidate_cache("doc1")

        self.assertNotIn("doc1", db._cache)


if __name__ == "__main__":
    unittest.main()