import json
from hash import hash_password, verify_password


class Users:
    def __init__(self, filepath="json/users.json"):
        self.filepath = filepath
        try:
            with open(self.filepath) as f:
                self.users = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"File '{self.filepath}' does not exist. Make sure its present.")

    def register_user(self, login, password):
        if login in self.users:
            return "Login is already taken, choose a different one"
        self.users[login] = hash_password(password)
        with open(self.filepath, "w") as f:
            json.dump(self.users, f, indent=2)
        return f"Successfully registered, welcome {login}!"

    def login_user(self, login, password):
        if login not in self.users:
            return f"{login} is not registered yet"
        if not verify_password(password, self.users[login]):
            return "Wrong password"
        return f"Successfully logged in, welcome back {login}!"

    def change_password(self, login, old_password, new_password):
        if login not in self.users:
            return f"{login} is not registered yet"
        if not verify_password(old_password, self.users[login]):
            return "Old password does not match"
        self.users[login] = hash_password(new_password)
        with open(self.filepath, "w") as f:
            json.dump(self.users, f, indent=2)
        return "Password changed successfully!"

    def delete_account(self, login, password):
        if login not in self.users:
            return f"{login} is not registered yet"
        if not verify_password(password, self.users[login]):
            return "Wrong password"
        del self.users[login]
        with open(self.filepath, "w") as f:
            json.dump(self.users, f, indent=2)
        return f"Account {login} has been deleted successfully"
