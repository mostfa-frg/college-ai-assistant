
from pathlib import Path
import fitz  # PyMuPDF

PDF_DIR = Path("data/materials/distributed_systems")

for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
    print("\n" + "=" * 70)
    print("FILE:", pdf_path.name)

    try:
        with fitz.open(pdf_path) as doc:
            print("Pages:", len(doc))

            total_chars = 0
            pages_with_text = 0

            for page_num, page in enumerate(doc):
                text = page.get_text("text").strip()
                total_chars += len(text)

                if text:
                    pages_with_text += 1

                if page_num == 0:
                    print("First page preview:")
                    print(text[:1200] or "[No extractable text]")

            print("Pages with text:", pages_with_text)
            print("Total extracted characters:", total_chars)

            if total_chars < 100:
                print("CHECK: May require OCR or a different extraction method.")
            else:
                print("CHECK: Text extraction appears possible.")

    except Exception as exc:
        print("ERROR:", repr(exc))
