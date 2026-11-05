import sqlite3

from college_assistant.config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    """Create or migrate the local database without deleting existing records."""
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
        connection.execute("CREATE INDEX IF NOT EXISTS idx_materials_status ON materials(status)")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sync_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                error TEXT
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sync_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                course_id TEXT NOT NULL,
                course_title TEXT NOT NULL,
                activity_title TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                change_type TEXT NOT NULL,
                activity_url TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(run_id) REFERENCES sync_runs(id) ON DELETE CASCADE
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_sync_events_run ON sync_events(run_id)")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                course_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                last_successful_scan TEXT
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                activity_key TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                content_fingerprint TEXT NOT NULL,
                first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1,
                last_change TEXT NOT NULL DEFAULT 'baseline',
                UNIQUE(course_id, activity_key)
            )
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_activities_course_active
            ON activities(course_id, is_active)
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                activity_key TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                due_at TEXT,
                submission_status TEXT NOT NULL DEFAULT 'unknown',
                instructions_text TEXT,
                solution_status TEXT NOT NULL DEFAULT 'not_generated',
                solution_path TEXT,
                approved_at TEXT,
                approved_solution_path TEXT,
                generated_at TEXT,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(course_id, activity_key)
            )
        """)
        # Migrate databases created by earlier versions.
        existing = {
            row["name"] for row in connection.execute("PRAGMA table_info(assignments)")
        }
        migrations = {
            "instructions_text": "TEXT",
            "approved_at": "TEXT",
            "approved_solution_path": "TEXT",
            "generated_at": "TEXT",
        }
        for column, sql_type in migrations.items():
            if column not in existing:
                connection.execute(f"ALTER TABLE assignments ADD COLUMN {column} {sql_type}")
