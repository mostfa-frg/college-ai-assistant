from __future__ import annotations

from college_assistant.browser_setup import ensure_chromium_installed
from college_assistant.config import BASE_URL, DATA_DIR, PORTAL_STATE_FILE


def save_portal_login() -> None:
    """Open a browser for sign-in and save the session in the user's local data folder."""
    from playwright.sync_api import sync_playwright

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("A browser will open for Moodle sign-in.")
    print("Use the official college portal. Verify any certificate warning with the college.")
    with sync_playwright() as playwright:
        ensure_chromium_installed(playwright)
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        try:
            page.goto(BASE_URL + "my/", wait_until="domcontentloaded")
            print("Current URL:", page.url)
            input("Complete sign-in in the browser, then press Enter here...")
            print("After sign-in:", page.url)
            print("Page title:", page.title())
            context.storage_state(path=str(PORTAL_STATE_FILE))
            print(f"Local Moodle session saved to: {PORTAL_STATE_FILE}")
            print("Treat this file like a password. Do not share it.")
        finally:
            browser.close()
