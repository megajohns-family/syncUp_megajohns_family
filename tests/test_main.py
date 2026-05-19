"""
Tests for main.py FastAPI endpoints. Firebase and Firestore are mocked, so
no real network access is performed.
"""
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from tests.conftest import *  # noqa: F401,F403


# ---------------------------------------------------------------------------
# Module-level app bootstrap (one mocked Firestore for the whole test run).
# ---------------------------------------------------------------------------

def _bootstrap_app():
    """Import `main` with Firebase fully mocked out.

    The FastAPI lifespan calls ``verify_firebase_connection`` on every
    ``TestClient.__enter__``. We replace it (and ``save_to_firestore`` /
    ``get_user_boards``) with no-ops *on the imported main module* so they
    stay stubbed for the whole test session, regardless of environment.
    """
    import os
    os.environ.setdefault("FIREBASE_SERVICE_ACCOUNT", '{"type":"service_account"}')
    os.environ.setdefault("SECRET_KEY", "testsecret")

    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value.get.return_value = MagicMock()

    with patch("firebase_admin._apps", {"default": True}), \
         patch("firebase_admin.firestore.client", return_value=mock_db):
        import main  # noqa: WPS433  (intentional in-function import)

    # Permanently neutralise Firestore-touching helpers on the main module
    main.verify_firebase_connection = lambda: None
    return main


main_mod = _bootstrap_app()
app = main_mod.app


class _AppTestCase(unittest.TestCase):
    """Base class that wires up a TestClient and a fresh mocked UserManager."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=True)
        self.client.__enter__()
        self.mock_um = MagicMock()
        main_mod.user_manager = self.mock_um
        # Reset register rate-limit state between tests
        main_mod._last_register_attempt.clear()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def _login(self, username="testuser", password="pw"):
        self.mock_um.login_user.return_value = True
        response = self.client.post(
            "/users/login", json={"login": username, "password": password}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Root / static
# ---------------------------------------------------------------------------

class TestRoot(_AppTestCase):
    def test_root_redirects_to_landing_page(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertIn("landingpage", response.headers["location"])


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

class TestRegister(_AppTestCase):
    def test_register_success_returns_201(self):
        self.mock_um.register_user.return_value = True
        response = self.client.post(
            "/users/register", json={"login": "alice", "password": "pw123"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"message": "registered"})

    def test_register_duplicate_returns_400(self):
        self.mock_um.register_user.return_value = False
        response = self.client.post(
            "/users/register", json={"login": "alice", "password": "pw123"}
        )
        self.assertEqual(response.status_code, 400)

    def test_register_missing_fields_returns_422(self):
        response = self.client.post("/users/register", json={"login": "alice"})
        self.assertEqual(response.status_code, 422)

    def test_register_rate_limit_returns_429(self):
        self.mock_um.register_user.return_value = True
        first = self.client.post(
            "/users/register", json={"login": "a", "password": "pw"}
        )
        self.assertEqual(first.status_code, 201)
        second = self.client.post(
            "/users/register", json={"login": "b", "password": "pw"}
        )
        self.assertEqual(second.status_code, 429)
        self.assertIn("Retry-After", second.headers)


class TestLogin(_AppTestCase):
    def test_login_invalid_credentials_returns_401(self):
        self.mock_um.login_user.return_value = False
        response = self.client.post(
            "/users/login", json={"login": "wrong", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 401)

    def test_login_success_returns_token(self):
        self.mock_um.login_user.return_value = True
        response = self.client.post(
            "/users/login", json={"login": "alice", "password": "pw123"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")

    def test_login_missing_password_returns_422(self):
        response = self.client.post("/users/login", json={"login": "alice"})
        self.assertEqual(response.status_code, 422)


# ---------------------------------------------------------------------------
# Protected endpoints (require Bearer token)
# ---------------------------------------------------------------------------

class TestAuthGuard(_AppTestCase):
    def test_get_boards_without_token_returns_401(self):
        self.assertEqual(self.client.get("/boards").status_code, 401)

    def test_create_board_without_token_returns_401(self):
        self.assertEqual(
            self.client.post("/boards", json={"name": "X"}).status_code, 401
        )

    def test_lists_endpoint_without_token_returns_401(self):
        self.assertEqual(
            self.client.get("/boards/fake/lists").status_code, 401
        )


class TestBoardsListing(_AppTestCase):
    def test_get_boards_with_valid_token_returns_200(self):
        headers = self._login()
        with patch("main.get_user_boards", return_value=[]):
            response = self.client.get("/boards", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])

    def test_get_boards_returns_payload_from_db(self):
        headers = self._login()
        boards = [{"id": "abc", "name": "B", "owner": "testuser"}]
        with patch("main.get_user_boards", return_value=boards):
            response = self.client.get("/boards", headers=headers)
            self.assertEqual(response.json(), boards)


class TestBoardCreate(_AppTestCase):
    def test_create_board_with_token_returns_201(self):
        headers = self._login()
        with patch("main.save_to_firestore"):
            response = self.client.post(
                "/boards", json={"name": "Sprint 1"}, headers=headers
            )
            self.assertEqual(response.status_code, 201)
            self.assertIn("board_id", response.json())


# ---------------------------------------------------------------------------
# Board user management
# ---------------------------------------------------------------------------

class TestBoardUsers(_AppTestCase):
    def _board(self, owner="testuser", users=None):
        from app.models import TaskManager
        return TaskManager(board_id="abc", name="Board", owner=owner, users=users or [])

    def test_get_board_users_returns_owner_and_users(self):
        headers = self._login()
        board = self._board(users=["bob"])
        with patch("main.load_task_manager", return_value=board):
            response = self.client.get("/boards/abc/users", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"owner": "testuser", "users": ["bob"]})

    def test_get_nonexistent_board_returns_404(self):
        headers = self._login()
        with patch("main.load_task_manager", return_value=None):
            response = self.client.get("/boards/missing/lists", headers=headers)
            self.assertEqual(response.status_code, 404)

    def test_add_user_to_board_succeeds_for_owner(self):
        headers = self._login()
        board = self._board(owner="testuser")
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            response = self.client.post(
                "/boards/abc/users", json={"username": "bob"}, headers=headers
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["ok"])
            self.assertIn("bob", board.users)

    def test_add_user_forbidden_for_non_owner(self):
        headers = self._login()
        board = self._board(owner="someone_else")
        with patch("main.load_task_manager", return_value=board):
            response = self.client.post(
                "/boards/abc/users", json={"username": "bob"}, headers=headers
            )
            self.assertEqual(response.status_code, 403)

    def test_remove_user_succeeds_for_owner(self):
        headers = self._login()
        board = self._board(owner="testuser", users=["bob"])
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            response = self.client.delete(
                "/boards/abc/users/bob", headers=headers
            )
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("bob", board.users)

    def test_remove_user_forbidden_for_non_owner(self):
        headers = self._login()
        board = self._board(owner="someone_else", users=["bob"])
        with patch("main.load_task_manager", return_value=board):
            response = self.client.delete(
                "/boards/abc/users/bob", headers=headers
            )
            self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# Lists CRUD
# ---------------------------------------------------------------------------

class TestLists(_AppTestCase):
    def _board(self):
        from app.models import TaskManager
        return TaskManager(board_id="abc", name="Board", owner="testuser", users=[])

    def test_create_list_returns_201(self):
        headers = self._login()
        board = self._board()
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            response = self.client.post(
                "/boards/abc/lists", json={"name": "Todo"}, headers=headers
            )
            self.assertEqual(response.status_code, 201)
            self.assertIn("list_id", response.json())

    def test_get_lists_returns_all(self):
        headers = self._login()
        board = self._board()
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            board.add_list("Todo")
            response = self.client.get("/boards/abc/lists", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()), 1)

    def test_rename_list_success(self):
        board = self._board()
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            lid = board.add_list("Old")
            response = self.client.patch(
                f"/boards/abc/lists/{lid}", json={"name": "New"}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(board.lists[lid].name, "New")

    def test_rename_missing_list_returns_404(self):
        board = self._board()
        with patch("main.load_task_manager", return_value=board):
            response = self.client.patch(
                "/boards/abc/lists/999", json={"name": "X"}
            )
            self.assertEqual(response.status_code, 404)

    def test_delete_list_success(self):
        board = self._board()
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            lid = board.add_list("L")
            response = self.client.delete(f"/boards/abc/lists/{lid}")
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(lid, board.lists)

    def test_reorder_lists_success(self):
        board = self._board()
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            l1 = board.add_list("A")
            l2 = board.add_list("B")
            response = self.client.put(
                "/boards/abc/lists/order", json={"order": [l2, l1]}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(board.list_order, [l2, l1])

    def test_reorder_lists_invalid_returns_400(self):
        board = self._board()
        with patch("main.load_task_manager", return_value=board):
            board.add_list("A")
            response = self.client.put(
                "/boards/abc/lists/order", json={"order": [999]}
            )
            self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# Task CRUD
# ---------------------------------------------------------------------------

class TestTasks(_AppTestCase):
    def _board_with_list(self):
        from app.models import TaskManager
        board = TaskManager(board_id="abc", name="B", owner="testuser", users=[])
        with patch("main.save_to_firestore"):
            list_id = board.add_list("My List")
        return board, list_id

    def test_create_task_returns_201_and_task_id(self):
        board, list_id = self._board_with_list()
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            response = self.client.post(
                f"/boards/abc/lists/{list_id}/tasks",
                json={"name": "Write tests", "description": "cover all paths"},
            )
            self.assertEqual(response.status_code, 201)
            self.assertIn("task_id", response.json())

    def test_create_task_with_due_date_persists_it(self):
        board, list_id = self._board_with_list()
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            response = self.client.post(
                f"/boards/abc/lists/{list_id}/tasks",
                json={"name": "Birthday", "description": "", "due_date": "2027-06-01"},
            )
            self.assertEqual(response.status_code, 201)
            task_id = response.json()["task_id"]
            self.assertEqual(board.tasks[task_id].due_date, "2027-06-01")

    def test_create_task_without_due_date_stores_none(self):
        board, list_id = self._board_with_list()
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            response = self.client.post(
                f"/boards/abc/lists/{list_id}/tasks",
                json={"name": "Plain task"},
            )
            self.assertEqual(response.status_code, 201)
            task_id = response.json()["task_id"]
            self.assertIsNone(board.tasks[task_id].due_date)

    def test_create_task_empty_due_date_string_stores_none(self):
        board, list_id = self._board_with_list()
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            response = self.client.post(
                f"/boards/abc/lists/{list_id}/tasks",
                json={"name": "Plain task", "due_date": ""},
            )
            self.assertEqual(response.status_code, 201)
            task_id = response.json()["task_id"]
            self.assertIsNone(board.tasks[task_id].due_date)

    def test_move_task_succeeds(self):
        board, list_id = self._board_with_list()
        with patch("main.save_to_firestore"):
            second_list_id = board.add_list("Done")
            task_id = board.add_task(list_id, "My Task")
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            response = self.client.post(
                f"/boards/abc/tasks/{task_id}/move",
                json={"target_list_id": second_list_id},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(task_id, board.lists[second_list_id].task_ids)

    def test_update_task_changes_name_and_description(self):
        board, list_id = self._board_with_list()
        with patch("main.save_to_firestore"):
            task_id = board.add_task(list_id, "Old", "old desc")
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            response = self.client.patch(
                f"/boards/abc/tasks/{task_id}",
                json={"name": "New", "description": "new desc"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(board.tasks[task_id].name, "New")
            self.assertEqual(board.tasks[task_id].description, "new desc")

    def test_update_task_changes_color_tag(self):
        board, list_id = self._board_with_list()
        with patch("main.save_to_firestore"):
            task_id = board.add_task(list_id, "T")
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            response = self.client.patch(
                f"/boards/abc/tasks/{task_id}", json={"color_tag": "BLUE"}
            )
            self.assertEqual(response.status_code, 200)
            stored = board.tasks[task_id].color_tag
            self.assertEqual(getattr(stored, "value", stored), "BLUE")

    def test_update_task_sets_and_clears_due_date(self):
        board, list_id = self._board_with_list()
        with patch("main.save_to_firestore"):
            task_id = board.add_task(list_id, "T")
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            self.client.patch(
                f"/boards/abc/tasks/{task_id}", json={"due_date": "2027-01-01"}
            )
            self.assertEqual(board.tasks[task_id].due_date, "2027-01-01")
            self.client.patch(
                f"/boards/abc/tasks/{task_id}", json={"due_date": ""}
            )
            self.assertIsNone(board.tasks[task_id].due_date)

    def test_delete_task_succeeds(self):
        board, list_id = self._board_with_list()
        with patch("main.save_to_firestore"):
            task_id = board.add_task(list_id, "Task to delete")
        with patch("main.load_task_manager", return_value=board), \
             patch("main.save_to_firestore"):
            response = self.client.delete(f"/boards/abc/tasks/{task_id}")
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(task_id, board.tasks)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class TestSearch(_AppTestCase):
    def _seeded_board(self):
        from app.models import TaskManager
        board = TaskManager(board_id="abc", name="B", owner="testuser", users=[])
        with patch("main.save_to_firestore"):
            lid = board.add_list("Inbox")
            board.add_task(lid, "Buy milk", "from the store")
            board.add_task(lid, "Read book", "great novel")
        return board

    def test_search_matches_name(self):
        headers = self._login()
        board = self._seeded_board()
        with patch("main.load_task_manager", return_value=board):
            response = self.client.get(
                "/boards/abc/search", params={"q": "milk"}, headers=headers
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["name"], "Buy milk")

    def test_search_matches_description(self):
        headers = self._login()
        board = self._seeded_board()
        with patch("main.load_task_manager", return_value=board):
            response = self.client.get(
                "/boards/abc/search", params={"q": "novel"}, headers=headers
            )
            self.assertEqual(len(response.json()), 1)

    def test_search_is_case_insensitive(self):
        headers = self._login()
        board = self._seeded_board()
        with patch("main.load_task_manager", return_value=board):
            response = self.client.get(
                "/boards/abc/search", params={"q": "MILK"}, headers=headers
            )
            self.assertEqual(len(response.json()), 1)

    def test_search_no_match_returns_empty_list(self):
        headers = self._login()
        board = self._seeded_board()
        with patch("main.load_task_manager", return_value=board):
            response = self.client.get(
                "/boards/abc/search", params={"q": "zzz"}, headers=headers
            )
            self.assertEqual(response.json(), [])


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

class TestWebSocket(_AppTestCase):
    def test_rejects_invalid_token(self):
        # An invalid token closes the connection immediately.
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws/board1?token=garbage"):
                pass

    def test_accepts_valid_token(self):
        from app.auth import create_access_token
        token = create_access_token("alice")
        with self.client.websocket_connect(f"/ws/board1?token={token}") as ws:
            self.assertIn("alice", main_mod.manager_ws.get_active_users("board1"))


# ---------------------------------------------------------------------------
# ConnectionManager (unit-level, no HTTP)
# ---------------------------------------------------------------------------

class TestConnectionManager(unittest.TestCase):
    def test_active_users_empty_for_unknown_board(self):
        from main import ConnectionManager
        cm = ConnectionManager()
        self.assertEqual(cm.get_active_users("nope"), [])

    def test_disconnect_unknown_websocket_is_safe(self):
        from main import ConnectionManager
        cm = ConnectionManager()
        # should not raise
        cm.disconnect(MagicMock(), "board1")


if __name__ == "__main__":
    unittest.main()
