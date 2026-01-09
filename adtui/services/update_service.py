"""Update service for checking and performing updates."""

import json
import logging
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger(__name__)

# Update check interval (24 hours in seconds)
UPDATE_CHECK_INTERVAL = 86400

# Git repository URLs for update checking and installation
REPO_URLS = [
    ("servgitea.domman.ad", "ti2103", "adtui"),
    ("github.com", "brz-admin", "adtui"),
]

# Install directory
INSTALL_DIR = Path.home() / ".local" / "share" / "adtui"
VENV_DIR = INSTALL_DIR / "venv"


@dataclass
class UpdateCheckResult:
    """Result of an update check."""
    current_version: str
    latest_version: Optional[str]
    update_available: bool
    error: Optional[str] = None


class UpdateService:
    """Service for checking and applying updates."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the update service.

        Args:
            cache_dir: Directory to store update check cache
        """
        self.cache_dir = cache_dir or (Path.home() / ".config" / "adtui")
        self.cache_file = self.cache_dir / "update_check.json"
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> dict:
        """Load cached update check data."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return {}

    def _save_cache(self, data: dict) -> None:
        """Save update check data to cache."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(data, f)
        except IOError as e:
            logger.debug(f"Failed to save update cache: {e}")

    def _should_check(self) -> bool:
        """Check if enough time has passed since last check."""
        cache = self._load_cache()
        last_check = cache.get("last_check", 0)
        return (time.time() - last_check) > UPDATE_CHECK_INTERVAL

    def _get_current_version(self) -> str:
        """Get current installed version."""
        try:
            from importlib.metadata import version
            return version("adtui")
        except Exception:
            try:
                from adtui import __version__
                return __version__
            except Exception:
                return "0.0.0"

    def _fetch_latest_version(self) -> Optional[str]:
        """Fetch latest version from git tags.

        Tries multiple repository URLs in order.
        Returns the latest version tag or None if failed.
        """
        for host, owner, repo in REPO_URLS:
            try:
                if "github.com" in host:
                    api_url = f"https://api.github.com/repos/{owner}/{repo}/tags"
                else:
                    # Gitea API
                    api_url = f"https://{host}/api/v1/repos/{owner}/{repo}/tags"

                req = Request(api_url, headers={
                    "Accept": "application/json",
                    "User-Agent": "adtui-update-checker"
                })
                with urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())

                    if data:
                        # Get first tag (usually most recent)
                        # Filter for version tags (vX.Y.Z or X.Y.Z)
                        for tag in data:
                            tag_name = tag.get("name", "")
                            if tag_name.startswith("v"):
                                return tag_name[1:]  # Remove 'v' prefix
                            elif tag_name and tag_name[0].isdigit():
                                return tag_name

            except (URLError, json.JSONDecodeError, KeyError, TimeoutError, OSError) as e:
                logger.debug(f"Failed to fetch from {host}: {e}")
                continue

        return None

    def _compare_versions(self, current: str, latest: str) -> bool:
        """Compare versions. Returns True if latest > current."""
        def parse_version(v: str) -> Tuple[int, ...]:
            """Parse version string to tuple of integers."""
            # Remove any suffix like -dev, -beta, etc.
            v = v.split("-")[0].split("+")[0]
            parts = []
            for part in v.split(".")[:3]:
                try:
                    parts.append(int(part))
                except ValueError:
                    parts.append(0)
            # Pad to 3 parts
            while len(parts) < 3:
                parts.append(0)
            return tuple(parts)

        try:
            return parse_version(latest) > parse_version(current)
        except Exception:
            return False

    def check_for_update(self, force: bool = False) -> UpdateCheckResult:
        """Check for updates.

        Args:
            force: If True, ignore cache and check anyway

        Returns:
            UpdateCheckResult with version information
        """
        current = self._get_current_version()

        # Return cached result if recent enough
        if not force and not self._should_check():
            cache = self._load_cache()
            cached_latest = cache.get("latest_version")
            if cached_latest:
                return UpdateCheckResult(
                    current_version=current,
                    latest_version=cached_latest,
                    update_available=self._compare_versions(current, cached_latest),
                )

        # Fetch latest version
        latest = self._fetch_latest_version()

        # Update cache
        self._save_cache({
            "last_check": time.time(),
            "latest_version": latest,
            "current_version": current,
        })

        if latest is None:
            return UpdateCheckResult(
                current_version=current,
                latest_version=None,
                update_available=False,
                error="Could not fetch latest version",
            )

        return UpdateCheckResult(
            current_version=current,
            latest_version=latest,
            update_available=self._compare_versions(current, latest),
        )

    def check_for_update_async(
        self, callback: Callable[[UpdateCheckResult], None]
    ) -> threading.Thread:
        """Check for updates in background thread.

        Args:
            callback: Function to call with result

        Returns:
            The background thread
        """
        def _check():
            try:
                result = self.check_for_update()
                callback(result)
            except Exception as e:
                logger.debug(f"Async update check failed: {e}")

        thread = threading.Thread(target=_check, daemon=True)
        thread.start()
        return thread

    def perform_update(self) -> Tuple[bool, str]:
        """Perform the actual update.

        Returns:
            Tuple of (success, message)
        """
        # Check if installed in venv
        if not VENV_DIR.exists():
            return False, "ADTUI venv not found. Update manually with: pip install --upgrade adtui"

        pip_path = VENV_DIR / "bin" / "pip"
        if not pip_path.exists():
            pip_path = VENV_DIR / "Scripts" / "pip.exe"  # Windows

        if not pip_path.exists():
            return False, "pip not found in venv"

        # Try updating from git repos
        for host, owner, repo in REPO_URLS:
            try:
                if "github.com" in host:
                    repo_url = f"https://{host}/{owner}/{repo}.git"
                else:
                    repo_url = f"https://{host}/{owner}/{repo}.git"

                result = subprocess.run(
                    [str(pip_path), "install", "--upgrade", f"git+{repo_url}"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    # Clear the cache so next check shows current version
                    self._save_cache({})
                    return True, f"Successfully updated from {host}"
            except subprocess.TimeoutExpired:
                continue
            except Exception as e:
                logger.debug(f"Update from {host} failed: {e}")
                continue

        return False, "Failed to update from any repository"
