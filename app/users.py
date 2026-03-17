import json
from werkzeug.security import generate_password_hash, check_password_hash


class Users:
    def __init__(self, filepath="json/users.json"):
        self.filepath = filepath
        with open(self.filepath) as f:
            self.users = json.load(f)

    def register_user(self, login, password):
        if login in self.users:
            return "Login is already taken, choose a different one"
        self.users[login] = generate_password_hash(password)
        with open(self.filepath, "w") as f:
            json.dump(self.users, f, indent=2)
        return f"Successfully registered, welcome {login}!"

    def login_user(self, login, password):
        if login not in self.users:
            return f"{login} is not registered yet"
        if not check_password_hash(self.users[login], password):
            return "Wrong password"
        return f"Successfully logged in, welcome back {login}!"
    
    def change_password(self, login, old_password, new_password):
        if login not in self.users:
            return f"{login} is not registered yet"
        
        if not check_password_hash(self.users[login], old_password):
            return "old password does not match"
        
        self.users[login] = generate_password_hash(new_password)
        with open(self.filepath, "w") as f:
            json.dump(self.users, f, indent=2)
        return "Password changed successfully!"
    
    def delete_account(self, login, password):
        if login not in self.users:
            return f"{login} is not registered yet"
        
        if not check_password_hash(self.users[login], password):
            return "wrong password"
        
        del self.users[login]
        with open(self.filepath, "w") as f:
            json.dump(self.users, f, indent=2)
        return f"Account {login} has been deleted successfully"