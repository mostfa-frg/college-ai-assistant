
import sqlite3

from college_assistant.config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                title TEXT NOT NULL,
                source_url TEXT,
                file_path TEXT,
                content_hash TEXT,
                status TEXT NOT NULL DEFAULT 'discovered',
                discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(course_id, title)
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_materials_status
            ON materials(status)
        """)
