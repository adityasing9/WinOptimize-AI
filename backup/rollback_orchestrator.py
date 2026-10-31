"""
WinOptimize AI - Rollback Orchestrator
Restores system configuration to exact original state using backup snapshots.
"""

from __future__ import annotations
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from storage.database import DatabaseManager
from optimizer.modifiers import (
    BaseModifier,
    StartupRegistryModifier,
    ScheduledTaskModifier,
    ServiceModifier,
)

logger = logging.getLogger("WinOp.Rollback")


class RollbackOrchestrator:
    """
    Executes atomic rollbacks of previous optimization changes.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager if db_manager is not None else DatabaseManager()
        self.modifiers: Dict[str, BaseModifier] = {
            "registry_startup": StartupRegistryModifier(),
            "scheduled_task": ScheduledTaskModifier(),
            "service": ServiceModifier(),
        }

    def rollback_snapshot(self, snapshot_id: str) -> Tuple[bool, str]:
        """
        Rolls back a single modification snapshot.
        Returns (success: bool, message: str).
        """
        snapshots = self.db.get_all_snapshots(limit=1000)
        target_snap = next((s for s in snapshots if s["snapshot_id"] == snapshot_id), None)
        if not target_snap:
            return False, f"Snapshot '{snapshot_id}' not found."

        if target_snap["status"] == "reverted":
            return True, f"Snapshot '{snapshot_id}' is already reverted."

        target_type = target_snap["target_type"]
        modifier = self.modifiers.get(target_type)
        if not modifier:
            return False, f"No modifier available for target type '{target_type}'."

        orig_state = json.loads(target_snap["original_state_json"])
        target_id = target_snap["target_identifier"]

        try:
            success = modifier.revert_modification(target_id, orig_state)
            if success:
                self.db.update_snapshot_status(snapshot_id, "reverted")
                return True, f"Successfully rolled back '{target_snap['component_name']}'."
            else:
                return False, f"Modifier failed to revert '{target_snap['component_name']}'."
        except Exception as e:
            logger.error("Error during rollback of %s: %s", snapshot_id, e)
            return False, f"Rollback failed with error: {str(e)}"

    def rollback_session(self, session_id: str) -> Tuple[int, int, List[str]]:
        """
        Rolls back all snapshots associated with an optimization session.
        Returns (success_count, fail_count, messages).
        """
        snapshots = self.db.get_snapshots_for_session(session_id)
        if not snapshots:
            return 0, 0, [f"No snapshots found for session '{session_id}'."]

        success_count = 0
        fail_count = 0
        messages = []

        # Revert in reverse order of application
        for snap in reversed(snapshots):
            ok, msg = self.rollback_snapshot(snap["snapshot_id"])
            if ok:
                success_count += 1
            else:
                fail_count += 1
            messages.append(msg)

        if fail_count == 0:
            self.db.update_session_status(session_id, "rolled_back")
        else:
            self.db.update_session_status(session_id, "partial_rollback")

        return success_count, fail_count, messages
