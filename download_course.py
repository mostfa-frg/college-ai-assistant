
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
import re

from playwright.sync_api import sync_playwright

BASE_URL = "https://learn3.sha.edu.eg/"
STATE_FILE = "data/portal-state.json"
COURSE_URL = BASE_URL + "course/view.php?id=1326"
OUTPUT_DIR = Path("data/materials/distributed_systems")


def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name.strip(" .") or "downloaded_file"


def download_file(context, url, output_dir):
    response = context.request.get(url, timeout=60000)

    if not response.ok:
        print(f"  FAILED: HTTP {response.status}")
        return

    # Use the filename from the URL.
    filename = unquote(Path(urlparse(url).path).name)
    filename = safe_filename(filename)

    if not filename:
        filename = "downloaded_file"

    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / filename

    # Avoid silently overwriting an existing file.
    if destination.exists():
        print(f"  EXISTS: {destination.name}")
        return

    content = response.body()

    # Basic PDF signature check; don't save HTML login pages as PDFs.
    if url.lower().endswith(".pdf") and not content.startswith(b"%PDF-"):
        print(f"  SKIPPED: {filename} (response is not a PDF)")
        return

    destination.write_bytes(content)
    print(f"  SAVED: {destination} ({len(content):,} bytes)")


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

    activities = []
    links = page.locator('a[href*="/mod/"]')
    seen = set()

    for i in range(links.count()):
        link = links.nth(i)
        href = link.get_attribute("href")
        name = " ".join(link.inner_text().split())

        if not href or not name:
            continue

        url = urljoin(BASE_URL, href)

        if url not in seen:
            seen.add(url)
            activities.append((name, url))

    print(f"Found {len(activities)} activities.")

    for name, url in activities:
        path = urlparse(url).path

        # Download lecture/resource files.
        if "/mod/resource/view.php" in path:
            print(f"\nRESOURCE: {name}")

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            if response and response.ok:
                final_url = page.url
                if "/pluginfile.php/" in urlparse(final_url).path:
                    download_file(context, final_url, OUTPUT_DIR)
                else:
                    print("  No direct file URL detected.")
            else:
                print("  Could not open resource.")

        # Download files inside a course folder.
        elif "/mod/folder/view.php" in path:
            print(f"\nFOLDER: {name}")

            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            file_links = page.locator(
                'a[href*="/pluginfile.php/"][href*="mod_folder/content"]'
            )

            folder_files = []
            for j in range(file_links.count()):
                href = file_links.nth(j).get_attribute("href")
                if href:
                    folder_files.append(urljoin(page.url, href))

            for file_url in dict.fromkeys(folder_files):
                download_file(context, file_url, OUTPUT_DIR)

        # Download assignment instructions/attachments only.
        # Intentionally exclude personal submitted files.
        elif "/mod/assign/view.php" in path:
            print(f"\nASSIGNMENT ATTACHMENTS: {name}")

            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            attachment_links = page.locator(
                'a[href*="/pluginfile.php/"][href*="mod_assign/introattachment"]'
            )

            urls = []
            for j in range(attachment_links.count()):
                href = attachment_links.nth(j).get_attribute("href")
                if href:
                    urls.append(urljoin(page.url, href))

            if not urls:
                print("  No downloadable instruction attachments found.")

            for file_url in dict.fromkeys(urls):
                download_file(context, file_url, OUTPUT_DIR)

    print(f"\nFinished. Files are in: {OUTPUT_DIR.resolve()}")
    input("Press Enter to close...")
    browser.close()
