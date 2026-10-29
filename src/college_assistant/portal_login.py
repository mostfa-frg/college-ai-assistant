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
    """Open Moodle sign-in and wait until the login form is actually gone."""
    print("Moodle sign-in is required. Complete sign-in in the browser window that opens.")
    print("The browser will remain open while you sign in.")
    print("Verify any certificate warning with the college before entering credentials.")
    playwright, browser, context, page = _open_login_browser()
    try:
        # URL alone is not a reliable signal: Moodle can render its login form at
        # /my/ or keep the same URL after an unsuccessful/partial login attempt.
        page.wait_for_function(
            """() => {
                const username = document.querySelector(
                    'input[name="username"], input#username, input[name="email"]'
                );
                const password = document.querySelector(
                    'input[name="password"], input#password'
                );
                const loginForm = document.querySelector(
                    'form#login, form[action*="login"], form[action*="signin"]'
                );
                const url = window.location.href.toLowerCase();
                const loginText = /log in to the site|you are not logged in|invalid login/i
                    .test(document.body?.innerText || "");
                return !username && !password && !loginForm &&
                    !url.includes("/login/") && !loginText;
            }""",
            timeout=timeout_ms,
        )
        # Save only after the browser visibly leaves the login state.
        context.storage_state(path=str(PORTAL_STATE_FILE))
    except Exception as exc:
        raise RuntimeError(
            "Moodle sign-in was not detected before the timeout. Keep the login "
            "browser open, complete sign-in, and make sure it returns to the portal."
        ) from exc
    finally:
        context.close()
        browser.close()
        playwright.stop()
