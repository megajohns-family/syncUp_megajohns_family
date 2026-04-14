import unittest
from fastapi.testclient import TestClient
from main import app

class TestMainAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=True)
        self.client.__enter__()

    def test_root_redirect(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 307)

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_register_user(self):
        response = self.client.post("/users/register", json={
            "login": "testuser",
            "password": "password123"
        })
        #it can be 200 or 400 if user exists
        self.assertIn(response.status_code, [201, 400])

    def test_login_user_invalid(self):
        response = self.client.post("/users/login", json={
            "login": "wrong",
            "password": "wrong"
        })
        self.assertEqual(response.status_code, 401)

    def test_login_and_get_token(self):
        # registration firstly
        self.client.post("/users/register", json={
            "login": "user2",
            "password": "pass123"
        })

        response = self.client.post("/users/login", json={
            "login": "user2",
            "password": "pass123"
        })

        if response.status_code == 200:
            data = response.json()
            self.assertIn("access_token", data)
            self.assertEqual(data["token_type"], "bearer")

    def test_protected_endpoint_without_token(self):
        response = self.client.get("/lists")
        self.assertEqual(response.status_code, 401)

if __name__ == "__main__":
    unittest.main()