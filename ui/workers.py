"""
WinOptimize AI - Background QThread Workers
Ensures all system inspection, optimization, and rollback operations are 100% non-blocking.
"""

from __future__ import annotations
import logging
from typing import List, Optional
from PySide6.QtCore import QThread, Signal

from scanner.system_scanner import SystemScanner
from scanner.models import DiagnosticReport
from analyzer.process_analyzer import ProcessAnalyzer, OptimizationRecommendation
from optimizer.optimization_coordinator import OptimizationCoordinator, OptimizationResult
from backup.rollback_orchestrator import RollbackOrchestrator
from monitoring.relaunch_detector import RelaunchDiagnosticSession, RelaunchReport

logger = logging.getLogger("WinOp.Workers")


class ScanWorker(QThread):
    """Executes read-only system scan and analysis in background thread."""
    scan_finished = Signal(object, list)  # (DiagnosticReport, List[OptimizationRecommendation])
    scan_failed = Signal(str)

    def __init__(self, use_powershell: bool = True):
        super().__init__()
        self.use_powershell = use_powershell

    def run(self):
        try:
            scanner = SystemScanner()
            report = scanner.scan(use_powershell=self.use_powershell)

            analyzer = ProcessAnalyzer()
            recommendations = analyzer.analyze(report)

            self.scan_finished.emit(report, recommendations)
        except Exception as e:
            logger.error("Scan worker encountered exception: %s", e)
            self.scan_failed.emit(str(e))


class OptimizeWorker(QThread):
    """Executes safe optimizations with pre-backup and verification."""
    optimize_finished = Signal(str, list)  # (session_id, List[OptimizationResult])
    optimize_failed = Signal(str)

    def __init__(self, recommendations: List[OptimizationRecommendation]):
        super().__init__()
        self.recommendations = recommendations

    def run(self):
        try:
            coordinator = OptimizationCoordinator()
            session_id, results = coordinator.execute_session(self.recommendations, user_authorized=True)
            self.optimize_finished.emit(session_id, results)
        except Exception as e:
            logger.error("Optimize worker exception: %s", e)
            self.optimize_failed.emit(str(e))


class RollbackWorker(QThread):
    """Executes rollback for a specific snapshot or session."""
    rollback_finished = Signal(bool, str)
    rollback_failed = Signal(str)

    def __init__(self, snapshot_id: Optional[str] = None, session_id: Optional[str] = None):
        super().__init__()
        self.snapshot_id = snapshot_id
        self.session_id = session_id

    def run(self):
        try:
            orchestrator = RollbackOrchestrator()
            if self.snapshot_id:
                success, msg = orchestrator.rollback_snapshot(self.snapshot_id)
                self.rollback_finished.emit(success, msg)
            elif self.session_id:
                s_count, f_count, msgs = orchestrator.rollback_session(self.session_id)
                msg_str = f"Reverted {s_count} items." if f_count == 0 else f"Reverted {s_count}, failed {f_count}."
                self.rollback_finished.emit(f_count == 0, msg_str)
            else:
                self.rollback_failed.emit("Neither snapshot_id nor session_id was provided.")
        except Exception as e:
            logger.error("Rollback worker exception: %s", e)
            self.rollback_failed.emit(str(e))


class RelaunchWorker(QThread):
    """Executes diagnostic relaunch observation session."""
    relaunch_finished = Signal(object)  # RelaunchReport
    relaunch_failed = Signal(str)

    def __init__(self, targets: Optional[List[str]] = None, duration_seconds: int = 15):
        super().__init__()
        self.targets = targets
        self.duration_seconds = duration_seconds

    def run(self):
        try:
            session = RelaunchDiagnosticSession(target_names=self.targets, duration_seconds=self.duration_seconds)
            report = session.run_session()
            self.relaunch_finished.emit(report)
        except Exception as e:
            logger.error("Relaunch worker exception: %s", e)
            self.relaunch_failed.emit(str(e))


class CheckUpdateWorker(QThread):
    """Checks for latest releases on GitHub in background."""
    check_finished = Signal(object)  # ReleaseInfo or None
    check_failed = Signal(str)

    def run(self):
        try:
            from updater.in_app_updater import InAppUpdater
            updater = InAppUpdater()
            info = updater.check_for_updates()
            self.check_finished.emit(info)
        except Exception as e:
            logger.error("Check update worker error: %s", e)
            self.check_failed.emit(str(e))


class ApplyUpdateWorker(QThread):
    """Downloads update and applies in-place restart."""
    progress = Signal(int)
    update_finished = Signal(bool, str)

    def __init__(self, download_url: str):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            from updater.in_app_updater import InAppUpdater
            updater = InAppUpdater()
            ok = updater.download_and_apply_update(
                self.download_url,
                progress_callback=lambda pct: self.progress.emit(pct),
            )
            if ok:
                self.update_finished.emit(True, "Update downloaded successfully!")
            else:
                self.update_finished.emit(False, "Update download failed.")
        except Exception as e:
            logger.error("Apply update error: %s", e)
            self.update_finished.emit(False, str(e))
