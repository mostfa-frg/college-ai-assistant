
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin, urlparse

BASE_URL = "https://learn3.sha.edu.eg/my/"
STATE_FILE = "data/portal-state.json"
MAX_LINKS_PER_COURSE = 60

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        storage_state=STATE_FILE,
        ignore_https_errors=True,
    )
    page = context.new_page()

    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=20000)

    if "/login/" in page.url:
        raise RuntimeError("Login expired. Please run login.py first.")

    # Discover courses from the dashboard
    course_links = page.locator('a[href*="/course/view.php?id="]')
    courses = []
    seen_courses = set()

    for i in range(course_links.count()):
        link = course_links.nth(i)
        href = link.get_attribute("href")
        name = " ".join(link.inner_text().split())

        if not href:
            continue

        url = urljoin(BASE_URL, href)
        course_id = urlparse(url).query

        if url not in seen_courses and name:
            seen_courses.add(url)
            courses.append((name, url))

    print(f"\nFound {len(courses)} course links.\n")

    for course_name, course_url in courses:
        print("\n" + "=" * 70)
        print("COURSE:", course_name)
        print("URL:", course_url)

        try:
            response = page.goto(
                course_url,
                wait_until="domcontentloaded",
                timeout=60000,
            )
            page.wait_for_timeout(1200)

            if "/login/" in page.url:
                print("Login required; stopping.")
                break

            print("PAGE TITLE:", repr(page.title()))

            # Extract links to likely course activities/resources
            links = page.locator("a[href]")
            seen = set()
            count = 0

            for i in range(links.count()):
                link = links.nth(i)

                try:
                    href = link.get_attribute("href")
                    text = " ".join(link.inner_text().split())

                    if not href or not text:
                        continue

                    full_url = urljoin(page.url, href)
                    parsed = urlparse(full_url)

                    if parsed.netloc != urlparse(BASE_URL).netloc:
                        continue

                    activity_paths = (
                        "/mod/",
                        "/course/view.php",
                        "/pluginfile.php",
                    )

                    if not any(path in parsed.path for path in activity_paths):
                        continue

                    item = (text, full_url)
                    if item in seen:
                        continue

                    seen.add(item)
                    print(f"- {text[:100]} -> {full_url}")
                    count += 1

                    if count >= MAX_LINKS_PER_COURSE:
                        print("... link limit reached")
                        break

                except Exception:
                    continue

            if count == 0:
                print("No activity links found on this page.")

        except Exception as e:
            print("Could not inspect course:", str(e)[:200])

    input("\nInspection complete. Press Enter to close...")
    browser.close()
