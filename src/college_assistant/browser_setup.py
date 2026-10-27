from __future__ import annotations

import os
import subprocess
from pathlib import Path

from playwright._impl._driver import compute_driver_executable

from college_assistant.config import BROWSER_DIR, FROZEN


def ensure_chromium_installed(playwright) -> None:
    """Install Chromium on first use instead of shipping it inside the app ZIP."""
    executable = Path(playwright.chromium.executable_path)
    if executable.is_file():
        return

    if FROZEN:
        if BROWSER_DIR is None:
            raise RuntimeError("The browser cache directory is not configured.")
        BROWSER_DIR.mkdir(parents=True, exist_ok=True)
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSER_DIR)

    print("Chromium is not installed yet. Downloading it now (one-time setup)...")
    print("Keep the app open and connected to the internet until setup finishes.")

    driver_executable, driver_cli = compute_driver_executable()
    try:
        subprocess.run(
            [str(driver_executable), str(driver_cli), "install", "chromium"],
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "Could not download the required Chromium browser. Check your internet "
            "connection and try the Moodle login/sync option again."
        ) from exc

    if not Path(playwright.chromium.executable_path).is_file():
        raise RuntimeError(
            "Chromium installation finished, but its executable was not found. "
            "Try running the app again; if the problem continues, reinstall the app."
        )

    print("Chromium is ready.")
