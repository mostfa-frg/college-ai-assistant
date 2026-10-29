from __future__ import annotations

from college_assistant.browser_setup import ensure_chromium_installed
from college_assistant.config import BASE_URL, DATA_DIR, PORTAL_STATE_FILE


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


def save_portal_login_from_web(*, timeout_ms: int = 180_000) -> None:
    """Open Moodle sign-in and wait for the user to finish, without requiring a terminal prompt."""
    print("Moodle sign-in is required. Complete sign-in in the browser window that opens.")
    print("Verify any certificate warning with the college before entering credentials.")
    playwright, browser, context, page = _open_login_browser()
    try:
        if "/login/" in page.url:
            page.wait_for_url(lambda url: "/login/" not in str(url), timeout=timeout_ms)
        # A successful sign-in should land on a portal page, not the login form.
        if "/login/" in page.url:
            raise RuntimeError("Moodle sign-in was not completed.")
        context.storage_state(path=str(PORTAL_STATE_FILE))
    finally:
        context.close()
        browser.close()
        playwright.stop()
