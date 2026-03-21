import sqlite3
from contextlib import contextmanager

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