import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _make_app():
    """Import app with Firebase mocked out so no real connection is needed."""
    mock_db = MagicMock()
    # make health-check doc.get() not raise
    mock_db.collection.return_value.document.return_value.get.return_value = MagicMock()

    with patch("firebase_admin._apps", {"default": True}), \
         patch("firebase_admin.firestore.client", return_value=mock_db), \
         patch.dict("os.environ", {
             "FIREBASE_SERVICE_ACCOUNT": '{"type":"service_account"}',
             "SECRET_KEY": "testsecret",
         }):
        from main import app
        return app, mock_db


app, _mock_db = _make_app()


class TestRootAndStatic(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=True)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_root_redirects_to_landing_page(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertIn("landingpage", response.headers["location"])


class TestAuthEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=True)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def _patch_user_manager(self):
        """Return a mock UserManager that is injected into main.user_manager."""
        import main
        mock_um = MagicMock()
        main.user_manager = mock_um
        return mock_um

    # ---- register ----

    def test_register_success_returns_201(self):
        mock_um = self._patch_user_manager()
        mock_um.register_user.return_value = True
        response = self.client.post("/users/register", json={"login": "alice", "password": "pw123"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"message": "registered"})

    def test_register_duplicate_returns_400(self):
        mock_um = self._patch_user_manager()
        mock_um.register_user.return_value = False
        response = self.client.post("/users/register", json={"login": "alice", "password": "pw123"})
        self.assertEqual(response.status_code, 400)

    def test_register_missing_fields_returns_422(self):
        response = self.client.post("/users/register", json={"login": "alice"})
        self.assertEqual(response.status_code, 422)

    # ---- login ----

    def test_login_invalid_credentials_returns_401(self):
        mock_um = self._patch_user_manager()
        mock_um.login_user.return_value = False
        response = self.client.post("/users/login", json={"login": "wrong", "password": "wrong"})
        self.assertEqual(response.status_code, 401)

    def test_login_success_returns_token(self):
        mock_um = self._patch_user_manager()
        mock_um.login_user.return_value = True
        response = self.client.post("/users/login", json={"login": "alice", "password": "pw123"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")

    def test_login_missing_password_returns_422(self):
        response = self.client.post("/users/login", json={"login": "alice"})
        self.assertEqual(response.status_code, 422)


class TestProtectedEndpoints(unittest.TestCase):
    """Endpoints that require a valid Bearer token."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=True)
        self.client.__enter__()
        # get a real token
        import main
        mock_um = MagicMock()
        mock_um.login_user.return_value = True
        main.user_manager = mock_um
        response = self.client.post("/users/login", json={"login": "testuser", "password": "pw"})
        self.token = response.json()["access_token"]
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_get_boards_without_token_returns_401(self):
        response = self.client.get("/boards")
        self.assertEqual(response.status_code, 401)

    def test_get_boards_with_valid_token_returns_200(self):
        with patch("app.database.get_user_boards", return_value=[]):
            response = self.client.get("/boards", headers=self.auth_headers)
            self.assertEqual(response.status_code, 200)

    def test_create_board_without_token_returns_401(self):
        response = self.client.post("/boards", json={"name": "Sprint 1"})
        self.assertEqual(response.status_code, 401)

    def test_create_board_with_token_returns_201(self):
        with patch("app.database.save_to_firestore"):
            response = self.client.post("/boards", json={"name": "Sprint 1"}, headers=self.auth_headers)
            self.assertEqual(response.status_code, 201)
            self.assertIn("board_id", response.json())

    def test_lists_endpoint_without_token_returns_401(self):
        response = self.client.get("/boards/fakeid/lists")
        self.assertEqual(response.status_code, 401)


class TestBoardEndpoints(unittest.TestCase):
    """Tests for board-level CRUD with mocked Firestore."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=True)
        self.client.__enter__()
        import main
        mock_um = MagicMock()
        mock_um.login_user.return_value = True
        main.user_manager = mock_um
        response = self.client.post("/users/login", json={"login": "owner", "password": "pw"})
        self.token = response.json()["access_token"]
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def _mock_board(self, board_id="abc", owner="owner", users=None):
        from app.models import TaskManager
        manager = TaskManager(board_id=board_id, name="Test Board", owner=owner, users=users or [])
        return manager

    def test_get_board_users_returns_owner_and_users(self):
        board = self._mock_board()
        with patch("main.load_task_manager", return_value=board):
            response = self.client.get("/boards/abc/users", headers=self.auth_headers)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["owner"], "owner")

    def test_get_nonexistent_board_returns_404(self):
        with patch("app.database.load_from_firestore_raw", return_value=None):
            response = self.client.get("/boards/doesnotexist/lists", headers=self.auth_headers)
            self.assertEqual(response.status_code, 404)

    def test_create_list_on_valid_board(self):
        board = self._mock_board()
        with patch("main.load_task_manager", return_value=board), \
             patch("app.database.save_to_firestore"):
            response = self.client.post(
                "/boards/abc/lists",
                json={"name": "To Do"},
                headers=self.auth_headers
            )
            self.assertEqual(response.status_code, 201)
            self.assertIn("list_id", response.json())

    def test_add_user_to_board_forbidden_for_non_owner(self):
        board = self._mock_board(owner="someone_else")
        with patch("main.load_task_manager", return_value=board):
            response = self.client.post(
                "/boards/abc/users",
                json={"username": "bob"},
                headers=self.auth_headers
            )
            self.assertEqual(response.status_code, 403)

    def test_add_user_to_board_succeeds_for_owner(self):
        board = self._mock_board(owner="owner")
        with patch("main.load_task_manager", return_value=board), \
             patch("app.database.save_to_firestore"):
            response = self.client.post(
                "/boards/abc/users",
                json={"username": "bob"},
                headers=self.auth_headers
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["ok"])


class TestTaskEndpoints(unittest.TestCase):
    """Tests for task CRUD operations."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=True)
        self.client.__enter__()
        import main
        mock_um = MagicMock()
        mock_um.login_user.return_value = True
        main.user_manager = mock_um
        response = self.client.post("/users/login", json={"login": "owner", "password": "pw"})
        self.token = response.json()["access_token"]
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def _board_with_list(self):
        from app.models import TaskManager
        manager = TaskManager(board_id="abc", name="Board", owner="owner", users=[])
        list_id = manager.add_list.__wrapped__(manager, "My List") if hasattr(manager.add_list, "__wrapped__") else None
        # Use real add_list but suppress Firestore save
        with patch("app.database.save_to_firestore"):
            list_id = manager.add_list("My List")
        return manager, list_id

    def test_create_task_returns_201_and_task_id(self):
        board, list_id = self._board_with_list()
        with patch("main.load_task_manager", return_value=board), \
             patch("app.database.save_to_firestore"):
            response = self.client.post(
                f"/boards/abc/lists/{list_id}/tasks",
                json={"name": "Write tests", "description": "cover all paths"}
            )
            self.assertEqual(response.status_code, 201)
            self.assertIn("task_id", response.json())

    def test_move_task_succeeds(self):
        board, list_id = self._board_with_list()
        with patch("app.database.save_to_firestore"):
            second_list_id = board.add_list("Done")
            task_id = board.add_task(list_id, "My Task")
        with patch("main.load_task_manager", return_value=board), \
             patch("app.database.save_to_firestore"):
            response = self.client.post(
                f"/boards/abc/tasks/{task_id}/move",
                json={"target_list_id": second_list_id}
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["ok"])

    def test_delete_task_succeeds(self):
        board, list_id = self._board_with_list()
        with patch("app.database.save_to_firestore"):
            task_id = board.add_task(list_id, "Task to delete")
        with patch("main.load_task_manager", return_value=board), \
             patch("app.database.save_to_firestore"):
            response = self.client.delete(f"/boards/abc/tasks/{task_id}")
            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()