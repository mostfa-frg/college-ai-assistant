from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from college_assistant.config import MATERIALS_DIR
from college_assistant.storage.repositories import register_material

_COURSE_SLUGS = {
    "1325": "cloud_computing",
    "1327": "embedded_systems",
    "1323": "computer_security",
    "1328": "graduation_project_1",
    "1324": "digital_image_processing",
    "1326": "distributed_systems",
}
_ALLOWED_SUFFIXES = {".pdf", ".txt", ".md", ".docx", ".pptx"}


def _safe_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return value[:160] or "course_material"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _download(context, url: str, output_dir: Path, title: str, course_id: str) -> bool:
    parsed = urlparse(url)
    filename = _safe_filename(f"{title}_{unquote(Path(parsed.path).name)}")
    suffix = Path(filename).suffix.casefold()
    if suffix not in _ALLOWED_SUFFIXES:
        return False
    try:
        response = context.request.get(url, timeout=60000)
        if not response.ok:
            return False
        payload = response.body()
        if suffix == ".pdf" and not payload.startswith(b"%PDF"):
            return False
        if not payload:
            return False
        output_dir.mkdir(parents=True, exist_ok=True)
        destination = output_dir / filename
        digest = _sha256(payload)
        if not destination.exists() or _sha256(destination.read_bytes()) != digest:
            destination.write_bytes(payload)
        register_material(
            course_id=str(course_id),
            title=title or filename,
            file_path=destination,
            content_hash=digest,
            status="downloaded",
        )
        return True
    except Exception:
        # A single inaccessible Moodle file should not stop the whole course scan.
        return False


def sync_course_materials(context, course_id: str, course_title: str | None = None) -> dict:
    """Download readable resource/folder files for one course using the authenticated context.

    Assignment submission files are intentionally excluded. Only resources and course folders
    are considered so private student submissions are never collected as learning material.
    """
    from college_assistant.config import BASE_URL

    slug = _COURSE_SLUGS.get(str(course_id), _safe_filename(course_title or f"course_{course_id}").casefold())
    output_dir = MATERIALS_DIR / slug
    course_url = urljoin(BASE_URL, f"course/view.php?id={course_id}")
    page = context.new_page()
    downloaded = 0
    failed = 0
    seen: set[str] = set()
    try:
        response = page.goto(course_url, wait_until="domcontentloaded", timeout=60000)
        if "/login/" in page.url or (response and response.status >= 400):
            return {"downloaded": 0, "failed": 1}
        links = page.locator('a[href*="/mod/resource/view.php"], a[href*="/mod/folder/view.php"]')
        activities: list[tuple[str, str]] = []
        for index in range(links.count()):
            link = links.nth(index)
            try:
                href = link.get_attribute("href") or ""
                title = " ".join(link.inner_text(timeout=2000).split())
            except Exception:
                continue
            if not href or not title:
                continue
            url = urljoin(BASE_URL, href)
            if url not in seen:
                seen.add(url)
                activities.append((title, url))

        for title, url in activities:
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                if response and response.status >= 400:
                    failed += 1
                    continue
                final_url = page.url
                final_path = urlparse(final_url).path
                if "/pluginfile.php/" in final_path:
                    extension = Path(unquote(final_path)).suffix.casefold()
                    if extension not in _ALLOWED_SUFFIXES:
                        continue
                    if _download(context, final_url, output_dir, title, str(course_id)):
                        downloaded += 1
                    else:
                        failed += 1
                    continue

                file_links = page.locator('a[href*="/pluginfile.php/"]')
                for index in range(file_links.count()):
                    link = file_links.nth(index)
                    href = link.get_attribute("href") or ""
                    if not href:
                        continue
                    file_url = urljoin(page.url, href)
                    filename = unquote(Path(urlparse(file_url).path).name)
                    if Path(filename).suffix.casefold() not in _ALLOWED_SUFFIXES:
                        continue
                    file_title = " ".join(link.inner_text(timeout=1500).split()) or filename
                    if _download(context, file_url, output_dir, file_title, str(course_id)):
                        downloaded += 1
                    else:
                        failed += 1
            except Exception:
                failed += 1
    finally:
        page.close()
    return {"downloaded": downloaded, "failed": failed}
