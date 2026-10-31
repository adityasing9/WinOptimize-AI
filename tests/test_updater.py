"""
WinOptimize AI - Updater & Themes Unit Tests
"""

import unittest
from updater.in_app_updater import InAppUpdater, APP_VERSION
from ui.styles import THEMES
from ui.views.settings_view import SettingsView


class TestUpdaterAndThemes(unittest.TestCase):
    def setUp(self):
        self.updater = InAppUpdater(current_version="1.0.0")

    def test_version_comparison_logic(self):
        # 1.0.1 is newer than 1.0.0
        self.assertTrue(self.updater._compare_versions("1.0.1", "1.0.0"))
        # 2.0.0 is newer than 1.9.9
        self.assertTrue(self.updater._compare_versions("2.0.0", "1.9.9"))
        # 1.0.0 is not newer than 1.0.0
        self.assertFalse(self.updater._compare_versions("1.0.0", "1.0.0"))
        # 1.0.0 is not newer than 1.0.1
        self.assertFalse(self.updater._compare_versions("1.0.0", "1.0.1"))

    def test_all_12_themes_defined(self):
        expected_themes = [
            "dark",
            "midnight",
            "nordic",
            "emerald",
            "amber",
            "cyberpunk",
            "dracula",
            "crimson",
            "tokyo_night",
            "solarized_dark",
            "rose_pine",
            "light",
        ]
        self.assertEqual(len(THEMES), 12)
        for theme_key in expected_themes:
            self.assertIn(theme_key, THEMES)
            self.assertTrue(len(THEMES[theme_key]) > 100)

    def test_settings_view_theme_keys_match(self):
        self.assertEqual(SettingsView.THEME_KEYS, list(THEMES.keys()))
        self.assertEqual(len(SettingsView.THEME_LABELS), 12)


if __name__ == "__main__":
    unittest.main()
