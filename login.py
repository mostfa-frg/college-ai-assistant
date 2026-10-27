from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "https://learn3.sha.edu.eg/my/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    page.goto(BASE_URL)
    print("Current URL:", page.url)

    input(
        "Log in manually in the browser, "
        "then press Enter here..."
    )

    print("After login:", page.url)
    print("Page title:", page.title())

    Path("data").mkdir(exist_ok=True)
    context.storage_state(
        path="data/portal-state.json"
    )

    browser.close()