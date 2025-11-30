import sqlite3

from pathlib import Path

PATH_DB = Path(".data/database.db")

def get_connection():
    PATH_DB.parent.mkdir(exist_ok=True)

    conn = sqlite3.connect(PATH_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()

    with open("schema.sql", "r") as f:
        conn.executescript(f.read())

    conn.close()
