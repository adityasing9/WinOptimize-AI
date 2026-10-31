"""
Unit Tests for WinOptimize AI Safe Optimizer and Rollback Engine (Phase 4)
Tests atomic modification, backup snapshotting, verification, and rollback.
"""

import json
import os
import tempfile
import unittest
import winreg
from pathlib import Path

from storage.database import DatabaseManager
from optimizer.modifiers import StartupRegistryModifier
from backup.snapshot_manager import SnapshotManager
from backup.rollback_orchestrator import RollbackOrchestrator
from optimizer.optimization_coordinator import OptimizationCoordinator, OptimizationResult
from analyzer.process_analyzer import OptimizationRecommendation
from rules.rule_definitions import RuleRiskLevel


class TestSafeOptimizerAndRollback(unittest.TestCase):
    def setUp(self):
        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp_db.close()
        self.db = DatabaseManager(db_path=self.tmp_db.name)
        self.coordinator = OptimizationCoordinator(db_manager=self.db)
        self.modifier = StartupRegistryModifier()

        # Set up a test key in HKCU for testing without touching real software
        self.test_entry_name = "WinOp_Test_App_Unit_Test"
        self.test_subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
        # Ensure clean state
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.test_subkey, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, self.test_entry_name)
        except (FileNotFoundError, OSError):
            pass

    def tearDown(self):
        # Cleanup test registry entry
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.test_subkey, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, self.test_entry_name)
        except (FileNotFoundError, OSError):
            pass

        if os.path.exists(self.tmp_db.name):
            try:
                os.remove(self.tmp_db.name)
            except OSError:
                pass

    def test_startup_modifier_disable_and_revert(self):
        """Verify that disabling sets 0x03, verification succeeds, and revert restores 0x02."""
        # 1. Initially set to 0x02 enabled
        enabled_bytes = bytes([0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.test_subkey) as k:
            winreg.SetValueEx(k, self.test_entry_name, 0, winreg.REG_BINARY, enabled_bytes)

        # 2. Capture state
        initial_state = self.modifier.capture_current_state(
            f"Startup:{self.test_entry_name}",
            {"name": self.test_entry_name, "scope": "User"}
        )
        self.assertTrue(initial_state["is_enabled"])
        self.assertEqual(initial_state["raw_bytes_hex"], enabled_bytes.hex())

        # 3. Apply disable modification
        ok = self.modifier.apply_modification(
            f"Startup:{self.test_entry_name}",
            {"name": self.test_entry_name, "scope": "User"}
        )
        self.assertTrue(ok)

        # 4. Verify state is disabled
        verified = self.modifier.verify_state(
            f"Startup:{self.test_entry_name}",
            {"name": self.test_entry_name, "is_enabled": False, "scope": "User"}
        )
        self.assertTrue(verified)

        # 5. Revert back to original enabled state
        reverted = self.modifier.revert_modification(
            f"Startup:{self.test_entry_name}",
            initial_state
        )
        self.assertTrue(reverted)

        # 6. Verify restored state is enabled
        restored = self.modifier.verify_state(
            f"Startup:{self.test_entry_name}",
            {"name": self.test_entry_name, "is_enabled": True, "scope": "User"}
        )
        self.assertTrue(restored)

    def test_coordinator_blocks_protected_components(self):
        """Verify that OptimizationCoordinator refuses to modify protected items even if marked approved."""
        rec = OptimizationRecommendation(
            recommendation_id="REC-TEST-PROT",
            category="StartupEntry",
            component_name="SecurityHealth",
            target_identifier="Startup:SecurityHealth",
            risk_level=RuleRiskLevel.PROTECTED,
            confidence=1.0,
            title="Protected Component",
            description="Defender Systray",
            recommended_action="Do not modify",
            side_effects="Instability",
            reversibility_info="N/A",
            requires_elevation=True,
            is_protected=True,
            is_approved=True,  # Even if marked approved
        )

        session_id, results = self.coordinator.execute_session([rec])
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
        self.assertIn("Protected", results[0].message)

    def test_coordinator_atomic_flow_and_rollback(self):
        """Verify end-to-end execution, backup recording, and session rollback."""
        # Setup initial enabled test entry
        enabled_bytes = bytes([0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.test_subkey) as k:
            winreg.SetValueEx(k, self.test_entry_name, 0, winreg.REG_BINARY, enabled_bytes)

        rec = OptimizationRecommendation(
            recommendation_id="REC-TEST-FLOW",
            category="StartupEntry",
            component_name=self.test_entry_name,
            target_identifier=f"Startup:{self.test_entry_name}",
            risk_level=RuleRiskLevel.LOW,
            confidence=0.95,
            title="Test App",
            description="Test startup",
            recommended_action="Disable",
            side_effects="None",
            reversibility_info="Restore",
            requires_elevation=False,
            current_state={"name": self.test_entry_name, "scope": "User", "is_enabled": True},
            proposed_state={"name": self.test_entry_name, "scope": "User", "is_enabled": False},
            is_approved=True,
        )

        session_id, results = self.coordinator.execute_session([rec])
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)
        self.assertTrue(results[0].verified)
        snapshot_id = results[0].snapshot_id
        self.assertTrue(snapshot_id.startswith("SNAP-"))

        # Check that DB snapshot exists and is verified
        snapshots = self.db.get_snapshots_for_session(session_id)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["status"], "verified")

        # Now execute rollback
        rollback_orch = RollbackOrchestrator(db_manager=self.db)
        ok, msg = rollback_orch.rollback_snapshot(snapshot_id)
        self.assertTrue(ok)

        # Check DB status updated to 'reverted'
        updated_snaps = self.db.get_snapshots_for_session(session_id)
        self.assertEqual(updated_snaps[0]["status"], "reverted")


if __name__ == "__main__":
    unittest.main()
