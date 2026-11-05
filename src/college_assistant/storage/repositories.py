from pathlib import Path

from college_assistant.storage.database import get_connection


VALID_STATUSES = {"discovered", "downloaded", "extracted", "summarized", "failed"}


def register_material(course_id: str, title: str, file_path: Path, content_hash: str,
                      status: str = "discovered") -> None:
    """Insert a material or update its local file metadata without resetting progress."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO materials (course_id, title, file_path, content_hash, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(course_id, title) DO UPDATE SET
                file_path = excluded.file_path, content_hash = excluded.content_hash,
                updated_at = CURRENT_TIMESTAMP
        """, (course_id, title, str(file_path), content_hash, status))


def list_materials(course_id: str | None = None) -> list[dict]:
    base = """SELECT materials.*, COALESCE(courses.title, materials.course_id) AS course_title
              FROM materials LEFT JOIN courses ON courses.course_id = materials.course_id"""
    query, params = (base + " ORDER BY course_title COLLATE NOCASE, materials.title COLLATE NOCASE", ()) if course_id is None else (
        base + " WHERE materials.course_id = ? ORDER BY materials.title COLLATE NOCASE", (course_id,))
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(query, params).fetchall()]


def update_material_status(material_id: int, status: str) -> bool:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid material status: {status}")
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE materials SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, material_id))
        return cursor.rowcount > 0


def start_sync_run() -> int:
    with get_connection() as connection:
        return int(connection.execute("INSERT INTO sync_runs (status) VALUES ('running')").lastrowid)


def finish_sync_run(run_id: int, error: str | None = None) -> None:
    with get_connection() as connection:
        connection.execute("""
            UPDATE sync_runs SET finished_at = CURRENT_TIMESTAMP, status = ?, error = ?
            WHERE id = ?
        """, ("failed" if error else "success", error, run_id))


def get_course_scan_time(course_id: str) -> str | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT last_successful_scan FROM courses WHERE course_id = ?", (course_id,)).fetchone()
    return row["last_successful_scan"] if row else None


def save_course_scan(course_id: str, title: str) -> None:
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO courses (course_id, title, last_successful_scan)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(course_id) DO UPDATE SET
                title = excluded.title, last_successful_scan = CURRENT_TIMESTAMP
        """, (course_id, title))


def get_activity(course_id: str, activity_key: str) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM activities WHERE course_id = ? AND activity_key = ?",
            (course_id, activity_key)).fetchone()
    return dict(row) if row else None


def save_activity(course_id: str, activity_key: str, title: str, url: str,
                  activity_type: str, fingerprint: str, change: str) -> None:
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO activities (course_id, activity_key, title, url, activity_type,
                                    content_fingerprint, last_change)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(course_id, activity_key) DO UPDATE SET
                title = excluded.title, url = excluded.url,
                activity_type = excluded.activity_type,
                content_fingerprint = excluded.content_fingerprint,
                last_seen_at = CURRENT_TIMESTAMP, is_active = 1,
                last_change = excluded.last_change
        """, (course_id, activity_key, title, url, activity_type, fingerprint, change))


def mark_missing_activities_inactive(course_id: str, seen_keys: set[str]) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM activities WHERE course_id = ? AND is_active = 1", (course_id,)).fetchall()
        removed = [dict(row) for row in rows if row["activity_key"] not in seen_keys]
        for item in removed:
            connection.execute("""
                UPDATE activities SET is_active = 0, last_change = 'removed'
                WHERE course_id = ? AND activity_key = ?
            """, (course_id, item["activity_key"]))
    return removed


def upsert_assignment(course_id: str, activity_key: str, title: str, url: str,
                      due_at: str | None = None, instructions_text: str | None = None,
                      submission_status: str | None = None) -> None:
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO assignments (course_id, activity_key, title, url, due_at,
                                     instructions_text, submission_status)
            VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, 'unknown'))
            ON CONFLICT(course_id, activity_key) DO UPDATE SET
                title = excluded.title, url = excluded.url,
                due_at = COALESCE(excluded.due_at, assignments.due_at),
                instructions_text = COALESCE(excluded.instructions_text, assignments.instructions_text),
                submission_status = COALESCE(?, assignments.submission_status),
                last_seen_at = CURRENT_TIMESTAMP
        """, (course_id, activity_key, title, url, due_at, instructions_text,
              submission_status, submission_status))


def list_assignments(unresolved_only: bool = False) -> list[dict]:
    query = """SELECT assignments.*, COALESCE(courses.title, assignments.course_id) AS course_title\n                   FROM assignments LEFT JOIN courses ON courses.course_id = assignments.course_id"""
    if unresolved_only:
        query += " WHERE solution_status != 'approved'"
    query += " ORDER BY course_title COLLATE NOCASE, title COLLATE NOCASE, due_at IS NULL, due_at"
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(query).fetchall()]


def get_assignment(assignment_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute("""
            SELECT assignments.*, COALESCE(courses.title, assignments.course_id) AS course_title
            FROM assignments LEFT JOIN courses ON courses.course_id = assignments.course_id
            WHERE assignments.id = ?
        """, (assignment_id,)).fetchone()
    return dict(row) if row else None


def save_solution_draft(assignment_id: int, path: Path) -> None:
    with get_connection() as connection:
        connection.execute("""
            UPDATE assignments SET solution_status = 'pending_review',
                solution_path = ?, approved_solution_path = NULL, approved_at = NULL,
                generated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (str(path), assignment_id))


def approve_solution(assignment_id: int, approved_path: Path) -> bool:
    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE assignments SET solution_status = 'approved',
                approved_at = CURRENT_TIMESTAMP, approved_solution_path = ?
            WHERE id = ? AND solution_path IS NOT NULL
        """, (str(approved_path), assignment_id))
        return cursor.rowcount > 0


def list_courses() -> list[dict]:
    """Return locally known courses with assignment/material counts."""
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT courses.course_id, courses.title, courses.last_successful_scan,
                   (SELECT COUNT(*) FROM assignments WHERE assignments.course_id = courses.course_id) AS assignment_count,
                   (SELECT COUNT(*) FROM materials WHERE materials.course_id = courses.course_id) AS material_count
            FROM courses
            ORDER BY courses.title COLLATE NOCASE
        """).fetchall()
    return [dict(row) for row in rows]
