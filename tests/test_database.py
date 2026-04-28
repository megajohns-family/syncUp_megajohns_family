import unittest
from unittest.mock import MagicMock, patch


class TestVerifyFirebaseConnection(unittest.TestCase):
    """Tests for verify_firebase_connection()"""

    def test_raises_when_env_vars_missing(self):
        import app.database as db
        with patch("os.getenv", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                db.verify_firebase_connection()
            self.assertIn("Missing required environment variables", str(ctx.exception))

    def test_raises_on_invalid_json_service_account(self):
        import app.database as db
        env = {"FIREBASE_SERVICE_ACCOUNT": "not-json", "SECRET_KEY": "s"}
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                db.verify_firebase_connection()
            self.assertIn("not valid JSON", str(ctx.exception))

    def test_raises_when_firebase_init_fails(self):
        import app.database as db
        env = {"FIREBASE_SERVICE_ACCOUNT": '{"type":"service_account"}', "SECRET_KEY": "s"}
        with patch.dict("os.environ", env, clear=True):
            with patch("firebase_admin._apps", {}):
                with patch("firebase_admin.credentials.Certificate", side_effect=Exception("bad cred")):
                    with self.assertRaises(RuntimeError) as ctx:
                        db.verify_firebase_connection()
                    self.assertIn("Failed to initialize Firebase Admin SDK", str(ctx.exception))

    def test_raises_when_firestore_client_fails(self):
        import app.database as db
        env = {"FIREBASE_SERVICE_ACCOUNT": '{"type":"service_account"}', "SECRET_KEY": "s"}
        with patch.dict("os.environ", env, clear=True):
            with patch("firebase_admin._apps", {"default": True}):
                with patch("firebase_admin.firestore.client", side_effect=Exception("no client")):
                    with self.assertRaises(RuntimeError) as ctx:
                        db.verify_firebase_connection()
                    self.assertIn("Failed to create Firestore client", str(ctx.exception))

    def test_raises_when_health_check_fails(self):
        import app.database as db
        env = {"FIREBASE_SERVICE_ACCOUNT": '{"type":"service_account"}', "SECRET_KEY": "s"}
        mock_client = MagicMock()
        mock_client.collection.return_value.document.return_value.get.side_effect = Exception("timeout")
        with patch.dict("os.environ", env, clear=True):
            with patch("firebase_admin._apps", {"default": True}):
                with patch("firebase_admin.firestore.client", return_value=mock_client):
                    with self.assertRaises(RuntimeError) as ctx:
                        db.verify_firebase_connection()
                    self.assertIn("Firestore connectivity test failed", str(ctx.exception))


class TestSaveToFirestore(unittest.TestCase):
    """Tests for save_to_firestore()"""

    def test_save_calls_set_on_correct_collection_and_doc(self):
        import app.database as db
        mock_db = MagicMock()
        with patch.object(db, "_get_db", return_value=mock_db):
            db.save_to_firestore("boards", "board_abc", {"name": "MyBoard"})
            mock_db.collection.assert_called_once_with("boards")
            mock_db.collection.return_value.document.assert_called_once_with("board_abc")
            mock_db.collection.return_value.document.return_value.set.assert_called_once_with({"name": "MyBoard"})

    def test_save_passes_data_unchanged(self):
        import app.database as db
        mock_db = MagicMock()
        data = {"lists": {1: {"name": "Todo"}}, "owner": "alice"}
        with patch.object(db, "_get_db", return_value=mock_db):
            db.save_to_firestore("boards", "board_xyz", data)
            mock_db.collection.return_value.document.return_value.set.assert_called_once_with(data)

    def test_save_to_users_collection(self):
        import app.database as db
        mock_db = MagicMock()
        with patch.object(db, "_get_db", return_value=mock_db):
            db.save_to_firestore("users", "users", {"users": {"alice": "hashed_pw"}})
            mock_db.collection.assert_called_once_with("users")
            mock_db.collection.return_value.document.assert_called_once_with("users")


class TestLoadFromFirestoreRaw(unittest.TestCase):
    """Tests for load_from_firestore_raw()"""

    def test_returns_dict_when_doc_exists(self):
        import app.database as db
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "TestBoard", "owner": "bob"}
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        with patch.object(db, "_get_db", return_value=mock_db):
            result = db.load_from_firestore_raw("boards", "board_123")
            self.assertEqual(result, {"name": "TestBoard", "owner": "bob"})

    def test_returns_none_when_doc_missing(self):
        import app.database as db
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        with patch.object(db, "_get_db", return_value=mock_db):
            result = db.load_from_firestore_raw("boards", "board_missing")
            self.assertIsNone(result)

    def test_queries_correct_collection_and_doc(self):
        import app.database as db
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {}
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        with patch.object(db, "_get_db", return_value=mock_db):
            db.load_from_firestore_raw("users", "users")
            mock_db.collection.assert_called_once_with("users")
            mock_db.collection.return_value.document.assert_called_once_with("users")

    def test_returns_empty_dict_when_to_dict_returns_empty(self):
        import app.database as db
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {}
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        with patch.object(db, "_get_db", return_value=mock_db):
            result = db.load_from_firestore_raw("boards", "board_empty")
            self.assertEqual(result, {})


class TestDeleteFromFirestore(unittest.TestCase):
    """Tests for delete_from_firestore()"""

    def test_calls_delete_on_correct_doc(self):
        import app.database as db
        mock_db = MagicMock()
        with patch.object(db, "_get_db", return_value=mock_db):
            db.delete_from_firestore("boards", "board_abc")
            mock_db.collection.assert_called_once_with("boards")
            mock_db.collection.return_value.document.assert_called_once_with("board_abc")
            mock_db.collection.return_value.document.return_value.delete.assert_called_once()


class TestGetUserBoards(unittest.TestCase):
    """Tests for get_user_boards()"""

    def _make_doc(self, doc_id, data):
        doc = MagicMock()
        doc.id = doc_id
        doc.to_dict.return_value = data
        return doc

    def test_returns_owned_boards(self):
        import app.database as db
        owned_doc = self._make_doc("board_abc", {"name": "My Board", "owner": "alice", "users": []})
        mock_db = MagicMock()
        mock_db.collection.return_value.where.return_value.stream.side_effect = [
            iter([owned_doc]),
            iter([]),
        ]
        with patch.object(db, "_get_db", return_value=mock_db):
            result = db.get_user_boards("alice")
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["id"], "abc")
            self.assertEqual(result[0]["name"], "My Board")
            self.assertEqual(result[0]["owner"], "alice")

    def test_returns_shared_boards(self):
        import app.database as db
        shared_doc = self._make_doc("board_xyz", {"name": "Shared", "owner": "bob", "users": ["alice"]})
        mock_db = MagicMock()
        mock_db.collection.return_value.where.return_value.stream.side_effect = [
            iter([]),
            iter([shared_doc]),
        ]
        with patch.object(db, "_get_db", return_value=mock_db):
            result = db.get_user_boards("alice")
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["id"], "xyz")
            self.assertEqual(result[0]["owner"], "bob")

    def test_no_duplicate_boards_when_owner_also_in_users(self):
        import app.database as db
        doc = self._make_doc("board_abc", {"name": "My Board", "owner": "alice", "users": ["alice"]})
        mock_db = MagicMock()
        mock_db.collection.return_value.where.return_value.stream.side_effect = [
            iter([doc]),
            iter([doc]),
        ]
        with patch.object(db, "_get_db", return_value=mock_db):
            result = db.get_user_boards("alice")
            self.assertEqual(len(result), 1)

    def test_returns_empty_list_when_no_boards(self):
        import app.database as db
        mock_db = MagicMock()
        mock_db.collection.return_value.where.return_value.stream.side_effect = [
            iter([]),
            iter([]),
        ]
        with patch.object(db, "_get_db", return_value=mock_db):
            result = db.get_user_boards("alice")
            self.assertEqual(result, [])

    def test_strips_board_prefix_from_doc_id(self):
        import app.database as db
        doc = self._make_doc("board_myid123", {"name": "X", "owner": "carol", "users": []})
        mock_db = MagicMock()
        mock_db.collection.return_value.where.return_value.stream.side_effect = [
            iter([doc]),
            iter([]),
        ]
        with patch.object(db, "_get_db", return_value=mock_db):
            result = db.get_user_boards("carol")
            self.assertEqual(result[0]["id"], "myid123")


class TestGetDbGuard(unittest.TestCase):
    """Tests that _get_db() raises before initialization."""

    def test_raises_runtime_error_before_init(self):
        import app.database as db
        original = db._db
        db._db = None
        try:
            with self.assertRaises(RuntimeError) as ctx:
                db._get_db()
            self.assertIn("not initialized", str(ctx.exception))
        finally:
            db._db = original


if __name__ == "__main__":
    unittest.main()