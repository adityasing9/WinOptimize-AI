"""
WinOptimize AI - Snapshot Manager
Captures and records pre-modification snapshots into local SQLite database.
"""

from __future__ import annotations
import uuid
import logging
from typing import Dict, Any, Optional

from storage.database import DatabaseManager
from optimizer.modifiers import BaseModifier

logger = logging.getLogger("WinOp.Backup")


class SnapshotManager:
    """
    Captures complete system configuration snapshots prior to any modification.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager if db_manager is not None else DatabaseManager()

    def capture_and_store_snapshot(
        self,
        session_id: str,
        component_name: str,
        target_type: str,
        target_identifier: str,
        modifier: BaseModifier,
        params: Dict[str, Any],
        proposed_state: Dict[str, Any],
    ) -> str:
        """
        Captures pre-change state via the modifier and writes snapshot record to SQLite.
        Returns snapshot_id.
        """
        snapshot_id = f"SNAP-{uuid.uuid4().hex[:10].upper()}"
        original_state = modifier.capture_current_state(target_identifier, params)

        self.db.record_backup_snapshot(
            snapshot_id=snapshot_id,
            session_id=session_id,
            component_name=component_name,
            target_type=target_type,
            target_identifier=target_identifier,
            original_state=original_state,
            target_state=proposed_state,
            status="pending",
        )
        logger.info("Captured snapshot %s for %s (%s)", snapshot_id, component_name, target_type)
        return snapshot_id
