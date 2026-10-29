from __future__ import annotations

from urllib.parse import urlparse

from college_assistant.browser_setup import ensure_chromium_installed
from college_assistant.config import BASE_URL, COURSE_IDS, DATA_DIR, PORTAL_STATE_FILE

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


def _page_login_signals(page) -> tuple[bool, str]:
    """Return login evidence without relying on fragile Moodle theme selectors."""
    parsed = urlparse(page.url)
    try:
        body = " ".join(page.locator("body").inner_text(timeout=2500).split()).casefold()
    except Exception:
        body = ""
    login_words = (
        "log in using your account on",
        "you are not logged in",
        "invalid login",
        "sign in to your account",
    )
    is_login = parsed.path.startswith("/login/") or any(word in body for word in login_words)
    return is_login, body


def _is_portal_authenticated(page) -> bool:
    """Identify a protected Moodle course page after SSO, not the public login landing page."""
    try:
        parsed = urlparse(page.url)
        if parsed.hostname != urlparse(BASE_URL).hostname:
            return False
        is_login, body = _page_login_signals(page)
        if is_login or not body:
            return False

        # A protected course URL that remains on Moodle and contains course activity
        # content is a stronger signal than theme-dependent menu selectors.
        if parsed.path == "/course/view.php" and parsed.query:
            if page.locator('a[href*="/mod/"], [data-for="section"], .course-content').count():
                return True
            title = (page.title() or "").casefold()
            if "course" in title and len(body) > 250:
                return True

        # Dashboard page: require a recognizable authenticated course/navigation element.
        return bool(page.locator(
            'a[href*="/course/view.php"], a[href*="/mod/"], '
            '[data-region="user-menu"], .usermenu, #user-menu-toggle, '
            'a[href*="/login/logout.php"]'
        ).count())
    except Exception:
        return False


def start_portal_login_from_web() -> None:
    """Open SSO browser and return immediately; leave it under user control."""
    global _login_runtime
    close_pending_portal_login()
    playwright, browser, context, page = _open_login_browser()
    _login_runtime = {"playwright": playwright, "browser": browser, "context": context, "page": page}


def complete_portal_login_from_web() -> tuple[bool, str]:
    """Verify SSO only after user confirmation and persist browser storage on success."""
    global _login_runtime
    if not _login_runtime:
        raise RuntimeError("No sign-in window is active. Click Check Moodle assignments to open it.")

    runtime = _login_runtime
    context = runtime["context"]

    # If SSO returned to Moodle in any tab, preserve that URL and inspect it first.
    for page in list(context.pages):
        if _is_portal_authenticated(page):
            context.storage_state(path=str(PORTAL_STATE_FILE))
            close_pending_portal_login()
            return True, "Authenticated Moodle session saved."

    # Explicit user confirmation means it is now safe to navigate the main tab once.
    page = runtime["page"]
    course_url = f"{BASE_URL}course/view.php?id={COURSE_IDS[0]}"
    try:
        response = page.goto(course_url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(1200)
    except Exception as exc:
        return False, f"Could not verify Moodle access ({type(exc).__name__}). The sign-in window remains open."

    final_url = page.url
    status = response.status if response else None
    if _is_portal_authenticated(page):
        context.storage_state(path=str(PORTAL_STATE_FILE))
        close_pending_portal_login()
        return True, "Authenticated Moodle session saved."

    parsed = urlparse(final_url)
    is_login, body = _page_login_signals(page)
    if parsed.hostname == urlparse(BASE_URL).hostname and parsed.path == "/course/view.php" and not is_login and body:
        # Some Moodle themes don't expose standard menu selectors. A successful
        # protected course URL with real content is enough even if the theme differs.
        context.storage_state(path=str(PORTAL_STATE_FILE))
        close_pending_portal_login()
        return True, "Moodle course page loaded; session saved."

    # Do not destroy the live login context on a failed verification. Return useful
    # diagnostics without exposing cookies, tokens, or full query strings.
    host = parsed.hostname or "unknown host"
    path = parsed.path or "/"
    reason = (
        f"Moodle did not accept the session (HTTP {status if status is not None else 'unknown'}; "
        f"final page {host}{path}). "
        "If this page is still the Microsoft sign-in page, finish its prompts and try again. "
        "If Microsoft says sign-in succeeded but Moodle returns to its login page, the college "
        "SSO callback may not be setting a Moodle session cookie."
    )
    return False, reason


def close_pending_portal_login() -> None:
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
    """Legacy CLI login helper."""
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
    start_portal_login_from_web()
    raise RuntimeError("Sign-in browser opened. Finish login and confirm from the dashboard.")
