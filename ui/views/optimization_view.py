"""
WinOptimize AI - Optimization View
Precondition validation, atomic execution, backup status, and real-time verification report.
"""

from __future__ import annotations
from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QFrame
)
from PySide6.QtCore import Qt, Signal

from analyzer.process_analyzer import OptimizationRecommendation
from optimizer.optimization_coordinator import OptimizationResult


class OptimizationView(QWidget):
    """View executing approved optimizations with live verification reporting."""
    start_optimization = Signal(list)  # (List[OptimizationRecommendation])
    view_history_requested = Signal()
    relaunch_admin_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.approved_recs: List[OptimizationRecommendation] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        top_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Optimization Execution & Verification")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #60A5FA;")
        self.status_sub = QLabel("Review approved changes before applying.")
        self.status_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(title)
        title_box.addWidget(self.status_sub)
        top_layout.addLayout(title_box)

        top_layout.addStretch()

        import ctypes
        is_admin = False
        try:
            is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            pass

        if not is_admin:
            self.elev_btn = QPushButton("🛡️ Relaunch as Admin")
            self.elev_btn.setProperty("class", "SecondaryButton")
            self.elev_btn.setToolTip("Relaunch WinOptimize AI as Administrator to apply scheduled tasks and services without permission issues.")
            self.elev_btn.clicked.connect(self.relaunch_admin_requested.emit)
            top_layout.addWidget(self.elev_btn)

        self.apply_btn = QPushButton("Apply Optimizations Now")
        self.apply_btn.setProperty("class", "PrimaryButton")
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        top_layout.addWidget(self.apply_btn)

        layout.addLayout(top_layout)

        # Precondition / Safety Guarantee Notice
        notice_frame = QFrame()
        notice_frame.setProperty("class", "Card")
        n_l = QVBoxLayout(notice_frame)
        n_l.setContentsMargins(12, 10, 12, 10)
        n_lbl = QLabel(
            "<b>Automatic Safety Guarantee:</b> A complete backup snapshot of every item will be captured "
            "into local storage before any modification occurs. The optimizer will verify each setting immediately after "
            "applying. If any verification fails, the change is automatically rolled back instantly."
        )
        n_lbl.setWordWrap(True)
        n_lbl.setStyleSheet("font-size: 11px; color: #38BDF8;")
        n_l.addWidget(n_lbl)
        layout.addWidget(notice_frame)

        # Progress Bar
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setVisible(False)
        layout.addWidget(self.prog_bar)

        # Results Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["Component", "Action", "Snapshot ID", "Status", "Verification Details"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.verticalHeader().setVisible(False)
        layout.addWidget(self.results_table)

        # Bottom Bar
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.history_btn = QPushButton("View Change History && Restore")
        self.history_btn.setProperty("class", "SecondaryButton")
        self.history_btn.clicked.connect(self.view_history_requested.emit)
        bottom_layout.addWidget(self.history_btn)

        layout.addLayout(bottom_layout)

    def set_approved_recommendations(self, recs: List[OptimizationRecommendation]):
        self.approved_recs = recs
        self.status_sub.setText(f"{len(recs)} optimization(s) selected and ready to apply.")
        self.apply_btn.setEnabled(len(recs) > 0)
        self.apply_btn.setText(f"Apply {len(recs)} Optimization(s)")
        self.prog_bar.setVisible(False)

        # Populate queue in table
        self.results_table.setRowCount(len(recs))
        for row, rec in enumerate(recs):
            self.results_table.setItem(row, 0, QTableWidgetItem(rec.component_name))
            self.results_table.setItem(row, 1, QTableWidgetItem(rec.recommended_action))
            self.results_table.setItem(row, 2, QTableWidgetItem("Pending..."))
            self.results_table.setItem(row, 3, QTableWidgetItem("Awaiting User Confirmation"))
            self.results_table.setItem(row, 4, QTableWidgetItem("Preconditions passed"))

    def _on_apply_clicked(self):
        self.apply_btn.setEnabled(False)
        self.apply_btn.setText("Optimizing & Verifying...")
        self.prog_bar.setVisible(True)
        self.prog_bar.setRange(0, 0)  # Indeterminate
        self.status_sub.setText("Executing safe modification pipeline...")
        self.start_optimization.emit(self.approved_recs)

    def display_results(self, session_id: str, results: List[OptimizationResult]):
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(100)
        self.apply_btn.setText("Optimizations Completed")

        success_count = sum(1 for r in results if r.success and r.verified)
        self.status_sub.setText(
            f"Session {session_id} completed: {success_count}/{len(results)} actions verified successfully."
        )

        self.results_table.setRowCount(len(results))
        for row, res in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(res.component_name))
            self.results_table.setItem(row, 1, QTableWidgetItem(res.action_name or "Optimized"))
            self.results_table.setItem(row, 2, QTableWidgetItem(res.snapshot_id))

            status_str = "Verified & Applied" if (res.success and res.verified) else "Failed / Reverted"
            status_item = QTableWidgetItem(status_str)
            if res.success and res.verified:
                status_item.setForeground(Qt.green)
            else:
                status_item.setForeground(Qt.red)
            self.results_table.setItem(row, 3, status_item)

            self.results_table.setItem(row, 4, QTableWidgetItem(res.message))
