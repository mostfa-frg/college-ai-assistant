from __future__ import annotations

from urllib.parse import urlparse

from college_assistant.browser_setup import ensure_chromium_installed
from college_assistant.config import BASE_URL, COURSE_IDS, DATA_DIR, PORTAL_STATE_FILE

# The dashboard uses an explicit two-step SSO flow. Keep the browser alive between
# HTTP requests so the user can complete Microsoft login at their own pace.
_login_runtime = None


def _open_login_browser():
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


def _is_portal_authenticated(page) -> bool:
    try:
        parsed = urlparse(page.url)
        if parsed.hostname != urlparse(BASE_URL).hostname or "/login/" in parsed.path:
            return False
        body = " ".join(page.locator("body").inner_text(timeout=2500).split()).casefold()
        if not body or "log in using your account on" in body:
            return False
        if "you are not logged in" in body or "invalid login" in body:
            return False
        return bool(page.locator(
            'a[href*="/mod/"], #page-content, [role="main"], .course-content, '
            '[data-region="user-menu"], .usermenu, #user-menu-toggle'
        ).count())
    except Exception:
        return False


def start_portal_login_from_web() -> None:
    """Open SSO browser and return immediately; do not poll, navigate, or close it."""
    global _login_runtime
    close_pending_portal_login()
    playwright, browser, context, page = _open_login_browser()
    _login_runtime = {
        "playwright": playwright,
        "browser": browser,
        "context": context,
        "page": page,
    }


def complete_portal_login_from_web() -> bool:
    """Called only after the user clicks the dashboard's finish-login button."""
    global _login_runtime
    if not _login_runtime:
        raise RuntimeError("No sign-in window is active. Click Start Moodle sign-in first.")

    runtime = _login_runtime
    context = runtime["context"]
    try:
        # Do not interfere with the Microsoft form while the user is typing.
        for page in list(context.pages):
            if _is_portal_authenticated(page):
                context.storage_state(path=str(PORTAL_STATE_FILE))
                return True

        # Only after the user explicitly says they finished do we navigate once
        # to a protected course page to test whether SSO established Moodle cookies.
        page = runtime["page"]
        page.goto(
            f"{BASE_URL}course/view.php?id={COURSE_IDS[0]}",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        page.wait_for_timeout(800)
        if not _is_portal_authenticated(page):
            return False
        context.storage_state(path=str(PORTAL_STATE_FILE))
        return True
    finally:
        close_pending_portal_login()


def close_pending_portal_login() -> None:
    """Close a pending sign-in browser safely when explicitly replacing/finishing it."""
    global _login_runtime
    runtime, _login_runtime = _login_runtime, None
    if not runtime:
        return
    for key in ("context", "browser"):
        try:
            runtime[key].close()
        except Exception:
            pass
    try:
        runtime["playwright"].stop()
    except Exception:
        pass


def save_portal_login() -> None:
    """Legacy CLI login helper; user confirms completion in terminal."""
    print("A browser will open for Moodle/Microsoft sign-in.")
    playwright, browser, context, page = _open_login_browser()
    try:
        input("Complete sign-in in the browser, then press Enter here...")
        context.storage_state(path=str(PORTAL_STATE_FILE))
    finally:
        context.close()
        browser.close()
        playwright.stop()


def save_portal_login_from_web(*, timeout_ms: int = 300_000) -> None:
    """Compatibility wrapper: use the explicit dashboard flow instead of blocking."""
    start_portal_login_from_web()
    raise RuntimeError(
        "A sign-in browser is open. Complete sign-in, then click 'I've finished signing in' "
        "in the dashboard to verify and save the session."
    )
