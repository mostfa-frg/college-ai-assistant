from __future__ import annotations

import hashlib
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from college_assistant.config import MATERIALS_DIR, BASE_URL
from college_assistant.storage.repositories import register_material

ALLOWED = {".pdf", ".txt", ".md", ".docx", ".pptx", ".xlsx", ".csv", ".zip", ".url"}


def safe_name(value: str, fallback: str = "item", limit: int = 100) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    return re.sub(r"\s+", " ", value).strip(" .")[:limit] or fallback


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.embeds = []
        self._link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self._link = [attrs["href"], []]
        elif tag in ("iframe", "embed", "source") and attrs.get("src"):
            self.embeds.append(attrs["src"])
        elif tag == "object" and attrs.get("data"):
            self.embeds.append(attrs["data"])

    def handle_data(self, data):
        if self._link is not None:
            self._link[1].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._link:
            self.links.append((self._link[0], " ".join("".join(self._link[1]).split())))
            self._link = None


def _parse(html: str):
    parser = _PageParser()
    parser.feed(html)
    return parser


def _register(context, url: str, folder: Path, course_id: str, title: str | None = None) -> bool:
    try:
        response = context.request.get(url, timeout=90000)
        if not response.ok:
            return False
        payload = response.body()
        if not payload:
            return False
        path_name = unquote(Path(urlparse(url).path).name) or "download"
        filename = safe_name(path_name, "download")
        suffix = Path(filename).suffix.casefold()
        if suffix not in ALLOWED:
            return False
        if suffix == ".pdf" and not payload.startswith(b"%PDF"):
            return False
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / filename
        if destination.exists() and digest(destination.read_bytes()) != digest(payload):
            destination = folder / f"{destination.stem}_{digest(payload)[:8]}{destination.suffix}"
        if not destination.exists():
            temporary = destination.with_suffix(destination.suffix + ".part")
            temporary.write_bytes(payload)
            temporary.replace(destination)
        register_material(str(course_id), title or destination.name, destination, digest(payload), "downloaded")
        return True
    except Exception:
        return False


def _save_shortcut(course_id: str, folder: Path, title: str, target: str) -> bool:
    try:
        urls_dir = folder / "URLs"
        urls_dir.mkdir(parents=True, exist_ok=True)
        filename = safe_name(title, "link") + ".url"
        destination = urls_dir / filename
        content = f"[InternetShortcut]\nURL={target}\n"
        if destination.exists() and destination.read_text(encoding="utf-8", errors="ignore") != content:
            destination = urls_dir / f"{destination.stem}_{hashlib.sha1(target.encode()).hexdigest()[:8]}.url"
        destination.write_text(content, encoding="utf-8")
        register_material(str(course_id), f"{title} (link)", destination, digest(content.encode()), "downloaded")
        return True
    except Exception:
        return False


def _resolve_moodle_url(context, activity_url: str, host: str) -> str | None:
    response = context.request.get(activity_url, timeout=60000, max_redirects=0)
    if 300 <= response.status < 400:
        target = urljoin(activity_url, response.headers.get("location", ""))
        if urlparse(target).netloc == host and "/pluginfile.php/" in urlparse(target).path:
            return target
        return target
    if response.ok:
        html = response.text()
        match = re.search(r'urlworkaround.*?href="([^"]+)"', html, re.S)
        if match:
            return urljoin(activity_url, unescape(match.group(1)))
        parsed = _parse(html)
        for source in parsed.embeds:
            target = urljoin(activity_url, source)
            if urlparse(target).netloc != host:
                return target
    return None


def sync_course_materials(context, course_id: str, course_title: str | None = None) -> dict:
    """Mirror Moodle-sync: resources, nested folders, teacher assignment attachments and URL shortcuts."""
    host = urlparse(BASE_URL).netloc
    course_dir = MATERIALS_DIR / safe_name(course_title or f"Course {course_id}", f"course_{course_id}")
    response = context.request.get(urljoin(BASE_URL, f"course/view.php?id={course_id}"), timeout=90000)
    if not response.ok or "/login/" in urlparse(response.url).path:
        return {"downloaded": 0, "failed": 1, "links": 0}
    parsed_page = _parse(response.text())
    activities = []
    seen = set()
    for href, label in parsed_page.links:
        url = urljoin(response.url, href)
        parsed = urlparse(url)
        if parsed.netloc != host:
            continue
        activity_id = (parse_qs(parsed.query).get("id") or [""])[0]
        kind = next((k for k in ("resource", "folder", "assign", "url") if f"/mod/{k}/view.php" in parsed.path), None)
        if not kind or not activity_id or (kind, activity_id) in seen:
            continue
        seen.add((kind, activity_id))
        label = re.sub(r"\s+(File|Folder|Assignment|URL|Page|Forum|Quiz)$", "", label).strip()
        activities.append((kind, activity_id, label or f"{kind}_{activity_id}", url))

    downloaded = failed = links = 0
    for kind, activity_id, title, activity_url in activities:
        try:
            if kind == "url":
                target = _resolve_moodle_url(context, activity_url, host)
                if not target:
                    failed += 1
                elif urlparse(target).netloc == host and "/pluginfile.php/" in urlparse(target).path:
                    if _register(context, target, course_dir, course_id, title): downloaded += 1
                    else: failed += 1
                else:
                    if _save_shortcut(course_id, course_dir, title, target): links += 1
                    else: failed += 1
                continue

            activity_response = context.request.get(activity_url, timeout=90000)
            if not activity_response.ok:
                failed += 1
                continue
            final_url = activity_response.url
            if "/pluginfile.php/" in urlparse(final_url).path:
                if _register(context, final_url, course_dir, course_id, title): downloaded += 1
                else: failed += 1
                continue
            detail = _parse(activity_response.text())
            candidates = [urljoin(final_url, u) for u in detail.embeds]
            candidates += [urljoin(final_url, href) for href, _ in detail.links]
            for file_url in dict.fromkeys(candidates):
                path = unquote(urlparse(file_url).path)
                if "/pluginfile.php/" not in path:
                    continue
                if kind == "assign" and "/mod_assign/introattachment/" not in path:
                    continue
                if kind == "resource" and "/mod_resource/content/" not in path:
                    continue
                if kind == "folder" and "/mod_folder/content/" not in path:
                    continue
                if Path(path).suffix.casefold() not in ALLOWED:
                    continue
                target_folder = course_dir
                if kind == "assign":
                    target_folder = course_dir / "Assignments"
                elif kind == "folder":
                    inner = path.split("mod_folder/content/", 1)[1].split("/")
                    for part in inner[1:-1]:
                        target_folder = target_folder / safe_name(part, "folder", 60)
                    target_folder = target_folder / safe_name(title, "Folder", 60)
                if _register(context, file_url, target_folder, course_id):
                    downloaded += 1
                else:
                    failed += 1
        except Exception:
            failed += 1
    return {"downloaded": downloaded, "failed": failed, "links": links}
