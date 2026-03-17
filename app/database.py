import sqlite3
from contextlib import contextmanager

DB_PATH = "syncup_users"

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                pw_hash TEXT NOT NULL,
                session INTEGER DEFAULT 1)
                """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks(
                task_id INT PRIMARY KEY,
                task_name VARCHAR(30),
                task_desc TEXT)
                """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS lists(
                list_id INT PRIMARY KEY,
                list_name VARCHAR(30),
                task_id INT,
                FOREIGN KEY(task_id) REFERENCES tasks(task_id))
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