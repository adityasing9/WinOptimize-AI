"""
WinOptimize AI - Settings and Diagnostics View
Theme selection, Relaunch Diagnostic Observer, privacy policies, and storage controls.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QTextEdit, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from monitoring.relaunch_detector import RelaunchReport


class SettingsView(QWidget):
    """Configuration, theme preferences, and interactive relaunch diagnostics."""
    theme_changed = Signal(str)  # 'dark' or 'light'
    start_relaunch_session = Signal(list, int)  # (targets, duration)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        title = QLabel("Settings & Relaunch Diagnostics")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #60A5FA;")
        layout.addWidget(title)

        # 1. Appearance / Theme Card
        theme_card = QFrame()
        theme_card.setProperty("class", "Card")
        tl = QVBoxLayout(theme_card)
        tl_title = QLabel("Application Appearance")
        tl_title.setStyleSheet("font-weight: 600; font-size: 14px; color: #F8FAFC;")
        tl.addWidget(tl_title)

        theme_row = QHBoxLayout()
        theme_lbl = QLabel("Color Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark Theme (Fluent)", "Light Theme (Fluent)"])
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_row.addWidget(theme_lbl)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        tl.addLayout(theme_row)
        layout.addWidget(theme_card)

        # 2. Interactive Relaunch Diagnostics Tool
        relaunch_card = QFrame()
        relaunch_card.setProperty("class", "Card")
        rl = QVBoxLayout(relaunch_card)

        rl_title = QLabel("Interactive Relaunch Diagnostic Session")
        rl_title.setStyleSheet("font-weight: 600; font-size: 14px; color: #F8FAFC;")
        rl.addWidget(rl_title)

        rl_desc = QLabel(
            "Detect applications that repeatedly reopen after being closed. "
            "Start a controlled observation session to trace parent PIDs and identify the responsible task or watchdog."
        )
        rl_desc.setWordWrap(True)
        rl_desc.setStyleSheet("font-size: 12px; color: #94A3B8;")
        rl.addWidget(rl_desc)

        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("Target Process (optional):"))
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("e.g. browser_assistant (leave blank for all)")
        input_row.addWidget(self.target_input)

        input_row.addWidget(QLabel("Duration (seconds):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 60)
        self.duration_spin.setValue(15)
        input_row.addWidget(self.duration_spin)

        self.relaunch_btn = QPushButton("Start Diagnostic Session")
        self.relaunch_btn.setProperty("class", "PrimaryButton")
        self.relaunch_btn.clicked.connect(self._on_start_relaunch)
        input_row.addWidget(self.relaunch_btn)

        rl.addLayout(input_row)

        self.relaunch_log = QTextEdit()
        self.relaunch_log.setReadOnly(True)
        self.relaunch_log.setMaximumHeight(160)
        self.relaunch_log.setPlaceholderText("Relaunch observation findings and root cause evidence will appear here...")
        rl.addWidget(self.relaunch_log)

        layout.addWidget(relaunch_card)

        # 3. Privacy and Local Storage Notice
        priv_card = QFrame()
        priv_card.setProperty("class", "Card")
        pl = QVBoxLayout(priv_card)
        pl_title = QLabel("Privacy & Data Guarantee")
        pl_title.setStyleSheet("font-weight: 600; font-size: 14px; color: #F8FAFC;")
        pl.addWidget(pl_title)

        pl_desc = QLabel(
            "WinOptimize AI is 100% offline. No process lists, user details, telemetry, or diagnostic logs "
            "are transmitted over the network. All scan records and configuration snapshots are saved in a local "
            "SQLite database (`winop.db`) on your computer."
        )
        pl_desc.setWordWrap(True)
        pl_desc.setStyleSheet("font-size: 12px; color: #94A3B8;")
        pl.addWidget(pl_desc)
        layout.addWidget(priv_card)

        layout.addStretch()

    def _on_theme_changed(self, idx: int):
        theme_name = "dark" if idx == 0 else "light"
        self.theme_changed.emit(theme_name)

    def _on_start_relaunch(self):
        target = self.target_input.text().strip()
        targets = [target] if target else []
        duration = self.duration_spin.value()

        self.relaunch_btn.setEnabled(False)
        self.relaunch_btn.setText(f"Observing ({duration}s)...")
        self.relaunch_log.setText(f"[*] Started diagnostic observation session ({duration} seconds)...")
        self.start_relaunch_session.emit(targets, duration)

    def display_relaunch_report(self, report: RelaunchReport):
        self.relaunch_btn.setEnabled(True)
        self.relaunch_btn.setText("Start Diagnostic Session")

        lines = [
            f"[+] Session Completed: {report.summary}",
            f"[*] Monitored Duration: {report.duration_seconds}s",
            f"[*] Events Detected: {len(report.events_detected)}",
            "-" * 50,
        ]

        if not report.events_detected:
            lines.append("No recurring process launches observed during this session window.")
        else:
            for ev in report.events_detected:
                lines.append(f"\n[!] Target: {ev.target_process_name} (New PID: {ev.new_pid})")
                lines.append(f"    Parent: {ev.parent_name} (PID: {ev.parent_pid})")
                lines.append(f"    Likely Root Cause: {ev.likely_cause} (Confidence: {int(ev.confidence*100)}%)")
                lines.append(f"    Recommended Fix: {ev.recommended_fix}")
                for e in ev.evidence:
                    lines.append(f"    Evidence: {e}")

        self.relaunch_log.setText("\n".join(lines))
