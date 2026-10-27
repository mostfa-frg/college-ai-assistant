from __future__ import annotations

import hashlib
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.sync_api import sync_playwright

from college_assistant.config import BASE_URL, COURSE_IDS, PORTAL_STATE_FILE
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


def scan_course(page, course_id: str) -> dict:
    course_url = urljoin(BASE_URL, f"course/view.php?id={course_id}")
    previous_scan = get_course_scan_time(course_id)
    response = page.goto(course_url, wait_until="domcontentloaded", timeout=60000)

    if "/login/" in page.url:
        raise RuntimeError("Portal session expired. Run login.py to sign in again.")
    if response and response.status >= 400:
        raise RuntimeError(f"Course {course_id} returned HTTP {response.status}.")

    course_title = page.title().replace("Course: ", "").strip() or f"Course {course_id}"
    links = page.locator('a[href*="/mod/"]')
    seen: set[str] = set()
    changes: list[dict] = []
    assignments: list[dict] = []

    for index in range(links.count()):
        link = links.nth(index)
        href = link.get_attribute("href")
        title = " ".join(link.inner_text().split())
        if not href or not title:
            continue

        url = urljoin(BASE_URL, href)
        parsed = urlparse(url)
        if parsed.netloc != urlparse(BASE_URL).netloc:
            continue
        if not parsed.path.startswith("/mod/"):
            continue

        key = _activity_key(url)
        if key in seen:
            continue
        seen.add(key)

        activity_type = _activity_type(url)
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
            upsert_assignment(course_id, key, title, url)
            assignments.append({"title": title, "url": url, "key": key})

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
    return {
        "course_id": course_id,
        "course_title": course_title,
        "first_scan": previous_scan is None,
        "activities_seen": len(seen),
        "assignments": assignments,
        "changes": changes,
    }


def run_sync() -> list[dict]:
    if not PORTAL_STATE_FILE.is_file():
        raise FileNotFoundError(
            f"Portal session not found: {PORTAL_STATE_FILE}. Run login.py first."
        )

    run_id = start_sync_run()
    try:
        results = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                storage_state=str(PORTAL_STATE_FILE),
                ignore_https_errors=True,
            )
            page = context.new_page()
            try:
                for course_id in COURSE_IDS:
                    results.append(scan_course(page, course_id))
            finally:
                context.close()
                browser.close()
        finish_sync_run(run_id)
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
        if not result["changes"]:
            print("  No new or changed activities detected.")
        for change in result["changes"]:
            print(f"  [{change['change'].upper()}] {change['title']} ({change['type']})")
            print(f"    {change['url']}")
        if result["assignments"]:
            print(f"  Assignment activities found: {len(result['assignments'])}")

    print("\nNote: this scan records assignment links only. Submission-state detection and")
    print("automatic draft generation are separate steps; nothing is submitted to the portal.")
