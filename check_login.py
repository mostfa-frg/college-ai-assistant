
from playwright.sync_api import sync_playwright

STATE_FILE = "data/portal-state.json"
BASE_URL = "https://learn3.sha.edu.eg/my/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    context = browser.new_context(
        storage_state=STATE_FILE,
        ignore_https_errors=True,
    )

    page = context.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)

    print("Current URL:", page.url)
    print("Page title:", repr(page.title()))

    if "/login/" in page.url:
        print("RESULT: Login state is NOT working.")
    else:
        print("RESULT: No login redirect detected. Verify the dashboard manually.")

    input("Press Enter to close the browser...")
    browser.close()
