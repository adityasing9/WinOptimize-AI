"""
WinOptimize AI - In-App Updater Module
Checks GitHub releases, downloads updates, and applies self-updates in-place.
"""

from .in_app_updater import InAppUpdater, ReleaseInfo, APP_VERSION

__all__ = ["InAppUpdater", "ReleaseInfo", "APP_VERSION"]
