from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.sync_api import sync_playwright

from college_assistant.browser_setup import ensure_chromium_installed
from college_assistant.config import BASE_URL, PORTAL_STATE_FILE
from college_assistant.materials_sync import sync_course_materials
from college_assistant.storage.repositories import (
    finish_sync_run,
    get_activity,
    get_course_scan_time,
    mark_missing_activities_inactive,
    save_activity,
    save_course_scan,
    start_sync_run,
    upsert_assignment,
)


def _is_login_page(page) -> bool:
    """Detect Moodle's native login page and the college's Microsoft SSO landing page."""
    parsed = urlparse(page.url)
    if parsed.path.startswith("/login/"):
        return True
    try:
        body = " ".join(page.locator("body").inner_text(timeout=3000).split()).casefold()
    except Exception:
        body = ""
    return (
        "log in using your account on" in body
        or "you are not logged in" in body
        or "invalid login" in body
    )


def _activity_key(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if query.get("id"):
        return f"{parsed.path}?id={query['id'][0]}"
    return f"{parsed.path}?{parsed.query}"


def _activity_type(url: str) -> str:
    path = urlparse(url).path
    if "/mod/assign/" in path:
        return "assignment"
    if "/mod/resource/" in path or "/mod/folder/" in path:
        return "material"
    if "/mod/forum/" in path:
        return "announcement_or_forum"
    return "activity"


def _extract_pdf_text(detail_page, href: str) -> str | None:
    """Download a Moodle attachment with the authenticated browser context and extract PDF text."""
    try:
        from urllib.parse import urljoin
        import pymupdf

        url = urljoin(detail_page.url, href)
        response = detail_page.context.request.get(url, timeout=30000)
        if not response.ok:
            return None
        payload = response.body()
        if not payload.startswith(b"%PDF"):
            return None
        document = pymupdf.open(stream=payload, filetype="pdf")
        try:
            text = "\n\n".join(page.get_text("text") for page in document).strip()
        finally:
            document.close()
        return text if len(text) >= 40 else "PDF_TEXT_EXTRACTION_EMPTY_OCR_REQUIRED"
    except Exception:
        return None


def _extract_assignment_instructions(detail_page) -> str | None:
    """Extract assignment descriptions and readable text from attached PDFs."""
    description_parts: list[str] = []
    for selector in ("#intro", ".activity-description", ".assignintro"):
        locator = detail_page.locator(selector)
        for index in range(locator.count()):
            try:
                text = "\n".join(line.strip() for line in locator.nth(index).inner_text(timeout=3000).splitlines() if line.strip())
            except Exception:
                continue
            if text and text not in description_parts:
                description_parts.append(text)

    attachments: list[tuple[str, str]] = []
    seen_hrefs: set[str] = set()
    for selector in (
        ".assignsubmission_file a",
        ".attachments a",
        "a[href*='/pluginfile.php/']",
    ):
        locator = detail_page.locator(selector)
        for index in range(locator.count()):
            link = locator.nth(index)
            try:
                name = " ".join(link.inner_text(timeout=2000).split())
                href = link.get_attribute("href") or ""
            except Exception:
                continue
            if name and href and href not in seen_hrefs:
                seen_hrefs.add(href)
                attachments.append((name, href))

    if not description_parts and not attachments:
        return "ASSIGNMENT_DESCRIPTION_NOT_FOUND: Moodle page loaded, but no readable assignment description was found."

    sections = []
    if description_parts:
        sections.append("ASSIGNMENT DESCRIPTION:\n" + "\n\n".join(description_parts))

    for name, href in attachments:
        if name.casefold().endswith(".pdf") or ".pdf" in href.casefold():
            extracted = _extract_pdf_text(detail_page, href)
            if extracted and extracted != "PDF_TEXT_EXTRACTION_EMPTY_OCR_REQUIRED":
                sections.append(f"ATTACHMENT PDF TEXT ({name}):\n{extracted}")
            elif extracted == "PDF_TEXT_EXTRACTION_EMPTY_OCR_REQUIRED":
                sections.append(f"PDF_TEXT_EXTRACTION_EMPTY_OCR_REQUIRED: {name}")
            else:
                sections.append(f"ATTACHMENT_FILES_DETECTED_NOT_EXTRACTED: {name}")
        else:
            sections.append(f"ATTACHMENT_FILES_DETECTED_NOT_EXTRACTED: {name}")

    return "\n\n".join(sections)[:24000]


def _inspect_assignment(context, url: str) -> tuple[str | None, str]:
    """Read assignment instructions and classify submission state conservatively."""
    detail_page = context.new_page()
    try:
        response = detail_page.goto(url, wait_until="domcontentloaded", timeout=45000)
        if _is_login_page(detail_page):
            raise RuntimeError("Portal session expired. Sign in through the college Microsoft SSO page.")
        if response and response.status >= 400:
            return None, "unknown"
        body = " ".join(detail_page.locator("body").inner_text(timeout=15000).split())
        lower = body.casefold()
        not_submitted_phrases = (
            "no submissions have been made", "nothing has been submitted",
            "no attempt has been made", "not submitted",
        )
        submitted_phrases = (
            "submitted for grading", "submission status: submitted",
            "submitted on", "submission was submitted",
        )
        if any(phrase in lower for phrase in not_submitted_phrases):
            status = "not_submitted"
        elif any(phrase in lower for phrase in submitted_phrases):
            status = "submitted"
        else:
            status = "unknown"
        return _extract_assignment_instructions(detail_page), status
    except RuntimeError:
        raise
    except Exception:
        return None, "unknown"
    finally:
        detail_page.close()


def discover_courses(page) -> dict[str, str]:
    """Discover enrolled courses using the same delayed-render handling as moodle-sync."""
    found: dict[str, str] = {}
    diagnostics: list[str] = []
    for path in ("my/courses.php", "my/"):
        target_url = urljoin(BASE_URL, path)
        response = page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        if _is_login_page(page):
            raise RuntimeError(
                f"Portal session expired while opening {path}. "
                "Sign in through the college Microsoft SSO page."
            )
        try:
            page.wait_for_selector('a[href*="/course/view.php?id="]', timeout=15000)
        except Exception:
            # Some Moodle themes render course cards asynchronously or expose
            # their URLs only after the page's remaining scripts finish.
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            try:
                page.wait_for_timeout(1500)
            except Exception:
                pass

        links = page.locator('a[href*="/course/view.php?id="]')
        link_count = links.count()
        diagnostics.append(
            f"{path}: HTTP {response.status if response else 'unknown'}, "
            f"URL={page.url}, title={page.title()!r}, course_links={link_count}"
        )
        for index in range(link_count):
            link = links.nth(index)
            href = link.get_attribute("href") or ""
            parsed = urlparse(urljoin(BASE_URL, href))
            course_id = (parse_qs(parsed.query).get("id") or [""])[0]
            if not course_id.isdigit() or course_id == "1":
                continue
            try:
                title = " ".join(link.inner_text(timeout=3000).split())
            except Exception:
                title = ""
            found.setdefault(course_id, title or f"Course {course_id}")
        if found:
            return found

    raise RuntimeError(
        "Moodle did not expose any enrolled course links. Discovery diagnostics: "
        + " | ".join(diagnostics)
        + ". Open My courses in the same browser session and confirm that your courses are visible."
    )



class _CourseLinkParser(HTMLParser):
    """Extract Moodle activity links from the same raw HTML used by moodle-sync."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str, str]] = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self._current = {
                "href": attrs["href"],
                "text": [],
                "title": attrs.get("title") or attrs.get("aria-label") or "",
            }

    def handle_data(self, data):
        if self._current is not None:
            self._current["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._current is not None:
            item = self._current
            label = " ".join("".join(item["text"]).split()) or " ".join(item["title"].split())
            self.links.append((item["href"], label, item["title"]))
            self._current = None


def _course_activity_links(html: str, base_url: str) -> list[tuple[str, str, str, str]]:
    parser = _CourseLinkParser()
    parser.feed(html)
    host = urlparse(base_url).netloc
    result = []
    seen = set()
    for href, label, title_attr in parser.links:
        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.netloc != host or not parsed.path.startswith("/mod/"):
            continue
        kind = next((name for name in ("assign", "resource", "folder", "url") if f"/mod/{name}/view.php" in parsed.path), None)
        activity_id = (parse_qs(parsed.query).get("id") or [""])[0]
        if not kind or not activity_id:
            continue
        key = (kind, activity_id)
        if key in seen:
            continue
        seen.add(key)
        label = label or title_attr or f"{kind.title()} {activity_id}"
        label = re.sub(r"\s+(File|Folder|Assignment|URL|Page|Forum|Quiz)$", "", label).strip()
        result.append((kind, activity_id, label, url))
    return result


def scan_course(page, course_id: str, *, download_materials: bool = False) -> dict:
    course_url = urljoin(BASE_URL, f"course/view.php?id={course_id}")
    previous_scan = get_course_scan_time(course_id)
    response = page.goto(course_url, wait_until="domcontentloaded", timeout=60000)

    if _is_login_page(page):
        raise RuntimeError("Portal session expired. Sign in through the college Microsoft SSO page.")
    if response and response.status >= 400:
        raise RuntimeError(f"Course {course_id} returned HTTP {response.status}.")

    course_title = page.title().replace("Course: ", "").strip() or f"Course {course_id}"
    seen: set[str] = set()
    changes: list[dict] = []
    assignments: list[dict] = []
    course_html = page.content()
    activity_links = _course_activity_links(course_html, BASE_URL)

    for kind, activity_id, title, url in activity_links:
        key = _activity_key(url)
        if key in seen:
            continue
        seen.add(key)

        activity_type = "assignment" if kind == "assign" else _activity_type(url)
        fingerprint = hashlib.sha256(
            f"{title.strip()}\n{url}".encode("utf-8")
        ).hexdigest()
        previous = get_activity(course_id, key)
        if previous is None:
            change = "baseline" if previous_scan is None else "new"
        elif previous["content_fingerprint"] != fingerprint:
            change = "changed"
        else:
            change = "unchanged"

        save_activity(course_id, key, title, url, activity_type, fingerprint, change)
        if change in {"new", "changed"}:
            changes.append({
                "change": change,
                "course": course_title,
                "title": title,
                "type": activity_type,
                "url": url,
            })

        if activity_type == "assignment":
            instructions_text, submission_status = _inspect_assignment(page.context, url)
            upsert_assignment(
                course_id, key, title, url,
                instructions_text=instructions_text,
                submission_status=submission_status,
            )
            assignments.append({
                "title": title, "url": url, "key": key,
                "submission_status": submission_status,
            })

    # An empty result may mean a portal/layout/loading problem, not that all
    # course activities were deleted. Fail safely and preserve the prior snapshot.
    if not seen:
        raise RuntimeError(
            f"No activities were detected in course {course_id}; "
            "the previous snapshot was left unchanged."
        )

    removed = mark_missing_activities_inactive(course_id, seen)
    for item in removed:
        if previous_scan is not None:
            changes.append({
                "change": "removed",
                "course": course_title,
                "title": item["title"],
                "type": item["activity_type"],
                "url": item["url"],
            })

    save_course_scan(course_id, course_title)
    material_sync = {"downloaded": 0, "failed": 0}
    if download_materials:
        try:
            material_sync = sync_course_materials(page.context, course_id, course_title)
        except Exception as error:
            print(f"Warning: material download failed for {course_title}: {error}")
    return {
        "course_id": course_id,
        "course_title": course_title,
        "first_scan": previous_scan is None,
        "activities_seen": len(seen),
        "assignments": assignments,
        "changes": changes,
        "materials_downloaded": material_sync["downloaded"],
        "material_download_failures": material_sync["failed"],
    }


def run_sync(*, download_materials: bool = False, auto_generate_drafts: bool = False) -> list[dict]:
    if not PORTAL_STATE_FILE.is_file():
        raise FileNotFoundError(
            f"Portal session not found: {PORTAL_STATE_FILE}. Run login.py first."
        )

    run_id = start_sync_run()
    try:
        results = []
        with sync_playwright() as playwright:
            ensure_chromium_installed(playwright)
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                storage_state=str(PORTAL_STATE_FILE),
                ignore_https_errors=True,
            )
            page = context.new_page()
            try:
                courses = discover_courses(page)
                print(f"Discovered {len(courses)} enrolled Moodle courses.")
                for course_id, discovered_title in courses.items():
                    try:
                        result = scan_course(page, course_id, download_materials=download_materials)
                        results.append(result)
                    except RuntimeError as error:
                        if "session expired" in str(error).casefold():
                            raise
                        print(f"Skipping course {discovered_title} ({course_id}): {error}")
                        results.append({
                            "course_id": course_id, "course_title": discovered_title,
                            "first_scan": get_course_scan_time(course_id) is None,
                            "activities_seen": 0, "assignments": [], "changes": [],
                            "materials_downloaded": 0, "material_download_failures": 1,
                            "error": str(error),
                        })
            finally:
                context.close()
                browser.close()
        finish_sync_run(run_id)
        if auto_generate_drafts:
            from college_assistant.assignment_solutions import generate_pending_drafts
            generated = generate_pending_drafts()
            if generated:
                print("\nAssignment drafts generated for review:")
                for item in generated:
                    print(f"  [{item['id']}] {item['title']} -> {item['path']}")
        return results
    except Exception as error:
        finish_sync_run(run_id, str(error)[:1000])
        raise


def print_report(results: list[dict]) -> None:
    print("\n=== COLLEGE PORTAL SYNC ===")
    total_changes = sum(len(item["changes"]) for item in results)
    print(f"Courses scanned: {len(results)}")
    print(f"New/changed/removed activities: {total_changes}")

    for result in results:
        marker = " (baseline scan)" if result["first_scan"] else ""
        print(f"\n{result['course_title']}{marker}")
        print(f"  Activities checked: {result['activities_seen']}")
        if "materials_downloaded" in result:
            print(f"  Course materials downloaded/updated: {result['materials_downloaded']}")
            if result.get("material_download_failures"):
                print(f"  Material files skipped/failed: {result['material_download_failures']}")
        if not result["changes"]:
            print("  No new or changed activities detected.")
        for change in result["changes"]:
            print(f"  [{change['change'].upper()}] {change['title']} ({change['type']})")
            print(f"    {change['url']}")
        if result["assignments"]:
            print(f"  Assignment activities found: {len(result['assignments'])}")
            for assignment in result["assignments"]:
                print(f"    - {assignment['title']} [submission: {assignment['submission_status']}]")

    print("\nDraft generation is limited to assignments explicitly marked not_submitted")
    print("with captured instructions. Nothing is submitted to the portal.")
