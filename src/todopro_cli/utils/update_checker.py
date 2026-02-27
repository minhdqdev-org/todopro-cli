"""Automatic update checker for TodoPro CLI."""

import json
import os
import time
from pathlib import Path

import httpx
from packaging import version
from platformdirs import user_cache_dir

from todopro_cli import __version__

CACHE_DIR = Path(user_cache_dir("todopro"))
CACHE_FILE = CACHE_DIR / "update_check.json"

CHECK_INTERVAL = 3600  # 1 hour in seconds
DEFAULT_BACKEND_URL = "https://todopro.minhdq.dev/api"


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

    # 2. If cache expired or missing, fetch from PyPI
    if not latest_version:
        try:
            response = httpx.get("https://pypi.org/pypi/todopro-cli/json", timeout=0.5)
            if response.status_code == 200:
                latest_version = response.json()["info"]["version"]
                # Save to cache
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                CACHE_FILE.write_text(
                    json.dumps(
                        {"latest_version": latest_version, "last_check_timestamp": now}
                    )
                )
        except Exception:
            # Silently fail on network errors
            pass

    # 3. Display notification if newer version available
    if latest_version and version.parse(latest_version) > version.parse(__version__):
        print(
            f"\n\033[93m✨ New version available: {latest_version} (Current: {__version__})"
        )
        print("👉 Run: 'uv tool upgrade todopro-cli' to update.\033[0m\n")


def get_latest_version() -> str | None:
    """Get the latest version from PyPI.

    Returns:
        Latest version string or None if unable to fetch
    """
    now = time.time()

    # Check cache first
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            # Use cache if it's less than 5 minutes old for update command
            if now - data.get("last_check_timestamp", 0) < 300:
                return data.get("latest_version")
        except Exception:
            pass

    # Fetch from PyPI
    try:
        response = httpx.get("https://pypi.org/pypi/todopro-cli/json", timeout=2)
        if response.status_code == 200:
            latest_version = response.json()["info"]["version"]
            # Cache the result
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(
                json.dumps(
                    {"latest_version": latest_version, "last_check_timestamp": now}
                )
            )
            return latest_version
    except Exception:
        pass
    return None


def is_update_available() -> tuple[bool, str | None]:
    """Check if an update is available.

    Returns:
        Tuple of (is_available, latest_version)
    """
    latest_version = get_latest_version()
    if latest_version and version.parse(latest_version) > version.parse(__version__):
        return True, latest_version
    return False, latest_version


def get_backend_url() -> str:
    """Get backend URL with priority: env var > cache > PyPI > default.

    Priority hierarchy:
    1. Environment variable (TODOPRO_BACKEND_URL) - highest priority for dev/testing
    2. Local cache - if PyPI was fetched within last hour
    3. PyPI metadata - fetch from project_urls.Backend
    4. Hard-coded fallback - default URL

    Returns:
        Backend URL string
    """
    # Priority 1: Environment variable
    env_url = os.getenv("TODOPRO_BACKEND_URL")
    if env_url:
        return env_url.rstrip("/")

    # Priority 2: Check cache
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            # If cache is fresh (less than 1 hour old), use cached backend URL
            if time.time() - data.get("last_check_timestamp", 0) < CHECK_INTERVAL:
                backend_url = data.get("backend_url")
                if backend_url:
                    return backend_url.rstrip("/")
        except Exception:
            pass

    # Priority 3: Fetch from PyPI metadata
    try:
        response = httpx.get("https://pypi.org/pypi/todopro-cli/json", timeout=2)
        if response.status_code == 200:
            data = response.json()
            backend_url = data.get("info", {}).get("project_urls", {}).get("Backend")
            if backend_url:
                # Cache it
                cache_data = {}
                if CACHE_FILE.exists():
                    try:
                        cache_data = json.loads(CACHE_FILE.read_text())
                    except Exception:
                        pass
                cache_data["backend_url"] = backend_url
                cache_data["last_check_timestamp"] = time.time()
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                CACHE_FILE.write_text(json.dumps(cache_data))
                return backend_url.rstrip("/")
    except Exception:
        pass

    # Priority 4: Try to use cached backend URL even if expired
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            backend_url = data.get("backend_url")
            if backend_url:
                return backend_url.rstrip("/")
        except Exception:
            pass

    # Final fallback: Hard-coded default
    return DEFAULT_BACKEND_URL
