"""
WinOptimize AI - Main Window
Integrated multi-view interface with sidebar navigation, theme manager, and worker threads.
"""

from __future__ import annotations
import logging
from typing import List, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QMessageBox, QStatusBar
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon

from .styles import THEMES, DARK_THEME
from .views.dashboard_view import DashboardView
from .views.scan_results_view import ScanResultsView
from .views.recommendations_view import RecommendationsView
from .views.optimization_view import OptimizationView
from .views.history_view import HistoryView
from .views.settings_view import SettingsView

from .workers import (
    ScanWorker,
    OptimizeWorker,
    RollbackWorker,
    RelaunchWorker,
    CheckUpdateWorker,
    ApplyUpdateWorker,
)
from scanner.models import DiagnosticReport
from analyzer.process_analyzer import OptimizationRecommendation
from optimizer.optimization_coordinator import OptimizationResult
from storage.database import DatabaseManager

logger = logging.getLogger("WinOp.UI")


class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self, auto_scan: bool = True):
        super().__init__()
        self.setWindowTitle("WinOptimize AI — Intelligent Background Process Optimizer")
        self.resize(1100, 720)
        self.setMinimumSize(950, 600)

        self.db = DatabaseManager()
        self.latest_report: Optional[DiagnosticReport] = None
        self.latest_recs: List[OptimizationRecommendation] = []

        # Active worker references to prevent garbage collection
        self._scan_worker: Optional[ScanWorker] = None
        self._optimize_worker: Optional[OptimizeWorker] = None
        self._rollback_worker: Optional[RollbackWorker] = None
        self._relaunch_worker: Optional[RelaunchWorker] = None
        self._update_check_worker: Optional[CheckUpdateWorker] = None
        self._update_apply_worker: Optional[ApplyUpdateWorker] = None

        self._init_ui()

        # Load persisted theme preference
        saved_theme = self.db.get_user_preference("AppSetting:Theme") or "dark"
        self.apply_theme(saved_theme)

        # Set dropdown to match saved theme
        if saved_theme in SettingsView.THEME_KEYS:
            idx = SettingsView.THEME_KEYS.index(saved_theme)
            self.settings_view.theme_combo.setCurrentIndex(idx)

        # Automatically initiate initial read-only baseline scan on startup if enabled
        if auto_scan:
            self.start_scan()

        # Non-blocking background check for app updates
        self._silent_check_update()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar Navigation Frame
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 16, 12, 16)
        side_layout.setSpacing(4)

        # App Brand
        app_title = QLabel("WinOptimize AI")
        app_title.setObjectName("AppTitle")
        app_sub = QLabel("Process & Startup Optimizer")
        app_sub.setObjectName("AppSubtitle")
        side_layout.addWidget(app_title)
        side_layout.addWidget(app_sub)

        # Navigation Buttons
        self.nav_btns = []
        self.btn_dash = self._create_nav_button("  Dashboard", 0)
        self.btn_findings = self._create_nav_button("  Findings", 1)
        self.btn_recs = self._create_nav_button("  Recommendations", 2)
        self.btn_opt = self._create_nav_button("  Optimization", 3)
        self.btn_hist = self._create_nav_button("  History && Restore", 4)
        self.btn_set = self._create_nav_button("  Settings && Observer", 5)

        for btn in [self.btn_dash, self.btn_findings, self.btn_recs, self.btn_opt, self.btn_hist, self.btn_set]:
            side_layout.addWidget(btn)
            self.nav_btns.append(btn)

        side_layout.addStretch()

        # In-App Update shortcut button in sidebar
        self.sidebar_update_btn = QPushButton("🔄 Check for Updates")
        self.sidebar_update_btn.setProperty("class", "SecondaryButton")
        self.sidebar_update_btn.setCursor(Qt.PointingHandCursor)
        self.sidebar_update_btn.setStyleSheet("font-size: 11px; padding: 6px; margin: 4px 4px;")
        self.sidebar_update_btn.clicked.connect(self._on_sidebar_update_clicked)
        side_layout.addWidget(self.sidebar_update_btn)

        # Offline / Privacy Badge
        priv_badge = QLabel("• 100% Offline & Private")
        priv_badge.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 600; padding: 8px;")
        side_layout.addWidget(priv_badge)

        main_layout.addWidget(sidebar)

        # 2. Content Stack
        self.stack = QStackedWidget()

        self.dash_view = DashboardView()
        self.dash_view.scan_requested.connect(self.start_scan)

        self.findings_view = ScanResultsView()

        self.recs_view = RecommendationsView()
        self.recs_view.proceed_to_optimize.connect(self._on_proceed_to_optimize)

        self.opt_view = OptimizationView()
        self.opt_view.start_optimization.connect(self._on_execute_optimization)
        self.opt_view.view_history_requested.connect(lambda: self.switch_page(4))

        self.hist_view = HistoryView(db_manager=self.db)
        self.hist_view.rollback_snapshot_requested.connect(self._on_rollback_snapshot)

        self.settings_view = SettingsView()
        self.settings_view.theme_changed.connect(self.apply_theme)
        self.settings_view.start_relaunch_session.connect(self._on_start_relaunch)
        self.settings_view.check_update_requested.connect(self._on_check_update)
        self.settings_view.apply_update_requested.connect(self._on_apply_update)

        self.stack.addWidget(self.dash_view)      # 0
        self.stack.addWidget(self.findings_view)  # 1
        self.stack.addWidget(self.recs_view)      # 2
        self.stack.addWidget(self.opt_view)       # 3
        self.stack.addWidget(self.hist_view)      # 4
        self.stack.addWidget(self.settings_view)  # 5

        main_layout.addWidget(self.stack)

        # 3. Status Bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready. Strict Read-Only Mode.")

        self.btn_dash.setChecked(True)

    def _create_nav_button(self, text: str, page_index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("class", "NavButton")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.switch_page(page_index))
        return btn

    def switch_page(self, page_index: int):
        self.stack.setCurrentIndex(page_index)
        for i, b in enumerate(self.nav_btns):
            b.setChecked(i == page_index)

        if page_index == 4:
            self.hist_view.reload_history()

    def apply_theme(self, theme_name: str):
        theme_qss = THEMES.get(theme_name.lower(), DARK_THEME)
        self.setStyleSheet(theme_qss)
        try:
            self.db.set_user_preference("AppSetting:Theme", "Theme", theme_name.lower())
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Scan Flow
    # -------------------------------------------------------------------------
    def start_scan(self):
        self.statusBar.showMessage("Scanning system processes, startup registry, tasks, and services...")
        self.dash_view.scan_btn.setEnabled(False)
        self.dash_view.scan_btn.setText("Scanning System...")

        self._scan_worker = ScanWorker(use_powershell=True)
        self._scan_worker.scan_finished.connect(self._on_scan_finished)
        self._scan_worker.scan_failed.connect(self._on_scan_failed)
        self._scan_worker.start()

    def _on_scan_finished(self, report: DiagnosticReport, recommendations: List[OptimizationRecommendation]):
        self.latest_report = report
        self.latest_recs = recommendations

        self.dash_view.scan_btn.setEnabled(True)
        self.dash_view.scan_btn.setText("Scan System")
        self.dash_view.update_metrics(report, len(recommendations))

        self.findings_view.populate(report)
        self.recs_view.populate(recommendations)

        # Record scan to SQLite
        self.db.record_scan(
            used_memory_mb=report.system.used_physical_memory_mb,
            total_memory_mb=report.system.total_physical_memory_mb,
            cpu_percent=report.system.cpu_load_percent,
            proc_count=report.processes_count,
            startup_count=report.startup_entries_count,
            task_count=report.scheduled_tasks_count,
            service_count=report.services_count,
            candidates_count=len(recommendations),
        )

        self.statusBar.showMessage(
            f"Scan completed in {report.scan_duration_sec}s. Discovered {len(recommendations)} safe recommendations."
        )

    def _on_scan_failed(self, error_msg: str):
        self.dash_view.scan_btn.setEnabled(True)
        self.dash_view.scan_btn.setText("Scan System")
        self.statusBar.showMessage(f"Scan failed: {error_msg}")
        QMessageBox.warning(self, "Scan Error", f"Diagnostic scan encountered an error:\n{error_msg}")

    # -------------------------------------------------------------------------
    # Optimization Flow
    # -------------------------------------------------------------------------
    def _on_proceed_to_optimize(self, approved_recs: List[OptimizationRecommendation]):
        self.opt_view.set_approved_recommendations(approved_recs)
        self.switch_page(3)

    def _on_execute_optimization(self, recs: List[OptimizationRecommendation]):
        self.statusBar.showMessage("Executing optimizations: capturing backup snapshots & verifying...")
        self._optimize_worker = OptimizeWorker(recs)
        self._optimize_worker.optimize_finished.connect(self._on_optimize_finished)
        self._optimize_worker.optimize_failed.connect(self._on_optimize_failed)
        self._optimize_worker.start()

    def _on_optimize_finished(self, session_id: str, results: List[OptimizationResult]):
        self.opt_view.display_results(session_id, results)
        self.hist_view.reload_history()
        self.statusBar.showMessage(f"Optimization session {session_id} finished and verified.")

    def _on_optimize_failed(self, error_msg: str):
        self.statusBar.showMessage(f"Optimization failed: {error_msg}")
        QMessageBox.critical(self, "Optimization Error", f"Optimization pipeline failed:\n{error_msg}")

    # -------------------------------------------------------------------------
    # Rollback Flow
    # -------------------------------------------------------------------------
    def _on_rollback_snapshot(self, snapshot_id: str):
        self.statusBar.showMessage(f"Restoring snapshot {snapshot_id}...")
        self._rollback_worker = RollbackWorker(snapshot_id=snapshot_id)
        self._rollback_worker.rollback_finished.connect(self._on_rollback_finished)
        self._rollback_worker.rollback_failed.connect(self._on_rollback_failed)
        self._rollback_worker.start()

    def _on_rollback_finished(self, success: bool, message: str):
        self.hist_view.reload_history()
        self.statusBar.showMessage(message)
        if success:
            QMessageBox.information(self, "Rollback Restored", message)
        else:
            QMessageBox.warning(self, "Rollback Incomplete", message)

    def _on_rollback_failed(self, error_msg: str):
        self.statusBar.showMessage(f"Rollback error: {error_msg}")
        QMessageBox.critical(self, "Rollback Error", f"Failed to restore configuration:\n{error_msg}")

    # -------------------------------------------------------------------------
    # Relaunch Observer Flow
    # -------------------------------------------------------------------------
    def _on_start_relaunch(self, targets: List[str], duration: int):
        self.statusBar.showMessage(f"Observing process relaunch behavior ({duration}s)...")
        self._relaunch_worker = RelaunchWorker(targets=targets, duration_seconds=duration)
        self._relaunch_worker.relaunch_finished.connect(self._on_relaunch_finished)
        self._relaunch_worker.relaunch_failed.connect(self._on_relaunch_failed)
        self._relaunch_worker.start()

    def _on_relaunch_finished(self, report):
        self.settings_view.display_relaunch_report(report)
        self.statusBar.showMessage(f"Relaunch observation completed: {report.summary}")

    def _on_relaunch_failed(self, error_msg: str):
        self.statusBar.showMessage(f"Relaunch observer failed: {error_msg}")
        QMessageBox.warning(self, "Relaunch Observer Error", f"Observer session failed:\n{error_msg}")

    # -------------------------------------------------------------------------
    # In-App Updater Flow
    # -------------------------------------------------------------------------
    def _silent_check_update(self):
        """Checks for updates silently without popping dialogs or setting status bar."""
        self._update_check_worker = CheckUpdateWorker()
        self._update_check_worker.check_finished.connect(self._on_silent_update_check_finished)
        self._update_check_worker.start()

    def _on_silent_update_check_finished(self, release_info):
        if release_info and release_info.is_newer:
            self.statusBar.showMessage(f"🎉 New version available: {release_info.tag_name} (See Settings)")
            self.sidebar_update_btn.setText(f"🎉 Update {release_info.tag_name}")
            self.sidebar_update_btn.setStyleSheet(
                "font-size: 11px; font-weight: 700; padding: 6px; margin: 4px 4px; "
                "background-color: #059669; color: #FFFFFF; border-radius: 6px; border: none;"
            )
            self.settings_view.display_update_info(release_info)

    def _on_sidebar_update_clicked(self):
        self.switch_page(5)  # Switch to Settings page
        self._on_check_update()

    def _on_check_update(self):
        self.statusBar.showMessage("Checking GitHub Releases for updates...")
        self._update_check_worker = CheckUpdateWorker()
        self._update_check_worker.check_finished.connect(self._on_update_check_finished)
        self._update_check_worker.check_failed.connect(self._on_update_check_failed)
        self._update_check_worker.start()

    def _on_update_check_finished(self, release_info):
        self.settings_view.display_update_info(release_info)
        if release_info and release_info.is_newer:
            self.statusBar.showMessage(f"Update available: {release_info.tag_name}")
            self.sidebar_update_btn.setText(f"🎉 Update {release_info.tag_name}")
            self.sidebar_update_btn.setStyleSheet(
                "font-size: 11px; font-weight: 700; padding: 6px; margin: 4px 4px; "
                "background-color: #059669; color: #FFFFFF; border-radius: 6px; border: none;"
            )
        else:
            self.statusBar.showMessage("WinOptimize AI is up to date.")
            self.sidebar_update_btn.setText("✓ App Up to Date")
            self.sidebar_update_btn.setStyleSheet("font-size: 11px; padding: 6px; margin: 4px 4px;")

    def _on_update_check_failed(self, error_msg: str):
        self.settings_view.display_update_info(None)
        self.statusBar.showMessage(f"Update check failed: {error_msg}")

    def _on_apply_update(self, download_url: str):
        self.statusBar.showMessage("Downloading update from GitHub...")
        self._update_apply_worker = ApplyUpdateWorker(download_url)
        self._update_apply_worker.progress.connect(self.settings_view.set_update_progress)
        self._update_apply_worker.update_finished.connect(self._on_update_apply_finished)
        self._update_apply_worker.start()

    def _on_update_apply_finished(self, success: bool, message: str):
        self.settings_view.on_update_completed(success, message)
        if success:
            self.statusBar.showMessage("Update applied. Restarting application...")
        else:
            self.statusBar.showMessage(f"Update error: {message}")
