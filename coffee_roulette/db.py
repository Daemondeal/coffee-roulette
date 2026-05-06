import os
import sqlite3

from pathlib import Path

PATH_DB = Path(".data/database.db")

def get_connection():
    PATH_DB.parent.mkdir(exist_ok=True)

    conn = sqlite3.connect(PATH_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    global PATH_DB

    custom_db_path = os.getenv("PATH_DB", "")
    if custom_db_path != "":
        PATH_DB = Path(custom_db_path)

    conn = get_connection()


    schema_path = Path(__file__).parent.parent / "schema.sql"

    with open(schema_path, "r") as f:
        conn.executescript(f.read())

    conn.close()
