"""
Unit Tests for WinOptimize AI PySide6 Desktop GUI (Phase 3)
Tests UI initialization, view rendering, and metrics binding in offscreen mode.
"""

import os
import sys
import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui.main_window import MainWindow
from scanner.models import DiagnosticReport, SystemInfo, StartupFinding
from analyzer.process_analyzer import OptimizationRecommendation
from rules.rule_definitions import RuleRiskLevel


class TestDesktopUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure offscreen Qt platform for testing without an interactive desktop display
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.window = MainWindow(auto_scan=False)

    def tearDown(self):
        self.window.close()

    def test_main_window_structure(self):
        """Verify that MainWindow initializes all required pages and navigation buttons."""
        self.assertEqual(self.window.stack.count(), 6)
        self.assertEqual(len(self.window.nav_btns), 6)
        self.assertEqual(self.window.windowTitle(), "WinOptimize AI — Intelligent Background Process Optimizer")

    def test_dashboard_metrics_update(self):
        """Verify that dashboard cards update correctly from a DiagnosticReport."""
        report = DiagnosticReport(
            system=SystemInfo(
                caption="Microsoft Windows 11 Home",
                build_number="26200",
                architecture="64-bit",
                used_physical_memory_mb=8192.0,
                total_physical_memory_mb=16384.0,
                memory_usage_percent=50.0,
                cpu_load_percent=15.0,
            ),
            startup_entries_count=10,
            active_startup_count=4,
            scheduled_tasks_count=20,
            services_count=100,
        )

        self.window.dash_view.update_metrics(report, recommendations_count=3)
        self.assertEqual(self.window.dash_view.mem_bar.value(), 50)
        self.assertEqual(self.window.dash_view.cpu_bar.value(), 15)
        self.assertIn("10 Entries", self.window.dash_view.startup_card.val_lbl.text())
        self.assertIn("3 Optimization Suggestions", self.window.dash_view.recs_card.val_lbl.text())

    def test_recommendations_approval_flow(self):
        """Verify that recommendation cards can be approved and trigger optimization queue."""
        rec = OptimizationRecommendation(
            recommendation_id="REC-TEST-UI",
            category="StartupEntry",
            component_name="Opera Browser Assistant",
            target_identifier="Startup:Opera Browser Assistant",
            risk_level=RuleRiskLevel.LOW,
            confidence=0.95,
            title="Disable Opera Assistant",
            description="Background assistant",
            recommended_action="Disable",
            side_effects="None",
            reversibility_info="Restore",
            requires_elevation=False,
        )

        self.window.recs_view.populate([rec])
        self.assertEqual(len(self.window.recs_view.cards), 1)

        # Approve low risk
        self.window.recs_view._approve_all_low_risk()
        self.assertTrue(self.window.recs_view.cards[0].checkbox.isChecked())
        self.assertIn("Review & Apply (1)", self.window.recs_view.proceed_btn.text())


if __name__ == "__main__":
    unittest.main()
