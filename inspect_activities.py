
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

BASE_URL = "https://learn3.sha.edu.eg/"
STATE_FILE = "data/portal-state.json"
COURSE_URL = BASE_URL + "course/view.php?id=1326"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        storage_state=STATE_FILE,
        ignore_https_errors=True,
    )
    page = context.new_page()

    page.goto(COURSE_URL, wait_until="domcontentloaded", timeout=60000)

    if "/login/" in page.url:
        raise RuntimeError("Login expired. Run login.py first.")

    course_title = page.title().replace("Course: ", "")
    print(f"\nCOURSE: {course_title}")

    # Collect activities before navigating away from the course page.
    links = page.locator('a[href*="/mod/"]')
    activities = []
    seen = set()

    for i in range(links.count()):
        link = links.nth(i)

        href = link.get_attribute("href")
        name = " ".join(link.inner_text().split())

        if not href or not name:
            continue

        url = urljoin(BASE_URL, href)
        parsed = urlparse(url)

        if parsed.netloc != urlparse(BASE_URL).netloc:
            continue

        if url in seen:
            continue

        seen.add(url)
        activities.append((name, url))

    print(f"Found {len(activities)} activity links.")

    for name, url in activities:
        print("\n" + "-" * 65)
        print("LINK NAME:", name)
        print("LINK:", url)

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )
            page.wait_for_timeout(700)

            print("FINAL URL:", page.url)
            print(
                "HTTP STATUS:",
                response.status if response else "unknown",
            )
            print("PAGE TITLE:", repr(page.title()))

            # Extract visible text, with a limit to keep output manageable.
            try:
                body = " ".join(page.locator("body").inner_text().split())
                print("PAGE TEXT:", body[:1200])
            except Exception:
                print("PAGE TEXT: Could not extract text.")

            # Find links that may point to downloadable course files.
            file_links = page.locator(
                'a[href*="pluginfile.php"], '
                'a[href*="/mod/resource/"], '
                'a[href*="/mod/folder/"]'
            )

            for j in range(min(file_links.count(), 10)):
                item = file_links.nth(j)
                href = item.get_attribute("href")
                text = " ".join(item.inner_text().split())

                if href:
                    print(
                        "FILE LINK:",
                        text[:100],
                        "->",
                        urljoin(page.url, href),
                    )

        except Exception as e:
            print("INSPECTION ERROR:", str(e)[:200])

    input("\nDone. Press Enter to close...")
    browser.close()
