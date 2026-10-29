from __future__ import annotations

import time
from urllib.parse import urlparse

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


def _is_authenticated_portal_page(page) -> bool:
    """Return true only when a page is back on the college portal and looks signed in."""
    try:
        parsed = urlparse(page.url)
        portal_host = urlparse(BASE_URL).hostname
        if parsed.hostname != portal_host or parsed.path.startswith("/login/"):
            return False
        body = " ".join(page.locator("body").inner_text(timeout=1500).split()).casefold()
        if not body or "log in using your account on" in body:
            return False
        if "you are not logged in" in body or "invalid login" in body:
            return False
        # Authenticated Moodle pages normally expose a course link, dashboard
        # navigation, or a logout/profile control. Requiring one avoids treating
        # the external Microsoft identity page as successful authentication.
        return bool(
            page.locator('a[href*="/course/view.php"], a[href*="/my/"], '
                         'a[href*="logout"], [data-region="user-menu"], '
                         '.usermenu, #user-menu-toggle').count()
        )
    except Exception:
        return False


def save_portal_login_from_web(*, timeout_ms: int = 300_000) -> None:
    """Handle Moodle's Microsoft SSO flow and save state only after returning authenticated."""
    print("Moodle sign-in is required. A browser window will stay open during Microsoft sign-in.")
    print("Finish the Microsoft sign-in and wait until the browser returns to the college portal.")
    print("Verify the address before entering credentials; the app will not bypass authentication.")
    playwright, browser, context, first_page = _open_login_browser()
    deadline = time.monotonic() + timeout_ms / 1000
    try:
        while time.monotonic() < deadline:
            # Microsoft SSO may redirect the current tab or open a separate tab.
            for page in list(context.pages):
                if _is_authenticated_portal_page(page):
                    context.storage_state(path=str(PORTAL_STATE_FILE))
                    return
            time.sleep(0.5)
        raise RuntimeError(
            "Microsoft sign-in did not return to an authenticated college portal page "
            "within five minutes. Complete all Microsoft prompts and wait for the "
            "browser to return to learn3.sha.edu.eg; if it stays on Microsoft, check "
            "for an approval/MFA prompt or sign-in error."
        )
    finally:
        context.close()
        browser.close()
        playwright.stop()
