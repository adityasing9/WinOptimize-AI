"""
WinOptimize AI - Dashboard View
Displays overall system health, memory & CPU metrics, scan counts, and scan trigger.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QGridLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from scanner.models import DiagnosticReport


class DashboardView(QWidget):
    """Modern system overview dashboard."""
    scan_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # 1. Header Banner
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()

        welcome_lbl = QLabel("System Dashboard")
        welcome_lbl.setStyleSheet("font-size: 22px; font-weight: 700; color: #60A5FA;")
        subtitle_lbl = QLabel("Safe, non-destructive Windows background process analysis.")
        subtitle_lbl.setStyleSheet("font-size: 13px; color: #94A3B8;")

        title_box.addWidget(welcome_lbl)
        title_box.addWidget(subtitle_lbl)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        self.scan_btn = QPushButton("Scan System")
        self.scan_btn.setProperty("class", "PrimaryButton")
        self.scan_btn.setMinimumHeight(42)
        self.scan_btn.setMinimumWidth(160)
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self.scan_requested.emit)
        header_layout.addWidget(self.scan_btn)

        layout.addLayout(header_layout)

        # 2. Resource Metrics Cards Grid
        grid = QGridLayout()
        grid.setSpacing(16)

        # Memory Card
        self.mem_card = self._create_card("Memory Utilization", "0.0 GB / 0.0 GB (0%)")
        self.mem_bar = QProgressBar()
        self.mem_bar.setRange(0, 100)
        self.mem_bar.setValue(0)
        self.mem_card.layout().addWidget(self.mem_bar)
        grid.addWidget(self.mem_card, 0, 0)

        # CPU Card
        self.cpu_card = self._create_card("CPU Load", "0%")
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setValue(0)
        self.cpu_card.layout().addWidget(self.cpu_bar)
        grid.addWidget(self.cpu_card, 0, 1)

        # OS Details Card
        self.os_card = self._create_card("Operating System", "Windows 11")
        self.os_sub = QLabel("Build: Checking...")
        self.os_sub.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.os_card.layout().addWidget(self.os_sub)
        grid.addWidget(self.os_card, 0, 2)

        # Startup Card
        self.startup_card = self._create_card("Startup Applications", "0 Discovered")
        self.startup_sub = QLabel("0 Active at Boot")
        self.startup_sub.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.startup_card.layout().addWidget(self.startup_sub)
        grid.addWidget(self.startup_card, 1, 0)

        # Tasks & Services Card
        self.tasks_card = self._create_card("Background Tasks", "0 Scheduled Tasks")
        self.tasks_sub = QLabel("0 Services Evaluated")
        self.tasks_sub.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.tasks_card.layout().addWidget(self.tasks_sub)
        grid.addWidget(self.tasks_card, 1, 1)

        # Recommendations Card
        self.recs_card = self._create_card("Recommendations", "0 Available")
        self.recs_sub = QLabel("Run a scan to generate safe fixes")
        self.recs_sub.setStyleSheet("font-size: 11px; color: #34D399;")
        self.recs_card.layout().addWidget(self.recs_sub)
        grid.addWidget(self.recs_card, 1, 2)

        layout.addLayout(grid)

        # 3. Status Notice / Safety Policy Card
        notice_frame = QFrame()
        notice_frame.setProperty("class", "Card")
        notice_layout = QVBoxLayout(notice_frame)
        notice_title = QLabel("Safe Optimization Policy Guarantee")
        notice_title.setStyleSheet("font-weight: 700; color: #38BDF8; font-size: 13px;")
        notice_text = QLabel(
            "WinOptimize AI strictly enforces non-destructive operations. Protected Windows components "
            "(Defender, Firewall, Core Audio, Drivers, LSASS) are permanently locked. "
            "Startup entries are disabled natively without deleting keys, and all modifications capture "
            "complete backup snapshots prior to execution with instant one-click rollback."
        )
        notice_text.setWordWrap(True)
        notice_text.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 1.4;")
        notice_layout.addWidget(notice_title)
        notice_layout.addWidget(notice_text)

        layout.addWidget(notice_frame)
        layout.addStretch()

    def _create_card(self, title: str, initial_val: str) -> QFrame:
        frame = QFrame()
        frame.setProperty("class", "Card")
        l = QVBoxLayout(frame)
        l.setSpacing(4)
        l.setContentsMargins(14, 14, 14, 14)

        t_lbl = QLabel(title)
        t_lbl.setProperty("class", "CardTitle")
        v_lbl = QLabel(initial_val)
        v_lbl.setProperty("class", "CardValue")
        frame.val_lbl = v_lbl  # Store ref

        l.addWidget(t_lbl)
        l.addWidget(v_lbl)
        return frame

    def update_metrics(self, report: DiagnosticReport, recommendations_count: int = 0):
        """Updates dashboard display with freshly scanned metrics."""
        # Memory
        used_gb = report.system.used_physical_memory_mb / 1024.0
        total_gb = report.system.total_physical_memory_mb / 1024.0
        pct = int(report.system.memory_usage_percent)
        self.mem_card.val_lbl.setText(f"{used_gb:.1f} GB / {total_gb:.1f} GB ({pct}%)")
        self.mem_bar.setValue(pct)

        # CPU
        cpu_pct = int(report.system.cpu_load_percent)
        self.cpu_card.val_lbl.setText(f"{cpu_pct}%")
        self.cpu_bar.setValue(cpu_pct)

        # OS
        self.os_card.val_lbl.setText(report.system.caption)
        self.os_sub.setText(f"Build {report.system.build_number} ({report.system.architecture})")

        # Startup
        self.startup_card.val_lbl.setText(f"{report.startup_entries_count} Entries")
        self.startup_sub.setText(f"{report.active_startup_count} Active / Enabled")

        # Tasks & Services
        self.tasks_card.val_lbl.setText(f"{report.scheduled_tasks_count} Scheduled Tasks")
        self.tasks_sub.setText(f"{report.services_count} Services Evaluated")

        # Recommendations
        self.recs_card.val_lbl.setText(f"{recommendations_count} Optimization Suggestions")
        if recommendations_count > 0:
            self.recs_sub.setText("Ready for safe review and approval")
            self.recs_sub.setStyleSheet("font-size: 11px; color: #F59E0B;")
        else:
            self.recs_sub.setText("System is well-optimized; no redundant startups flagged")
            self.recs_sub.setStyleSheet("font-size: 11px; color: #34D399;")
