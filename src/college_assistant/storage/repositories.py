
from pathlib import Path

from college_assistant.storage.database import get_connection


def register_material(
    course_id: str,
    title: str,
    file_path: Path,
    content_hash: str,
    status: str = "discovered",
) -> None:
    """Insert a material or update its file metadata without resetting its status."""

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO materials (
                course_id,
                title,
                file_path,
                content_hash,
                status
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(course_id, title) DO UPDATE SET
                file_path = excluded.file_path,
                content_hash = excluded.content_hash,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                course_id,
                title,
                str(file_path),
                content_hash,
                status,
            ),
        )


def list_materials(course_id: str | None = None) -> list[dict]:
    """Return registered materials, optionally filtered by course."""

    with get_connection() as connection:
        if course_id is None:
            rows = connection.execute(
                "SELECT * FROM materials ORDER BY title"
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM materials
                WHERE course_id = ?
                ORDER BY title
                """,
                (course_id,),
            ).fetchall()

    return [dict(row) for row in rows]

VALID_STATUSES = {
    "discovered",
    "downloaded",
    "extracted",
    "summarized",
    "failed",
}


def update_material_status(
    material_id: int,
    status: str,
) -> bool:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid material status: {status}")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE materials
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, material_id),
        )

        return cursor.rowcount > 0
