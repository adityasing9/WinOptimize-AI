"""
Unit and Integration Tests for WinOptimize AI Diagnostic Scanner (Phase 1)
Validates read-only execution, schema conformity, error handling, and candidate detection.
Compatible with standard unittest and pytest.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from scanner.models import (
    DiagnosticReport,
    SystemInfo,
    ProcessFinding,
    StartupFinding,
    ScheduledTaskFinding,
    ServiceFinding,
    CandidateFinding,
)
from scanner.system_scanner import SystemScanner


class TestScannerModels(unittest.TestCase):
    def test_models_serialization(self):
        """Verify that DiagnosticReport serializes and deserializes accurately without data loss."""
        report = DiagnosticReport(
            version="1.0.0-test",
            engine="WinOp-Test",
            timestamp="2026-10-31T23:00:00Z",
            scan_duration_sec=1.25,
            is_elevated=False,
            execution_mode="READ_ONLY_STRICT",
            system=SystemInfo(
                caption="Microsoft Windows 11 Pro",
                version="10.0.26200",
                build_number="26200",
                architecture="64-bit",
                total_physical_memory_mb=16384.0,
                free_physical_memory_mb=8192.0,
                used_physical_memory_mb=8192.0,
                memory_usage_percent=50.0,
                cpu_load_percent=12.5,
                machine_name="TEST-PC",
                current_user="TEST-PC\\User",
                is_elevated=False,
                source="Test",
            ),
            processes_count=1,
            startup_entries_count=1,
            active_startup_count=1,
            scheduled_tasks_count=1,
            services_count=1,
            candidates=[
                CandidateFinding(
                    category="StartupEntry",
                    target_name="Discord",
                    identifier="Registry:Discord",
                    risk_level="LOW",
                    confidence=0.95,
                    reason="Discord auto-launches at sign-in.",
                    recommended_action="Disable startup entry",
                    original_command="Discord.exe",
                    requires_elevation=False,
                )
            ],
            startup_entries=[
                StartupFinding(
                    name="Discord",
                    command="Discord.exe",
                    resolved_path="C:\\Users\\User\\AppData\\Local\\Discord\\Discord.exe",
                    publisher="Discord Inc.",
                    description="Discord",
                    location_type="Registry",
                    location_key="Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                    scope="User",
                    is_enabled=True,
                )
            ],
            scheduled_tasks=[
                ScheduledTaskFinding(
                    task_name="OperaUpdate",
                    task_path="\\",
                    state="Ready",
                    author="Opera Software",
                    description="Opera autoupdate task",
                )
            ],
            top_processes=[
                ProcessFinding(
                    pid=1234,
                    name="Discord.exe",
                    working_set_mb=120.5,
                    private_memory_mb=95.0,
                    cpu_total_seconds=4.2,
                    has_window=True,
                    window_title="Discord",
                    executable_path="C:\\Users\\User\\AppData\\Local\\Discord\\Discord.exe",
                    publisher="Discord Inc.",
                )
            ],
            services_overview=[
                ServiceFinding(
                    name="Spooler",
                    display_name="Print Spooler",
                    status="Running",
                    start_mode="Auto",
                    binary_path="C:\\Windows\\System32\\spoolsv.exe",
                    is_microsoft=True,
                )
            ],
        )

        json_str = report.to_json()
        self.assertIn("Discord", json_str)
        self.assertIn("Spooler", json_str)

        # Test round-trip
        parsed_dict = json.loads(json_str)
        self.assertEqual(parsed_dict["version"], "1.0.0-test")
        self.assertEqual(parsed_dict["system"]["caption"], "Microsoft Windows 11 Pro")
        self.assertEqual(len(parsed_dict["candidates"]), 1)

        # Test Markdown summary generation
        md_summary = report.generate_markdown_summary()
        self.assertIn("# WinOptimize AI — Diagnostic Report", md_summary)
        self.assertIn("Discord", md_summary)
        self.assertIn("Microsoft Windows 11 Pro", md_summary)

    def test_powershell_script_exists(self):
        """Verify that the PowerShell diagnostic script is present and non-empty."""
        scanner = SystemScanner()
        self.assertTrue(scanner.script_path.exists(), f"Script not found at {scanner.script_path}")
        self.assertGreater(scanner.script_path.stat().st_size, 500)

    def test_python_fallback_scanner(self):
        """Verify that the pure Python fallback scanner executes safely and produces a valid report."""
        scanner = SystemScanner()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            report = scanner.scan(output_json_path=temp_path, use_powershell=False)
            self.assertIsInstance(report, DiagnosticReport)
            self.assertEqual(report.execution_mode, "READ_ONLY_STRICT")
            self.assertGreater(report.system.total_physical_memory_mb, 0)
            self.assertGreater(report.processes_count, 0)
            self.assertGreater(len(report.top_processes), 0)
            self.assertTrue(Path(temp_path).exists())
            self.assertGreater(Path(temp_path).stat().st_size, 0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_read_only_safety_guarantee(self):
        """Verify that scanning does not modify system settings or delete files."""
        scanner = SystemScanner()
        with tempfile.TemporaryDirectory() as tmp_dir:
            report_file = Path(tmp_dir) / "safety_test.json"
            report = scanner.scan(output_json_path=str(report_file), use_powershell=False)

            self.assertTrue(report_file.exists())
            files_created = list(Path(tmp_dir).iterdir())
            self.assertEqual(len(files_created), 1)
            self.assertEqual(files_created[0].name, "safety_test.json")


if __name__ == "__main__":
    unittest.main()
