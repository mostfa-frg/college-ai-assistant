from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from college_assistant.config import MATERIALS_DIR, PROCESSED_DIR
from college_assistant.storage.repositories import list_materials

_TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_+#.-]{1,}")
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "what",
    "when", "where", "which", "why", "how", "explain", "describe", "discuss",
    "should", "would", "could", "about", "between", "their", "there", "then",
    "them", "they", "have", "has", "does", "use", "used", "using", "each",
    "your", "you", "are", "was", "were", "can", "not", "but", "all", "any",
}


@dataclass(frozen=True)
class EvidenceChunk:
    text: str
    source: str
    location: str


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_RE.findall(text)
            if token.casefold() not in _STOPWORDS and len(token) > 1]


def _split_text(text: str, source: str) -> list[EvidenceChunk]:
    """Split extracted material into bounded, source-labelled passages."""
    chunks: list[EvidenceChunk] = []
    # Keep page markers when extracted from PDFs so citations can point back to a page.
    page_parts = re.split(r"(?=---\s*(?:Page|Slide)\s+\d+\s*---)", text)
    for page_part in page_parts:
        page_match = re.search(r"---\s*(Page|Slide)\s+(\d+)\s*---", page_part)
        location = f"{page_match.group(1).casefold()} {page_match.group(2)}" if page_match else "text"
        body = re.sub(r"---\s*(?:Page|Slide)\s+\d+\s*---", "", page_part).strip()
        if not body:
            continue
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        current = ""
        for paragraph in paragraphs:
            # Break very long paragraphs without losing their content.
            pieces = [paragraph[i:i + 1400] for i in range(0, len(paragraph), 1400)]
            for piece in pieces:
                if current and len(current) + len(piece) + 2 > 1400:
                    chunks.append(EvidenceChunk(current, source, location))
                    # Small overlap keeps definitions connected across chunk boundaries.
                    current = current[-180:] + "\n" + piece
                else:
                    current = (current + "\n\n" + piece).strip()
        if current:
            chunks.append(EvidenceChunk(current, source, location))
    return chunks


def _course_material_paths(course_id: str) -> list[Path]:
    paths: set[Path] = set()
    # Prefer files explicitly registered for this course in the local database.
    for item in list_materials(str(course_id)):
        raw = item.get("file_path")
        if raw:
            path = Path(raw)
            if path.is_file():
                paths.add(path.resolve())
    # Also discover local course materials, including files not yet registered in SQLite.
    for root in (MATERIALS_DIR, PROCESSED_DIR):
        if root.exists():
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.casefold() in {".txt", ".md", ".pdf", ".docx", ".pptx"}:
                    # Course-specific folders prevent accidentally mixing another course's notes.
                    normalized = path.as_posix().casefold()
                    if str(course_id) in normalized:
                        paths.add(path.resolve())
                    elif any(part.casefold() in _course_folder_names(str(course_id))
                             for part in path.parts):
                        paths.add(path.resolve())
    return sorted(paths)


def _course_folder_names(course_id: str) -> set[str]:
    known = {
        "1325": {"cloud_computing", "cloud computing"},
        "1327": {"embedded_systems", "embedded systems", "es-101", "es101"},
        "1323": {"computer_security", "computer security"},
        "1328": {"graduation_project_1", "graduation project 1"},
        "1324": {"digital_image_processing", "digital image processing"},
        "1326": {"distributed_systems", "distributed systems"},
    }
    return known.get(course_id, set())


def _read_material(path: Path) -> str:
    if path.suffix.casefold() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.casefold() == ".pdf":
        try:
            import pymupdf
        except ImportError:
            return ""
        pages = []
        with pymupdf.open(path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                page_text = page.get_text("text").strip()
                if page_text:
                    pages.append(f"--- Page {page_number} ---\n{page_text}")
        return "\n\n".join(pages)
    if path.suffix.casefold() == ".docx":
        try:
            from docx import Document
            document = Document(path)
            parts = [p.text.strip() for p in document.paragraphs if p.text.strip()]
            for table in document.tables:
                for row in table.rows:
                    parts.append(" | ".join(cell.text.strip() for cell in row.cells))
            return "\n".join(parts)
        except Exception:
            return ""
    if path.suffix.casefold() == ".pptx":
        try:
            from pptx import Presentation
            presentation = Presentation(path)
            slides = []
            for slide_number, slide in enumerate(presentation.slides, start=1):
                parts = [shape.text.strip() for shape in slide.shapes if getattr(shape, "has_text_frame", False) and shape.text.strip()]
                if parts:
                    slides.append(f"--- Slide {slide_number} ---\n" + "\n".join(parts))
            return "\n\n".join(slides)
        except Exception:
            return ""
    return ""


def retrieve_course_evidence(course_id: str, query: str, top_k: int = 5) -> list[EvidenceChunk]:
    """Retrieve relevant passages only from local materials for the assignment's course.

    This first version uses a dependency-light lexical ranker. It intentionally avoids
    embedding API costs; retrieval can later be upgraded without changing the caller.
    """
    query_terms = set(_tokens(query))
    if not query_terms:
        return []
    candidates: list[EvidenceChunk] = []
    for path in _course_material_paths(str(course_id)):
        try:
            content = _read_material(path)
        except (OSError, ValueError):
            continue
        if content.strip():
            candidates.extend(_split_text(content, path.name))
    if not candidates:
        return []

    # BM25-like ranking over the local candidate set.
    tokenized = [_tokens(item.text) for item in candidates]
    document_frequency = Counter(
        term for term in query_terms
        for tokens in tokenized if term in set(tokens)
    )
    average_length = sum(map(len, tokenized)) / max(len(tokenized), 1)
    scored: list[tuple[float, int, EvidenceChunk]] = []
    total_docs = len(candidates)
    for index, (chunk, tokens) in enumerate(zip(candidates, tokenized)):
        counts = Counter(tokens)
        length = len(tokens)
        score = 0.0
        for term in query_terms:
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            df = document_frequency[term]
            inverse = max(0.0, __import__("math").log(1 + (total_docs - df + 0.5) / (df + 0.5)))
            denominator = frequency + 1.2 * (1 - 0.75 + 0.75 * length / max(average_length, 1))
            score += inverse * frequency * 2.2 / denominator
        if score > 0:
            scored.append((score, index, chunk))
    scored.sort(key=lambda row: (-row[0], row[1]))
    results: list[EvidenceChunk] = []
    seen: set[tuple[str, str, str]] = set()
    for _, _, chunk in scored:
        key = (chunk.source, chunk.location, chunk.text[:100])
        if key in seen:
            continue
        seen.add(key)
        results.append(chunk)
        if len(results) >= top_k:
            break
    return results
