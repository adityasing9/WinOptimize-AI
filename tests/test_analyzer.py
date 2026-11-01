"""
Unit Tests for WinOptimize AI Analysis and Rules Engine (Phase 2)
Tests rule matching, protected component enforcement, preference persistence, and recommendations.
"""

import os
import tempfile
import unittest
from pathlib import Path

from rules.rule_definitions import RuleRiskLevel, RuleCategory
from rules.rules_engine import RulesEngine
from storage.database import DatabaseManager
from analyzer.process_analyzer import ProcessAnalyzer, OptimizationRecommendation
from scanner.models import (
    DiagnosticReport,
    SystemInfo,
    StartupFinding,
    ScheduledTaskFinding,
    ProcessFinding,
    ServiceFinding,
)


class TestRulesAndAnalyzer(unittest.TestCase):
    def setUp(self):
        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp_db.close()
        self.db = DatabaseManager(db_path=self.tmp_db.name)
        self.rules_engine = RulesEngine()
        self.analyzer = ProcessAnalyzer(rules_engine=self.rules_engine, db_manager=self.db)

    def tearDown(self):
        if os.path.exists(self.tmp_db.name):
            try:
                os.remove(self.tmp_db.name)
            except OSError:
                pass

    def test_protected_components_cannot_be_recommended(self):
        """Verify that essential Windows components are strictly marked PROTECTED and cannot be optimized."""
        # Windows Defender process
        self.assertTrue(self.rules_engine.is_protected_process("MsMpEng.exe"))
        self.assertTrue(self.rules_engine.is_protected_process("dwm.exe"))
        self.assertTrue(self.rules_engine.is_protected_process("lsass.exe"))

        # Windows Defender service
        self.assertTrue(self.rules_engine.is_protected_service("WinDefend"))
        self.assertTrue(self.rules_engine.is_protected_service("MpsSvc"))
        self.assertTrue(self.rules_engine.is_protected_service("Audiosrv"))

        # Protected startup entry check
        res = self.rules_engine.evaluate_startup_entry("SecurityHealth", "C:\\Windows\\System32\\SecurityHealthSystray.exe")
        self.assertTrue(res.is_protected)
        self.assertEqual(res.risk_level, RuleRiskLevel.PROTECTED)

    def test_rule_matching_and_risk_classification(self):
        """Verify accurate matching for third-party background software."""
        # Opera Assistant
        res = self.rules_engine.evaluate_startup_entry("Opera Browser Assistant", "browser_assistant.exe")
        self.assertTrue(res.is_matched)
        self.assertEqual(res.risk_level, RuleRiskLevel.LOW)
        self.assertGreaterEqual(res.confidence, 0.90)

        # Discord
        res_discord = self.rules_engine.evaluate_startup_entry("Discord", "Discord.exe")
        self.assertTrue(res_discord.is_matched)
        self.assertEqual(res_discord.risk_level, RuleRiskLevel.LOW)

        # Docker Desktop (CONDITIONAL due to virtualization/WSL impact)
        res_docker = self.rules_engine.evaluate_startup_entry("Docker Desktop", "Docker Desktop.exe")
        self.assertTrue(res_docker.is_matched)
        self.assertEqual(res_docker.risk_level, RuleRiskLevel.CONDITIONAL)

    def test_user_preferences_persistence(self):
        """Verify that user preferences saved to SQLite correctly override recommendations."""
        self.db.set_user_preference("Startup:Discord", "Discord", "keep_enabled")
        pref = self.db.get_user_preference("Startup:Discord")
        self.assertEqual(pref, "keep_enabled")

        report = DiagnosticReport(
            startup_entries=[
                StartupFinding(name="Discord", command="Discord.exe", is_enabled=True),
                StartupFinding(name="Opera Browser Assistant", command="browser_assistant.exe", is_enabled=True),
            ]
        )

        recs = self.analyzer.analyze(report)
        target_names = [r.component_name for r in recs]
        # Discord should be excluded because user marked it as 'keep_enabled'
        self.assertNotIn("Discord", target_names)
        self.assertIn("Opera Browser Assistant", target_names)

    def test_process_correlation(self):
        """Verify that running processes are correlated to matching startup recommendations."""
        report = DiagnosticReport(
            top_processes=[
                ProcessFinding(pid=4567, name="browser_assistant.exe", working_set_mb=85.2),
            ],
            startup_entries=[
                StartupFinding(name="Opera Browser Assistant", command="browser_assistant.exe", is_enabled=True),
            ]
        )

        recs = self.analyzer.analyze(report)
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertEqual(rec.component_name, "Opera Browser Assistant")

    def test_background_process_and_bloatware_detection(self):
        """Verify that high-RAM background apps and bloatware tasks are detected."""
        report = DiagnosticReport(
            top_processes=[
                ProcessFinding(pid=1001, name="brave.exe", working_set_mb=450.0),
                ProcessFinding(pid=1002, name="brave.exe", working_set_mb=350.0),
                ProcessFinding(pid=2001, name="msedge.exe", working_set_mb=260.0),
                ProcessFinding(pid=3001, name="MsMpEng.exe", working_set_mb=350.0),  # Protected
            ],
            scheduled_tasks=[
                ScheduledTaskFinding(task_name="App Explorer", task_path="\\", state="Running"),
            ]
        )

        recs = self.analyzer.analyze(report)
        categories = [r.category for r in recs]
        names = [r.component_name for r in recs]

        # MsMpEng must NOT be recommended (protected)
        self.assertFalse(any("MsMpEng" in n for n in names))

        # Brave and Edge must be recommended under BackgroundProcess
        self.assertIn("BackgroundProcess", categories)
        self.assertTrue(any("brave" in n.lower() for n in names))
        self.assertTrue(any("msedge" in n.lower() for n in names))

        # App Explorer must be recommended under ScheduledTask
        self.assertIn("ScheduledTask", categories)
        self.assertIn("App Explorer", names)

    def test_service_detection_gaming_speedify_warp_mongodb(self):
        """Verify that Gaming Services, Speedify, WARP, and MongoDB are detected and recommended."""
        report = DiagnosticReport(
            services_overview=[
                ServiceFinding(name="GamingServices", display_name="Gaming Services", status="Running", start_mode="Auto", is_microsoft=True),
                ServiceFinding(name="Speedify", display_name="Speedify", status="Running", start_mode="Auto", is_microsoft=False),
                ServiceFinding(name="CloudflareWARP", display_name="Cloudflare WARP", status="Running", start_mode="Auto", is_microsoft=False),
                ServiceFinding(name="MongoDB", display_name="MongoDB Server", status="Running", start_mode="Auto", is_microsoft=False),
                ServiceFinding(name="RpcSs", display_name="Remote Procedure Call (RPC)", status="Running", start_mode="Auto", is_microsoft=True),
            ]
        )

        recs = self.analyzer.analyze(report)
        svc_names = [r.component_name for r in recs if r.category == RuleCategory.SERVICE.value]

        # RpcSs is core protected system service -> must NOT be present
        self.assertNotIn("Remote Procedure Call (RPC)", svc_names)

        # Gaming Services, Speedify, WARP, and MongoDB must all be detected
        self.assertIn("Gaming Services", svc_names)
        self.assertIn("Speedify", svc_names)
        self.assertIn("Cloudflare WARP", svc_names)
        self.assertIn("MongoDB Server", svc_names)


if __name__ == "__main__":
    unittest.main()
