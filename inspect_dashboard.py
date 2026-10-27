
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

    print("\n=== PAGE INFO ===")
    print("URL:", page.url)
    print("Title:", repr(page.title()))

    print("\n=== HEADINGS ===")
    for heading in page.locator("h1, h2, h3").all():
        text = heading.inner_text().strip()
        if text:
            print("-", text)

    print("\n=== LINKS ===")
    links = page.locator("a[href]")
    seen = set()

    for i in range(min(links.count(), 150)):
        link = links.nth(i)

        try:
            text = " ".join(link.inner_text().split())
            href = link.get_attribute("href")

            if text and href and (text, href) not in seen:
                seen.add((text, href))
                print(f"{text[:100]} -> {href}")
        except Exception:
            continue

    input("\nPress Enter to close...")
    browser.close()
