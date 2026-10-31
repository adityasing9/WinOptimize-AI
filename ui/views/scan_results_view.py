"""
WinOptimize AI - Scan Results View
Tabular inspection view for Startup entries, Scheduled Tasks, Services, and Processes.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt

from scanner.models import DiagnosticReport


class ScanResultsView(QWidget):
    """Organized, searchable inspection tables."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header & Filter
        top_layout = QHBoxLayout()
        header = QLabel("System Findings & Discovered Components")
        header.setStyleSheet("font-size: 20px; font-weight: 700; color: #60A5FA;")
        top_layout.addWidget(header)
        top_layout.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter findings by keyword...")
        self.search_box.setMinimumWidth(260)
        self.search_box.textChanged.connect(self._filter_tables)
        top_layout.addWidget(self.search_box)

        layout.addLayout(top_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.startup_table = self._create_table(["Name", "Scope", "Location", "Publisher", "Status", "Command"])
        self.task_table = self._create_table(["Task Name", "Path", "State", "Triggers", "Action Executable"])
        self.service_table = self._create_table(["Display Name", "Service Name", "Status", "Start Mode", "Account"])
        self.process_table = self._create_table(["Process Name", "PID", "Memory (MB)", "Has Window", "Window Title"])

        self.tabs.addTab(self.startup_table, "Startup Applications")
        self.tabs.addTab(self.task_table, "Scheduled Tasks")
        self.tabs.addTab(self.service_table, "Windows Services")
        self.tabs.addTab(self.process_table, "Running Processes")

        layout.addWidget(self.tabs)

    def _create_table(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        return table

    def populate(self, report: DiagnosticReport):
        """Populates all tables with scanned system telemetry."""
        # 1. Startup
        self.startup_table.setRowCount(len(report.startup_entries))
        for row, s in enumerate(report.startup_entries):
            status_text = "Enabled" if s.is_enabled else "Disabled"
            self.startup_table.setItem(row, 0, QTableWidgetItem(s.name))
            self.startup_table.setItem(row, 1, QTableWidgetItem(s.scope))
            self.startup_table.setItem(row, 2, QTableWidgetItem(s.location_type))
            self.startup_table.setItem(row, 3, QTableWidgetItem(s.publisher or "Unknown"))
            self.startup_table.setItem(row, 4, QTableWidgetItem(status_text))
            self.startup_table.setItem(row, 5, QTableWidgetItem(s.command))

        # 2. Tasks
        self.task_table.setRowCount(len(report.scheduled_tasks))
        for row, t in enumerate(report.scheduled_tasks):
            act_str = "; ".join(a.execute for a in t.actions)
            trig_str = f"{len(t.triggers)} trigger(s)"
            self.task_table.setItem(row, 0, QTableWidgetItem(t.task_name))
            self.task_table.setItem(row, 1, QTableWidgetItem(t.task_path))
            self.task_table.setItem(row, 2, QTableWidgetItem(t.state))
            self.task_table.setItem(row, 3, QTableWidgetItem(trig_str))
            self.task_table.setItem(row, 4, QTableWidgetItem(act_str))

        # 3. Services
        self.service_table.setRowCount(len(report.services_overview))
        for row, svc in enumerate(report.services_overview):
            self.service_table.setItem(row, 0, QTableWidgetItem(svc.display_name or svc.name))
            self.service_table.setItem(row, 1, QTableWidgetItem(svc.name))
            self.service_table.setItem(row, 2, QTableWidgetItem(svc.status))
            self.service_table.setItem(row, 3, QTableWidgetItem(svc.start_mode))
            self.service_table.setItem(row, 4, QTableWidgetItem(svc.account or "System"))

        # 4. Processes
        self.process_table.setRowCount(len(report.top_processes))
        for row, p in enumerate(report.top_processes):
            self.process_table.setItem(row, 0, QTableWidgetItem(p.name))
            self.process_table.setItem(row, 1, QTableWidgetItem(str(p.pid)))
            self.process_table.setItem(row, 2, QTableWidgetItem(f"{p.working_set_mb:.1f}"))
            self.process_table.setItem(row, 3, QTableWidgetItem("Yes" if p.has_window else "No"))
            self.process_table.setItem(row, 4, QTableWidgetItem(p.window_title))

    def _filter_tables(self, text: str):
        search = text.lower().strip()
        current_table: QTableWidget = self.tabs.currentWidget()
        if not current_table:
            return

        for r in range(current_table.rowCount()):
            match = False
            for c in range(current_table.columnCount()):
                item = current_table.item(r, c)
                if item and search in item.text().lower():
                    match = True
                    break
            current_table.setRowHidden(r, not match)
