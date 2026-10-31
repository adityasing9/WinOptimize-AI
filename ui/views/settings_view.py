"""
WinOptimize AI - Settings, In-App Updater & Diagnostics View
Theme selection (6 modern themes), in-app updater from GitHub, admin elevation, and relaunch diagnostics.
"""

from __future__ import annotations
import ctypes
import os
import sys
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QTextEdit, QFrame, QProgressBar, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal

from monitoring.relaunch_detector import RelaunchReport
from updater.in_app_updater import ReleaseInfo, APP_VERSION


class SettingsView(QWidget):
    """Configuration, in-app updater, theme switcher, and relaunch diagnostics."""
    theme_changed = Signal(str)  # theme key
    start_relaunch_session = Signal(list, int)  # (targets, duration)
    check_update_requested = Signal()
    apply_update_requested = Signal(str)  # download_url

    THEME_KEYS = [
        "dark",
        "midnight",
        "nordic",
        "emerald",
        "amber",
        "cyberpunk",
        "dracula",
        "crimson",
        "tokyo_night",
        "solarized_dark",
        "rose_pine",
        "light",
    ]
    THEME_LABELS = [
        "🌙 Dark Fluent (Default)",
        "🌑 Midnight Cyber (OLED Black)",
        "🌊 Nordic Cobalt (Navy & Arctic Blue)",
        "🌲 Emerald Forest (Evergreen & Mint)",
        "🌅 Sunset Amber (Obsidian & Gold)",
        "🔮 Cyberpunk Neon (Pink & Purple)",
        "🧛 Dracula Theme (Gothic Violet)",
        "🩸 Crimson Red (Blood Moon)",
        "🗼 Tokyo Night (Deep Synthwave)",
        "☀️ Solarized Dark (Teal & Yellow)",
        "🌸 Rosé Pine (Soft Dusk & Pastel)",
        "☀️ Modern Light (Fluent Daylight)",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.latest_release_info: Optional[ReleaseInfo] = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(0)

        # Scroll area so settings page fits comfortably
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Header
        title = QLabel("Settings & Application Management")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #60A5FA;")
        layout.addWidget(title)

        # 1. In-App Self-Updater Card
        update_card = QFrame()
        update_card.setProperty("class", "Card")
        ul = QVBoxLayout(update_card)

        u_title = QLabel("Application Updates (In-App Direct Update)")
        u_title.setStyleSheet("font-weight: 600; font-size: 14px; color: #F8FAFC;")
        ul.addWidget(u_title)

        u_desc = QLabel(f"Current installed version: <b>v{APP_VERSION}</b>. Update directly from inside the app without manual downloads.")
        u_desc.setStyleSheet("font-size: 12px; color: #94A3B8;")
        ul.addWidget(u_desc)

        btn_row = QHBoxLayout()
        self.check_update_btn = QPushButton("Check for Updates")
        self.check_update_btn.setProperty("class", "PrimaryButton")
        self.check_update_btn.clicked.connect(self._on_check_update)
        btn_row.addWidget(self.check_update_btn)

        self.apply_update_btn = QPushButton("Download & Update Now")
        self.apply_update_btn.setProperty("class", "PrimaryButton")
        self.apply_update_btn.setStyleSheet("background-color: #10B981;")
        self.apply_update_btn.setVisible(False)
        self.apply_update_btn.clicked.connect(self._on_apply_update)
        btn_row.addWidget(self.apply_update_btn)

        btn_row.addStretch()
        ul.addLayout(btn_row)

        self.update_progress = QProgressBar()
        self.update_progress.setRange(0, 100)
        self.update_progress.setValue(0)
        self.update_progress.setVisible(False)
        ul.addWidget(self.update_progress)

        self.update_status_lbl = QLabel("")
        self.update_status_lbl.setStyleSheet("font-size: 12px; color: #38BDF8;")
        self.update_status_lbl.setWordWrap(True)
        ul.addWidget(self.update_status_lbl)

        layout.addWidget(update_card)

        # 2. Administrator Elevation Card
        elev_card = QFrame()
        elev_card.setProperty("class", "Card")
        el = QVBoxLayout(elev_card)

        is_admin = False
        try:
            is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            pass

        el_title = QLabel("System Permission Level")
        el_title.setStyleSheet("font-weight: 600; font-size: 14px; color: #F8FAFC;")
        el.addWidget(el_title)

        status_text = "<b>Status:</b> Administrator (Elevated — can modify all system tasks & services)" if is_admin else "<b>Status:</b> Standard User (Requires UAC elevation for tasks marked 'Highest RunLevel')"
        status_color = "#34D399" if is_admin else "#FBBF24"
        admin_lbl = QLabel(status_text)
        admin_lbl.setStyleSheet(f"font-size: 12px; color: {status_color};")
        el.addWidget(admin_lbl)

        if not is_admin:
            elev_btn = QPushButton("🛡️ Relaunch as Administrator")
            elev_btn.setProperty("class", "SecondaryButton")
            elev_btn.setToolTip("Restarts WinOptimize AI with administrative rights to modify root-level tasks.")
            elev_btn.clicked.connect(self._relaunch_as_admin)
            el.addWidget(elev_btn)

        layout.addWidget(elev_card)

        # 3. Appearance / Themes Card (6 Distinct Themes)
        theme_card = QFrame()
        theme_card.setProperty("class", "Card")
        tl = QVBoxLayout(theme_card)
        tl_title = QLabel("Application Theme & Colors")
        tl_title.setStyleSheet("font-weight: 600; font-size: 14px; color: #F8FAFC;")
        tl.addWidget(tl_title)

        theme_row = QHBoxLayout()
        theme_lbl = QLabel("Color Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self.THEME_LABELS)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_row.addWidget(theme_lbl)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        tl.addLayout(theme_row)
        layout.addWidget(theme_card)

        # 4. Interactive Relaunch Diagnostics Tool
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
        self.relaunch_log.setMaximumHeight(140)
        self.relaunch_log.setPlaceholderText("Relaunch observation findings and root cause evidence will appear here...")
        rl.addWidget(self.relaunch_log)

        layout.addWidget(relaunch_card)

        # 5. Privacy and Local Storage Notice
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

    def _relaunch_as_admin(self):
        """Relaunches application with UAC administrative rights."""
        try:
            exe = sys.executable
            ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, " ".join(sys.argv[1:]), None, 1)
            sys.exit(0)
        except Exception as e:
            QMessageBox.warning(self, "Elevation Failed", f"Could not request administrator elevation:\n{e}")

    def _on_theme_changed(self, idx: int):
        theme_key = self.THEME_KEYS[idx] if idx < len(self.THEME_KEYS) else "dark"
        self.theme_changed.emit(theme_key)

    # -------------------------------------------------------------------------
    # In-App Updater Handlers
    # -------------------------------------------------------------------------
    def _on_check_update(self):
        self.check_update_btn.setEnabled(False)
        self.check_update_btn.setText("Checking GitHub...")
        self.update_status_lbl.setText("Connecting to GitHub Releases API...")
        self.check_update_requested.emit()

    def display_update_info(self, info: Optional[ReleaseInfo]):
        self.check_update_btn.setEnabled(True)
        self.check_update_btn.setText("Check for Updates")

        if not info:
            self.update_status_lbl.setText("You are running the latest version, or could not connect to GitHub.")
            self.apply_update_btn.setVisible(False)
            return

        self.latest_release_info = info
        if info.is_newer:
            self.update_status_lbl.setText(
                f"🎉 <b>New Version Available: {info.tag_name}</b> ({info.asset_size_mb} MB)<br>"
                f"Release: <i>{info.title}</i>"
            )
            self.apply_update_btn.setText(f"Update to {info.tag_name} Now")
            self.apply_update_btn.setVisible(True)
        else:
            self.update_status_lbl.setText(
                f"✓ App is up to date (Version <b>{APP_VERSION}</b> is the latest release). "
                f"<br>Re-download or force re-update is available if needed."
            )
            self.apply_update_btn.setText(f"Re-download & Refresh ({info.tag_name})")
            self.apply_update_btn.setVisible(True)

    def _on_apply_update(self):
        if not self.latest_release_info or not self.latest_release_info.download_url:
            QMessageBox.warning(self, "No URL", "No update download URL available.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm In-App Update",
            f"Download and apply update {self.latest_release_info.tag_name} ({self.latest_release_info.asset_size_mb} MB)?\n"
            f"The application will restart automatically after applying.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self.apply_update_btn.setEnabled(False)
            self.apply_update_btn.setText("Downloading...")
            self.update_progress.setVisible(True)
            self.update_progress.setValue(0)
            self.apply_update_requested.emit(self.latest_release_info.download_url)

    def set_update_progress(self, pct: int):
        self.update_progress.setValue(pct)
        self.update_status_lbl.setText(f"Downloading update from GitHub: {pct}%")

    def on_update_completed(self, success: bool, msg: str):
        self.apply_update_btn.setEnabled(True)
        self.apply_update_btn.setText("Download & Update Now")
        self.update_progress.setVisible(False)
        if not success:
            QMessageBox.critical(self, "Update Failed", f"Update could not be applied:\n{msg}")

    # -------------------------------------------------------------------------
    # Relaunch Diagnostics Handlers
    # -------------------------------------------------------------------------
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
