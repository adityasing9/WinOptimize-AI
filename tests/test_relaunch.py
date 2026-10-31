"""
Unit Tests for WinOptimize AI Relaunch Diagnostics (Phase 5)
Tests root cause identification, scheduled task correlation, and report models.
"""

import unittest
from monitoring.relaunch_detector import RelaunchEvent, RelaunchReport, RelaunchDiagnosticSession
from scanner.models import DiagnosticReport, ScheduledTaskFinding, TaskAction, ServiceFinding, StartupFinding


class TestRelaunchDiagnostics(unittest.TestCase):
    def setUp(self):
        self.session = RelaunchDiagnosticSession(target_names=["opera_assistant"], duration_seconds=5)

    def test_determine_cause_scheduled_task(self):
        """Verify that a relaunch with a matching scheduled task is correctly identified with evidence."""
        mock_report = DiagnosticReport(
            scheduled_tasks=[
                ScheduledTaskFinding(
                    task_name="Opera GX scheduled assistant Autoupdate",
                    task_path="\\",
                    state="Ready",
                    actions=[TaskAction(execute="C:\\Opera\\assistant\\opera_assistant.exe", arguments="--run")]
                )
            ]
        )

        cause, confidence, evidence, fix = self.session._determine_launch_cause(
            process_name="opera_assistant",
            parent_name="svchost.exe",
            parent_cmd="",
            system_report=mock_report,
        )

        self.assertEqual(cause, "ScheduledTask")
        self.assertGreaterEqual(confidence, 0.90)
        self.assertTrue(any("scheduled task" in e.lower() for e in evidence))
        self.assertIn("Disable scheduled task", fix)

    def test_determine_cause_service(self):
        """Verify that a relaunch matching a Windows service is correctly identified."""
        mock_report = DiagnosticReport(
            services_overview=[
                ServiceFinding(
                    name="TestSvc",
                    display_name="Test Background Service",
                    binary_path="C:\\Apps\\testsrv.exe",
                )
            ]
        )

        cause, confidence, evidence, fix = self.session._determine_launch_cause(
            process_name="testsrv",
            parent_name="services.exe",
            parent_cmd="",
            system_report=mock_report,
        )

        self.assertEqual(cause, "WindowsService")
        self.assertGreaterEqual(confidence, 0.80)
        self.assertIn("Manual", fix)

    def test_session_bounds(self):
        """Verify that session duration is safely bounded between 5s and 120s."""
        s_low = RelaunchDiagnosticSession(duration_seconds=1)
        self.assertEqual(s_low.duration_seconds, 5)

        s_high = RelaunchDiagnosticSession(duration_seconds=300)
        self.assertEqual(s_high.duration_seconds, 120)


if __name__ == "__main__":
    unittest.main()
