"""Automatic update checker for TodoPro CLI."""

import json
import time
from pathlib import Path

import requests
from packaging import version
from platformdirs import user_cache_dir

from todopro_cli import __version__

CACHE_DIR = Path(user_cache_dir("todopro"))
CACHE_FILE = CACHE_DIR / "update_check.json"
PYPI_URL = "https://pypi.org/pypi/todopro-cli/json"
CHECK_INTERVAL = 3600  # 1 hour in seconds


def check_for_updates() -> None:
    """Check for updates from PyPI and display notification if available.

    This function:
    - Checks cache to avoid frequent API calls (max 1 check per hour)
    - Makes a quick PyPI API call with 0.5s timeout
    - Fails silently on network errors to not disrupt user experience
    - Displays update notification if newer version is available
    """
    now = time.time()
    latest_version = None

    # 1. Try reading from cache first
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            if now - data.get("last_check_timestamp", 0) < CHECK_INTERVAL:
                latest_version = data.get("latest_version")
        except Exception:
            pass

    # 2. If cache expired or missing, call PyPI
    if not latest_version:
        try:
            # Short timeout to avoid blocking the CLI
            res = requests.get(PYPI_URL, timeout=0.5)
            if res.status_code == 200:
                latest_version = res.json()["info"]["version"]
                # Update cache
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                CACHE_FILE.write_text(
                    json.dumps(
                        {"last_check_timestamp": now, "latest_version": latest_version}
                    )
                )
        except Exception:
            return  # Fail silently on network errors

    # 3. Display notification if newer version available
    if latest_version and version.parse(latest_version) > version.parse(__version__):
        print(
            f"\n\033[93m✨ New version available: {latest_version} (Current: {__version__})"
        )
        print("👉 Run: 'uv tool upgrade todopro-cli' to update.\033[0m\n")
