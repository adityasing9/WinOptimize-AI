"""
WinOptimize AI - In-App Self-Updating Engine
Enables users to check, download, and apply updates directly inside the application.
"""

from __future__ import annotations
import json
import logging
import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger("WinOp.Updater")

APP_VERSION = "1.0.2"
GITHUB_REPO = "adityasing9/WinOptimize-AI"
API_LATEST_RELEASE = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class ReleaseInfo:
    tag_name: str
    version: str
    title: str
    release_notes: str
    download_url: str
    asset_name: str
    asset_size_mb: float
    is_newer: bool


class InAppUpdater:
    """
    Handles version checking, direct binary download from GitHub Releases,
    and graceful in-place application restarts.
    """

    def __init__(self, current_version: str = APP_VERSION):
        self.current_version = current_version.lstrip("v")

    def check_for_updates(self, timeout: int = 10) -> Optional[ReleaseInfo]:
        """
        Queries GitHub API for the latest published release.
        """
        req = urllib.request.Request(
            API_LATEST_RELEASE,
            headers={"User-Agent": "WinOptimizeAI-Updater"},
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    logger.warning("GitHub Releases API returned HTTP %d", resp.status)
                    return None
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
            logger.error("Failed to check for updates from GitHub: %s", e)
            return None

        tag = data.get("tag_name", "")
        remote_ver = tag.lstrip("v")
        title = data.get("name", tag)
        notes = data.get("body", "")

        # Look for WinOptimizeAI.exe in assets
        download_url = ""
        asset_name = ""
        asset_size = 0.0

        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if name == "WinOptimizeAI.exe":
                download_url = asset.get("browser_download_url", "")
                asset_name = name
                asset_size = round(asset.get("size", 0) / (1024 * 1024), 1)
                break

        # Fallback to zip if exe alone is not present
        if not download_url:
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".zip"):
                    download_url = asset.get("browser_download_url", "")
                    asset_name = name
                    asset_size = round(asset.get("size", 0) / (1024 * 1024), 1)
                    break

        if not download_url:
            logger.warning("No downloadable binary asset found in latest release.")
            return None

        is_newer = self._compare_versions(remote_ver, self.current_version)

        return ReleaseInfo(
            tag_name=tag,
            version=remote_ver,
            title=title,
            release_notes=notes,
            download_url=download_url,
            asset_name=asset_name,
            asset_size_mb=asset_size,
            is_newer=is_newer,
        )

    def _compare_versions(self, remote: str, current: str) -> bool:
        """Returns True if remote is strictly newer than current, using semver tuple comparison."""
        try:
            r_parts = [int(p) for p in remote.split(".") if p.isdigit()]
            c_parts = [int(p) for p in current.split(".") if p.isdigit()]
            return r_parts > c_parts
        except Exception:
            return remote != current

    def download_and_apply_update(
        self,
        download_url: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """
        Downloads new binary to temp file and spawns atomic replacement script.
        """
        current_exe = Path(sys.executable).resolve()
        temp_dir = Path(tempfile.gettempdir())
        new_exe = temp_dir / "WinOptimizeAI_new.exe"

        # Download with chunked progress updates
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "WinOptimizeAI-Updater"},
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response, open(new_exe, "wb") as out_file:
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                chunk_size = 64 * 1024  # 64 KB chunks

                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and progress_callback:
                        pct = int((downloaded / total_size) * 100)
                        progress_callback(pct)
        except Exception as e:
            logger.error("Download failed: %s", e)
            if new_exe.exists():
                try:
                    new_exe.unlink()
                except OSError:
                    pass
            return False

        # If running from source (python app/main.py), just report successful download
        if not getattr(sys, "frozen", False):
            logger.info("Running in development mode; downloaded update to %s", new_exe)
            return True

        # Generate atomic Windows batch script to swap the binary after process termination
        batch_script = temp_dir / "winop_update_apply.bat"
        script_content = f"""@echo off
timeout /t 1 /nobreak > nul
:retry
move /y "{new_exe}" "{current_exe}" > nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak > nul
    goto retry
)
start "" "{current_exe}"
del "%~f0"
"""
        try:
            with open(batch_script, "w", encoding="utf-8") as f:
                f.write(script_content)

            # Spawn updater detached and exit current application
            subprocess.Popen(
                ["cmd.exe", "/c", str(batch_script)],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                close_fds=True,
            )
            logger.info("Spawned in-place updater script. Exiting current process.")
            sys.exit(0)
        except Exception as e:
            logger.error("Failed to launch atomic update script: %s", e)
            return False
