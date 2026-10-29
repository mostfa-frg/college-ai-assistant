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
    """Check whether a page is an authenticated Moodle page."""
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
        return bool(
            page.locator(
                'a[href*="/mod/"], #page-content, [role="main"], .course-content, '
                '[data-region="user-menu"], .usermenu, #user-menu-toggle'
            ).count()
        )
    except Exception:
        return False


def _probe_authenticated_session(page) -> bool:
    """Verify the saved browser context only after interactive SSO has finished."""
    course_id = COURSE_IDS[0]
    try:
        page.goto(
            f"{BASE_URL}course/view.php?id={course_id}",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        page.wait_for_timeout(1000)
        return _is_portal_authenticated(page)
    except Exception:
        return False


def save_portal_login_from_web(*, timeout_ms: int = 300_000) -> None:
    """Wait without navigating during interactive Microsoft SSO, then verify Moodle once."""
    print("Moodle sign-in is required. Complete Microsoft sign-in in the browser window.")
    print("The app will not reload the login page while you enter your email or password.")
    print("After sign-in, the app verifies Moodle access and saves the session.")
    playwright, browser, context, first_page = _open_login_browser()
    deadline = time.monotonic() + timeout_ms / 1000
    popup_was_seen = False
    popup_closed_at = None
    verified = False
    try:
        while time.monotonic() < deadline:
            pages = list(context.pages)
            if len(pages) > 1:
                popup_was_seen = True

            # First accept an authenticated portal page if SSO redirected the same tab.
            for page in pages:
                if _is_portal_authenticated(page):
                    context.storage_state(path=str(PORTAL_STATE_FILE))
                    print("Verified authenticated Moodle session saved.")
                    return

            # If SSO opened a popup, do not touch the main Moodle tab while it is open.
            # Once the popup closes, give the portal a moment to process the callback,
            # then perform one protected-page probe (not repeated reloads).
            if popup_was_seen and len(pages) == 1 and popup_closed_at is None:
                popup_closed_at = time.monotonic() + 2.0

            if popup_closed_at is not None and time.monotonic() >= popup_closed_at and not verified:
                verified = True
                if first_page in context.pages and _probe_authenticated_session(first_page):
                    context.storage_state(path=str(PORTAL_STATE_FILE))
                    print("Verified authenticated Moodle session saved.")
                    return
                raise RuntimeError(
                    "The Microsoft sign-in window closed, but Moodle did not establish an "
                    "authenticated session. The app did not save an invalid session. "
                    "Please retry and check whether Microsoft displayed an error or blocked "
                    "the college portal callback."
                )

            time.sleep(0.5)

        raise RuntimeError(
            "Sign-in timed out. The browser was left alone while you entered your credentials. "
            "Complete all Microsoft prompts and wait for the college portal callback."
        )
    finally:
        context.close()
        browser.close()
        playwright.stop()
