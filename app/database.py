import sqlite3
from contextlib import contextmanager
import json
from pathlib import Path

#Files which program operates on:

users = Path("app/json_files/users.json")
tasks = Path("app/json_files/tasks.json")

DB_PATH = "syncup_db.db"

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users(
                users_file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                users_file_name VARCHAR(30) UNIQUE,
                users_file_data TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks(
                file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name VARCHAR(30) UNIQUE,
                file_data TEXT
            )
        """)
        db.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def push_to_db(filename: str) -> None:
    if filename == "tasks.json":
        path = tasks
    elif filename == "users.json":
        path = users
    else:
        print("File not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with get_db() as db:
        if filename == "tasks.json":
            db.execute(
                "INSERT OR REPLACE INTO tasks(file_name, file_data) VALUES (?, ?)",
                (filename, json.dumps(data, ensure_ascii=False))
            )
            db.commit()
        elif filename == "users.json":
            db.execute(
                "INSERT OR REPLACE INTO users(users_file_name, users_file_data) VALUES (?, ?)",
                (filename, json.dumps(data, ensure_ascii=False))
            )
            db.commit()

def pull_from_db(filename: str) -> None:
    with get_db() as db:
        if filename == "tasks.json":
            row = db.execute(
                "SELECT file_data FROM tasks WHERE file_name = ?",
                (filename,)
            ).fetchone()

            if row is None:
                print(f"There is no data for {filename} in database")
                return

            data = json.loads(row["file_data"])

            with open(tasks, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        elif filename == "users.json":
            row = db.execute(
                "SELECT users_file_data FROM users WHERE users_file_name = ?",
                (filename,)
            ).fetchone()

            if row is None:
                print(f"There is no data for {filename} in database")
                return

            data = json.loads(row["users_file_data"])

            with open(users, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        else:
            print(f"Unknown file: {filename}")