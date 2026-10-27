from pathlib import Path
from college_assistant.storage.database import get_connection


VALID_STATUSES = {
    "discovered", "downloaded", "extracted", "summarized", "failed",
}


def register_material(
    course_id: str,
    title: str,
    file_path: Path,
    content_hash: str,
    status: str = "discovered",
) -> None:
    """Insert a material or update its local file metadata without resetting progress."""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO materials (course_id, title, file_path, content_hash, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(course_id, title) DO UPDATE SET
                file_path = excluded.file_path,
                content_hash = excluded.content_hash,
                updated_at = CURRENT_TIMESTAMP
            """,
            (course_id, title, str(file_path), content_hash, status),
        )


def list_materials(course_id: str | None = None) -> list[dict]:
    with get_connection() as connection:
        if course_id is None:
            rows = connection.execute(
                "SELECT * FROM materials ORDER BY title"
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM materials WHERE course_id = ? ORDER BY title",
                (course_id,),
            ).fetchall()
    return [dict(row) for row in rows]


def update_material_status(material_id: int, status: str) -> bool:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid material status: {status}")
    with get_connection() as connection:
        cursor = connection.execute(
            """UPDATE materials SET status = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (status, material_id),
        )
        return cursor.rowcount > 0


def start_sync_run() -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO sync_runs (status) VALUES ('running')"
        )
        return int(cursor.lastrowid)


def finish_sync_run(run_id: int, error: str | None = None) -> None:
    with get_connection() as connection:
        connection.execute(
            """UPDATE sync_runs
               SET finished_at = CURRENT_TIMESTAMP, status = ?, error = ?
               WHERE id = ?""",
            ("failed" if error else "success", error, run_id),
        )


def get_course_scan_time(course_id: str) -> str | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT last_successful_scan FROM courses WHERE course_id = ?",
            (course_id,),
        ).fetchone()
    return row["last_successful_scan"] if row else None


def save_course_scan(course_id: str, title: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO courses (course_id, title, last_successful_scan)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(course_id) DO UPDATE SET
                 title = excluded.title,
                 last_successful_scan = CURRENT_TIMESTAMP""",
            (course_id, title),
        )


def get_activity(course_id: str, activity_key: str) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """SELECT * FROM activities
               WHERE course_id = ? AND activity_key = ?""",
            (course_id, activity_key),
        ).fetchone()
    return dict(row) if row else None


def save_activity(
    course_id: str,
    activity_key: str,
    title: str,
    url: str,
    activity_type: str,
    fingerprint: str,
    change: str,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO activities (
                 course_id, activity_key, title, url, activity_type,
                 content_fingerprint, last_change
               ) VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(course_id, activity_key) DO UPDATE SET
                 title = excluded.title,
                 url = excluded.url,
                 activity_type = excluded.activity_type,
                 content_fingerprint = excluded.content_fingerprint,
                 last_seen_at = CURRENT_TIMESTAMP,
                 is_active = 1,
                 last_change = excluded.last_change""",
            (course_id, activity_key, title, url, activity_type, fingerprint, change),
        )


def mark_missing_activities_inactive(course_id: str, seen_keys: set[str]) -> list[dict]:
    """Mark activities absent from a completed scan as inactive; return newly removed ones."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM activities WHERE course_id = ? AND is_active = 1",
            (course_id,),
        ).fetchall()
        removed = [dict(row) for row in rows if row["activity_key"] not in seen_keys]
        for item in removed:
            connection.execute(
                """UPDATE activities SET is_active = 0, last_change = 'removed'
                   WHERE course_id = ? AND activity_key = ?""",
                (course_id, item["activity_key"]),
            )
    return removed


def upsert_assignment(
    course_id: str,
    activity_key: str,
    title: str,
    url: str,
    due_at: str | None = None,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO assignments (course_id, activity_key, title, url, due_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(course_id, activity_key) DO UPDATE SET
                 title = excluded.title,
                 url = excluded.url,
                 due_at = COALESCE(excluded.due_at, assignments.due_at),
                 last_seen_at = CURRENT_TIMESTAMP""",
            (course_id, activity_key, title, url, due_at),
        )


def list_assignments(unresolved_only: bool = False) -> list[dict]:
    query = "SELECT * FROM assignments"
    if unresolved_only:
        query += " WHERE submission_status != 'submitted'"
    query += " ORDER BY due_at IS NULL, due_at, title"
    with get_connection() as connection:
        rows = connection.execute(query).fetchall()
    return [dict(row) for row in rows]
