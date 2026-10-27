
from pathlib import Path
import hashlib
import json

import pymupdf

SOURCE_DIR = Path("data/materials/distributed_systems")
OUTPUT_DIR = Path("data/processed/distributed_systems")
TEXT_DIR = OUTPUT_DIR / "text"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def extract_pdf(path):
    with pymupdf.open(path) as doc:
        pages = []

        for index, page in enumerate(doc):
            text = page.get_text("text").strip()
            pages.append(f"--- Page {index + 1} ---\n{text}")

        return len(doc), "\n\n".join(pages).strip()


def main():
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"Source directory not found: {SOURCE_DIR}")

    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    for pdf_path in sorted(SOURCE_DIR.glob("*.pdf")):
        print(f"Processing: {pdf_path.name}")

        try:
            page_count, text = extract_pdf(pdf_path)
            digest = sha256_file(pdf_path)

            text_path = TEXT_DIR / f"{pdf_path.stem}.txt"
            text_path.write_text(text, encoding="utf-8")

            record = {
                "filename": pdf_path.name,
                "sha256": digest,
                "pages": page_count,
                "characters": len(text),
                "text_file": str(text_path),
                "status": "ok" if text else "empty",
            }

            manifest.append(record)
            print(f"  Pages: {page_count}, characters: {len(text)}")

        except Exception as exc:
            manifest.append({
                "filename": pdf_path.name,
                "status": "error",
                "error": str(exc),
            })
            print(f"  ERROR: {exc}")

    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nProcessed {len(manifest)} PDF files.")
    print(f"Extracted text: {TEXT_DIR.resolve()}")
    print(f"Manifest: {MANIFEST_PATH.resolve()}")


if __name__ == "__main__":
    main()
