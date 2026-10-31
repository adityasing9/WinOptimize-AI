"""
WinOptimize AI - History and Rollback View
Displays chronological modification history from SQLite and provides 1-click restore.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from storage.database import DatabaseManager


class HistoryView(QWidget):
    """Change history and one-click recovery view."""
    rollback_snapshot_requested = Signal(str)  # snapshot_id
    rollback_session_requested = Signal(str)   # session_id

    def __init__(self, db_manager: Optional[DatabaseManager] = None, parent=None):
        super().__init__(parent)
        self.db = db_manager if db_manager is not None else DatabaseManager()
        self.snapshots: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        top_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Modification History & 1-Click Rollback")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #60A5FA;")
        sub = QLabel("Every modification is fully reversible. Restore any individual setting or previous session.")
        sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        top_layout.addLayout(title_box)

        top_layout.addStretch()

        self.refresh_btn = QPushButton("Refresh History")
        self.refresh_btn.setProperty("class", "SecondaryButton")
        self.refresh_btn.clicked.connect(self.reload_history)
        top_layout.addWidget(self.refresh_btn)

        layout.addLayout(top_layout)

        # History Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Snapshot ID", "Applied At", "Component", "Target Type", "Status", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.reload_history()

    def reload_history(self):
        self.snapshots = self.db.get_all_snapshots(limit=100)
        self.table.setRowCount(len(self.snapshots))

        for row, snap in enumerate(self.snapshots):
            snap_id = snap["snapshot_id"]
            status = snap["status"]

            self.table.setItem(row, 0, QTableWidgetItem(snap_id))
            self.table.setItem(row, 1, QTableWidgetItem(snap["applied_at"][:19].replace("T", " ")))
            self.table.setItem(row, 2, QTableWidgetItem(snap["component_name"]))
            self.table.setItem(row, 3, QTableWidgetItem(snap["target_type"]))

            status_item = QTableWidgetItem(status.capitalize())
            if status == "verified" or status == "applied":
                status_item.setForeground(Qt.yellow)
            elif status == "reverted":
                status_item.setForeground(Qt.cyan)
            self.table.setItem(row, 4, status_item)

            # Restore Button
            if status != "reverted":
                restore_btn = QPushButton("Restore")
                restore_btn.setProperty("class", "SecondaryButton")
                restore_btn.setStyleSheet("padding: 4px 8px; font-size: 11px;")
                restore_btn.clicked.connect(lambda checked=False, sid=snap_id: self._on_restore_clicked(sid))
                self.table.setCellWidget(row, 5, restore_btn)
            else:
                restored_lbl = QLabel("Restored")
                restored_lbl.setAlignment(Qt.AlignCenter)
                restored_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
                self.table.setCellWidget(row, 5, restored_lbl)

    def _on_restore_clicked(self, snapshot_id: str):
        reply = QMessageBox.question(
            self,
            "Confirm Rollback",
            f"Are you sure you want to restore the original configuration for snapshot '{snapshot_id}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self.rollback_snapshot_requested.emit(snapshot_id)
