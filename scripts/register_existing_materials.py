
import hashlib
from college_assistant.config import SUMMARIES_DIR
from college_assistant.config import MATERIALS_DIR, PROCESSED_DIR
from college_assistant.storage.database import initialize_database
from college_assistant.storage.repositories import (
    register_material,
    list_materials,
)


COURSE_ID = "1326"
COURSE_FOLDER = "distributed_systems"


def sha256_file(file_path) -> str:
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main() -> None:
    initialize_database()

    materials_dir = MATERIALS_DIR / COURSE_FOLDER
    text_dir = PROCESSED_DIR / COURSE_FOLDER / "text"
    summaries_dir = SUMMARIES_DIR / COURSE_FOLDER

    if not materials_dir.is_dir():
        raise FileNotFoundError(
            f"Materials directory not found: {materials_dir}"
        )

    pdf_files = sorted(materials_dir.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    for pdf_path in pdf_files:
        text_path = text_dir / f"{pdf_path.stem}.txt"

        if text_path.is_file():
            status = "extracted"
        else:
            status = "downloaded"

        register_material(
            course_id=COURSE_ID,
            title=pdf_path.name,
            file_path=pdf_path,
            content_hash=sha256_file(pdf_path),
            status=status,
        )

        print(f"[REGISTERED] {pdf_path.name} -> {status}")

    materials = list_materials(COURSE_ID)
    print(f"\nTotal materials registered: {len(materials)}")


if __name__ == "__main__":
    main()
