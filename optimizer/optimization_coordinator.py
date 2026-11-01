"""
WinOptimize AI - Optimization Coordinator
Orchestrates safe, authorized, and verified system optimizations with automatic rollback on failure.
"""

from __future__ import annotations
import uuid
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

from analyzer.process_analyzer import OptimizationRecommendation
from rules.rule_definitions import RuleRiskLevel
from storage.database import DatabaseManager
from backup.snapshot_manager import SnapshotManager
from backup.rollback_orchestrator import RollbackOrchestrator
from verification.state_verifier import StateVerifier
from .modifiers import (
    BaseModifier,
    StartupRegistryModifier,
    ScheduledTaskModifier,
    ServiceModifier,
    ProcessModifier,
)

logger = logging.getLogger("WinOp.Coordinator")


@dataclass
class OptimizationResult:
    recommendation_id: str
    component_name: str
    target_identifier: str
    action_name: str
    success: bool
    verified: bool
    snapshot_id: str
    message: str


class OptimizationCoordinator:
    """
    Coordinates safe, multi-step optimization sessions.
    Strictly enforces authorization, preconditions, backups, and verification.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager if db_manager is not None else DatabaseManager()
        self.snapshot_mgr = SnapshotManager(db_manager=self.db)
        self.rollback_orch = RollbackOrchestrator(db_manager=self.db)
        self.verifier = StateVerifier()
        self.modifiers: Dict[str, BaseModifier] = {
            "StartupEntry": StartupRegistryModifier(),
            "ScheduledTask": ScheduledTaskModifier(),
            "Service": ServiceModifier(),
            "BackgroundProcess": ProcessModifier(),
        }

    def execute_session(
        self,
        recommendations: List[OptimizationRecommendation],
        user_authorized: bool = True,
    ) -> Tuple[str, List[OptimizationResult]]:
        """
        Executes an optimization session on approved recommendations.
        Returns (session_id, list_of_results).
        """
        session_id = f"SESS-{uuid.uuid4().hex[:8].upper()}"
        approved_recs = [r for r in recommendations if r.is_approved]

        if not approved_recs:
            return session_id, []

        self.db.create_optimization_session(
            session_id=session_id,
            total_actions=len(approved_recs),
            user_authorized=user_authorized,
        )

        results: List[OptimizationResult] = []
        all_succeeded = True

        for rec in approved_recs:
            # Policy 1 & 6: Never modify protected components
            if rec.is_protected or rec.risk_level == RuleRiskLevel.PROTECTED:
                results.append(
                    OptimizationResult(
                        recommendation_id=rec.recommendation_id,
                        component_name=rec.component_name,
                        target_identifier=rec.target_identifier,
                        action_name=rec.recommended_action,
                        success=False,
                        verified=False,
                        snapshot_id="",
                        message="Hard-blocked: Protected Windows system component cannot be modified.",
                    )
                )
                continue

            modifier = self.modifiers.get(rec.category)
            if not modifier:
                results.append(
                    OptimizationResult(
                        recommendation_id=rec.recommendation_id,
                        component_name=rec.component_name,
                        target_identifier=rec.target_identifier,
                        action_name=rec.recommended_action,
                        success=False,
                        verified=False,
                        snapshot_id="",
                        message=f"No modifier registered for category '{rec.category}'.",
                    )
                )
                continue

            target_type_map = {
                "StartupEntry": "registry_startup",
                "ScheduledTask": "scheduled_task",
                "Service": "service",
                "BackgroundProcess": "background_process",
            }
            target_type = target_type_map.get(rec.category, "unknown")

            # 1. Capture Pre-Modification Backup Snapshot
            try:
                snapshot_id = self.snapshot_mgr.capture_and_store_snapshot(
                    session_id=session_id,
                    component_name=rec.component_name,
                    target_type=target_type,
                    target_identifier=rec.target_identifier,
                    modifier=modifier,
                    params=rec.current_state,
                    proposed_state=rec.proposed_state,
                )
            except Exception as e:
                logger.error("Failed to capture snapshot for %s: %s", rec.component_name, e)
                results.append(
                    OptimizationResult(
                        recommendation_id=rec.recommendation_id,
                        component_name=rec.component_name,
                        target_identifier=rec.target_identifier,
                        action_name=rec.recommended_action,
                        success=False,
                        verified=False,
                        snapshot_id="",
                        message=f"Aborted: Backup snapshot capture failed: {str(e)}",
                    )
                )
                all_succeeded = False
                continue

            # 2. Apply Safe Modification
            apply_success = False
            try:
                apply_success = modifier.apply_modification(rec.target_identifier, rec.proposed_state)
            except Exception as e:
                logger.error("Exception applying modification to %s: %s", rec.component_name, e)
                apply_success = False

            if not apply_success:
                all_succeeded = False
                self.db.update_snapshot_status(snapshot_id, "failed")
                results.append(
                    OptimizationResult(
                        recommendation_id=rec.recommendation_id,
                        component_name=rec.component_name,
                        target_identifier=rec.target_identifier,
                        action_name=rec.recommended_action,
                        success=False,
                        verified=False,
                        snapshot_id=snapshot_id,
                        message="Modification application failed (permission denied or target inaccessible).",
                    )
                )
                continue

            # 3. Verify State Post-Change
            verified = False
            try:
                verified = modifier.verify_state(rec.target_identifier, rec.proposed_state)
            except Exception as e:
                logger.warning("Verification threw exception for %s: %s", rec.component_name, e)
                verified = False

            if verified:
                self.db.update_snapshot_status(snapshot_id, "verified")
                results.append(
                    OptimizationResult(
                        recommendation_id=rec.recommendation_id,
                        component_name=rec.component_name,
                        target_identifier=rec.target_identifier,
                        action_name=rec.recommended_action,
                        success=True,
                        verified=True,
                        snapshot_id=snapshot_id,
                        message="Optimization successfully applied and verified.",
                    )
                )
            else:
                # Automatic recovery on verification failure!
                logger.warning("Verification failed for %s. Attempting automatic rollback.", rec.component_name)
                all_succeeded = False
                reverted, rev_msg = self.rollback_orch.rollback_snapshot(snapshot_id)
                results.append(
                    OptimizationResult(
                        recommendation_id=rec.recommendation_id,
                        component_name=rec.component_name,
                        target_identifier=rec.target_identifier,
                        action_name=rec.recommended_action,
                        success=False,
                        verified=False,
                        snapshot_id=snapshot_id,
                        message=f"Verification failed; automatic rollback executed: {rev_msg}",
                    )
                )

        final_status = "completed" if all_succeeded else "partial_failure"
        self.db.update_session_status(session_id, final_status)
        return session_id, results
