from __future__ import annotations

import time
from urllib.parse import urlparse

from college_assistant.browser_setup import ensure_chromium_installed
from college_assistant.config import BASE_URL, COURSE_IDS, DATA_DIR, PORTAL_STATE_FILE


def _open_login_browser():
    """Create a visible browser context for the college portal login."""
    from playwright.sync_api import sync_playwright

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    playwright = sync_playwright().start()
    try:
        ensure_chromium_installed(playwright)
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(BASE_URL + "my/", wait_until="domcontentloaded")
        return playwright, browser, context, page
    except Exception:
        playwright.stop()
        raise


def save_portal_login() -> None:
    """Open a browser for sign-in and save the session in the user's local data folder."""
    print("A browser will open for Moodle sign-in.")
    print("Use the official college portal. Verify any certificate warning with the college.")
    playwright, browser, context, page = _open_login_browser()
    try:
        print("Current URL:", page.url)
        input("Complete sign-in in the browser, then press Enter here...")
        print("After sign-in:", page.url)
        print("Page title:", page.title())
        context.storage_state(path=str(PORTAL_STATE_FILE))
        print(f"Local Moodle session saved to: {PORTAL_STATE_FILE}")
        print("Treat this file like a password. Do not share it.")
    finally:
        context.close()
        browser.close()
        playwright.stop()


def _is_portal_authenticated(page) -> bool:
    """Probe a protected Moodle page; avoid relying on fragile menu/URL heuristics."""
    try:
        parsed = urlparse(page.url)
        if parsed.hostname != urlparse(BASE_URL).hostname:
            return False
        if "/login/" in parsed.path:
            return False
        body = " ".join(page.locator("body").inner_text(timeout=2500).split()).casefold()
        if not body or "log in using your account on" in body:
            return False
        if "you are not logged in" in body or "invalid login" in body:
            return False
        # Moodle course pages contain course content; a login/SSO landing page does not.
        return bool(
            page.locator('a[href*="/mod/"], #page-content, [role="main"] '
                         '.course-content, .course-content').count()
        )
    except Exception:
        return False


def _probe_authenticated_session(page) -> bool:
    """Reload a protected course URL to let a completed SSO popup establish Moodle cookies."""
    course_id = COURSE_IDS[0]
    try:
        page.goto(
            f"{BASE_URL}course/view.php?id={course_id}",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        page.wait_for_timeout(750)
        return _is_portal_authenticated(page)
    except Exception:
        return False


def save_portal_login_from_web(*, timeout_ms: int = 300_000) -> None:
    """Support Moodle's Microsoft SSO popup/redirect flow and save only a verified session."""
    print("Moodle sign-in is required. Complete the Microsoft sign-in in the browser.")
    print("If the Microsoft popup closes itself, the app will keep checking the main portal tab.")
    print("Verify the address before entering credentials; the app will not bypass authentication.")
    playwright, browser, context, first_page = _open_login_browser()
    deadline = time.monotonic() + timeout_ms / 1000
    last_probe = 0.0
    try:
        while time.monotonic() < deadline:
            # Some SSO providers complete in a popup and close only that popup.
            # The main Moodle tab may need a fresh request to receive its session.
            pages = list(context.pages)
            for page in pages:
                try:
                    if urlparse(page.url).hostname == urlparse(BASE_URL).hostname:
                        if _is_portal_authenticated(page):
                            context.storage_state(path=str(PORTAL_STATE_FILE))
                            print("Verified authenticated Moodle session saved.")
                            return
                except Exception:
                    continue

            now = time.monotonic()
            if now - last_probe >= 3 and first_page in context.pages:
                last_probe = now
                if _probe_authenticated_session(first_page):
                    context.storage_state(path=str(PORTAL_STATE_FILE))
                    print("Verified authenticated Moodle session saved.")
                    return
            time.sleep(0.5)

        current_pages = [
            f"{urlparse(page.url).hostname or 'unknown'}{urlparse(page.url).path}"
            for page in context.pages
        ]
        raise RuntimeError(
            "Sign-in did not establish a Moodle session within five minutes. "
            "The app checked the protected course page after the Microsoft sign-in "
            f"flow but Moodle still showed a login/unauthenticated page. Open tabs: {current_pages}. "
            "If the Microsoft popup closes, that alone does not mean Moodle login succeeded; "
            "check for an error or approval prompt in the remaining browser window."
        )
    finally:
        context.close()
        browser.close()
        playwright.stop()
