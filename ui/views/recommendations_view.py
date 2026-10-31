"""
WinOptimize AI - Recommendations View
Interactive cards displaying actionable recommendations, risk badges, evidence,
side effects, and individual user approval controls.
"""

from __future__ import annotations
from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QCheckBox, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from analyzer.process_analyzer import OptimizationRecommendation
from rules.rule_definitions import RuleRiskLevel


class RecommendationCard(QFrame):
    """Card widget for an individual recommendation."""
    approval_toggled = Signal(object, bool)  # (OptimizationRecommendation, bool)

    def __init__(self, rec: OptimizationRecommendation, parent=None):
        super().__init__(parent)
        self.rec = rec
        self.setProperty("class", "Card")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header: Checkbox + Title + Risk Badge + Confidence
        header_layout = QHBoxLayout()

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.rec.is_approved)
        self.checkbox.stateChanged.connect(self._on_check_changed)
        header_layout.addWidget(self.checkbox)

        title_lbl = QLabel(self.rec.title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
        header_layout.addWidget(title_lbl)

        header_layout.addStretch()

        # Risk Badge
        risk_badge = QLabel(self.rec.risk_level.value)
        if self.rec.risk_level == RuleRiskLevel.LOW:
            risk_badge.setProperty("class", "BadgeLow")
        elif self.rec.risk_level == RuleRiskLevel.CONDITIONAL:
            risk_badge.setProperty("class", "BadgeConditional")
        else:
            risk_badge.setProperty("class", "BadgeProtected")
        header_layout.addWidget(risk_badge)

        conf_lbl = QLabel(f"{int(self.rec.confidence * 100)}% Confidence")
        conf_lbl.setStyleSheet("font-size: 11px; color: #94A3B8; font-weight: 500;")
        header_layout.addWidget(conf_lbl)

        layout.addLayout(header_layout)

        # Description
        desc_lbl = QLabel(self.rec.description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; color: #CBD5E1;")
        layout.addWidget(desc_lbl)

        # Details Grid / Metadata
        meta_box = QFrame()
        meta_box.setStyleSheet("background-color: rgba(0, 0, 0, 0.2); border-radius: 6px; padding: 8px;")
        meta_l = QVBoxLayout(meta_box)
        meta_l.setSpacing(4)
        meta_l.setContentsMargins(8, 8, 8, 8)

        action_lbl = QLabel(f"• <b>Recommended Action:</b> {self.rec.recommended_action}")
        action_lbl.setStyleSheet("font-size: 11px; color: #38BDF8;")
        meta_l.addWidget(action_lbl)

        side_effect_lbl = QLabel(f"• <b>Side Effects:</b> {self.rec.side_effects}")
        side_effect_lbl.setStyleSheet("font-size: 11px; color: #F59E0B;")
        meta_l.addWidget(side_effect_lbl)

        reversibility_lbl = QLabel(f"• <b>Rollback Method:</b> {self.rec.reversibility_info}")
        reversibility_lbl.setStyleSheet("font-size: 11px; color: #34D399;")
        meta_l.addWidget(reversibility_lbl)

        if self.rec.observed_ram_mb > 0:
            ram_lbl = QLabel(f"• <b>Observed Resident Memory:</b> ~{self.rec.observed_ram_mb} MB")
            ram_lbl.setStyleSheet("font-size: 11px; color: #CBD5E1;")
            meta_l.addWidget(ram_lbl)

        elev_text = "Yes (UAC prompt required)" if self.rec.requires_elevation else "No (Standard user rights)"
        elev_lbl = QLabel(f"• <b>Requires Elevation:</b> {elev_text}")
        elev_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        meta_l.addWidget(elev_lbl)

        layout.addWidget(meta_box)

    def _on_check_changed(self, state):
        is_checked = (state == Qt.Checked.value or state == 2)
        self.rec.is_approved = is_checked
        self.approval_toggled.emit(self.rec, is_checked)


class RecommendationsView(QWidget):
    """View managing the list of recommendation cards and batch actions."""
    proceed_to_optimize = Signal(list)  # (List[OptimizationRecommendation])

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recommendations: List[OptimizationRecommendation] = []
        self.cards: List[RecommendationCard] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header & Action Toolbar
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Optimization Recommendations")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #60A5FA;")
        sub = QLabel("Select items to optimize. Low-risk changes can be safely approved.")
        sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        self.approve_low_btn = QPushButton("Approve Low Risk")
        self.approve_low_btn.setProperty("class", "SecondaryButton")
        self.approve_low_btn.setToolTip("Selects only confirmed LOW-RISK startup items.")
        self.approve_low_btn.clicked.connect(self._approve_all_low_risk)
        header_layout.addWidget(self.approve_low_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setProperty("class", "SecondaryButton")
        self.clear_btn.clicked.connect(self._clear_all)
        header_layout.addWidget(self.clear_btn)

        self.proceed_btn = QPushButton("Review & Apply (0)")
        self.proceed_btn.setProperty("class", "PrimaryButton")
        self.proceed_btn.clicked.connect(self._on_proceed)
        header_layout.addWidget(self.proceed_btn)

        main_layout.addLayout(header_layout)

        # Scrollable area for cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setSpacing(14)
        self.cards_layout.setContentsMargins(0, 0, 10, 0)
        self.cards_layout.addStretch()
        self.scroll.setWidget(self.scroll_content)

        main_layout.addWidget(self.scroll)

    def populate(self, recommendations: List[OptimizationRecommendation]):
        self.recommendations = recommendations
        # Clear existing cards
        while self.cards_layout.count() > 1:
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.cards.clear()

        if not recommendations:
            empty_lbl = QLabel("No optimization recommendations generated. Your system is cleanly configured!")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #94A3B8; font-size: 14px; margin: 40px;")
            self.cards_layout.insertWidget(0, empty_lbl)
            self._update_proceed_button()
            return

        for rec in recommendations:
            card = RecommendationCard(rec)
            card.approval_toggled.connect(self._on_card_toggled)
            self.cards.append(card)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

        self._update_proceed_button()

    def _on_card_toggled(self, rec, is_checked):
        self._update_proceed_button()

    def _approve_all_low_risk(self):
        for card in self.cards:
            if card.rec.risk_level == RuleRiskLevel.LOW:
                card.checkbox.setChecked(True)
        self._update_proceed_button()

    def _clear_all(self):
        for card in self.cards:
            card.checkbox.setChecked(False)
        self._update_proceed_button()

    def _update_proceed_button(self):
        count = sum(1 for c in self.cards if c.checkbox.isChecked())
        self.proceed_btn.setText(f"Review & Apply ({count})")
        self.proceed_btn.setEnabled(count > 0)

    def _on_proceed(self):
        approved = [c.rec for c in self.cards if c.checkbox.isChecked()]
        self.proceed_to_optimize.emit(approved)
