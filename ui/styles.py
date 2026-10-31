"""
WinOptimize AI - Modern Themes and Stylesheets
Professional, Fluent-inspired styling for Dark and Light themes.
"""

DARK_THEME = """
QMainWindow, QWidget {
    background-color: #121417;
    color: #E2E8F0;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
}

QFrame#Sidebar {
    background-color: #1A1D24;
    border-right: 1px solid #2D3748;
}

QLabel#AppTitle {
    font-size: 18px;
    font-weight: 700;
    color: #60A5FA;
    padding: 12px 6px;
}

QLabel#AppSubtitle {
    font-size: 11px;
    color: #94A3B8;
    padding-bottom: 12px;
}

QPushButton.NavButton {
    text-align: left;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    color: #CBD5E1;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    margin: 2px 8px;
}

QPushButton.NavButton:hover {
    background-color: #2D3748;
    color: #FFFFFF;
}

QPushButton.NavButton:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: 600;
}

QFrame.Card {
    background-color: #1E232D;
    border: 1px solid #2D3748;
    border-radius: 8px;
    padding: 14px;
}

QLabel.CardTitle {
    font-size: 12px;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel.CardValue {
    font-size: 24px;
    font-weight: 700;
    color: #F8FAFC;
    margin-top: 4px;
}

QProgressBar {
    background-color: #2D3748;
    border-radius: 4px;
    height: 10px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #3B82F6;
    border-radius: 4px;
}

QPushButton.PrimaryButton {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: 600;
    padding: 10px 20px;
    border-radius: 6px;
    border: none;
}

QPushButton.PrimaryButton:hover {
    background-color: #1D4ED8;
}

QPushButton.PrimaryButton:pressed {
    background-color: #1E40AF;
}

QPushButton.SecondaryButton {
    background-color: #2D3748;
    color: #E2E8F0;
    font-weight: 500;
    padding: 8px 16px;
    border-radius: 6px;
    border: 1px solid #4A5568;
}

QPushButton.SecondaryButton:hover {
    background-color: #4A5568;
}

QTableWidget {
    background-color: #1A1D24;
    border: 1px solid #2D3748;
    border-radius: 6px;
    gridline-color: #2D3748;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #1E232D;
    color: #CBD5E1;
    font-weight: 600;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #2D3748;
}

QLineEdit, QComboBox {
    background-color: #1E232D;
    border: 1px solid #4A5568;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F8FAFC;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #3B82F6;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

/* Risk Pill Badges */
QLabel.BadgeLow {
    background-color: #064E3B;
    color: #34D399;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}

QLabel.BadgeConditional {
    background-color: #78350F;
    color: #FBBF24;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}

QLabel.BadgeProtected {
    background-color: #1E3A8A;
    color: #60A5FA;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}
"""

LIGHT_THEME = """
QMainWindow, QWidget {
    background-color: #F8FAFC;
    color: #1E293B;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
}

QFrame#Sidebar {
    background-color: #FFFFFF;
    border-right: 1px solid #E2E8F0;
}

QLabel#AppTitle {
    font-size: 18px;
    font-weight: 700;
    color: #1D4ED8;
    padding: 12px 6px;
}

QLabel#AppSubtitle {
    font-size: 11px;
    color: #64748B;
    padding-bottom: 12px;
}

QPushButton.NavButton {
    text-align: left;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    color: #475569;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    margin: 2px 8px;
}

QPushButton.NavButton:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}

QPushButton.NavButton:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: 600;
}

QFrame.Card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 14px;
}

QLabel.CardTitle {
    font-size: 12px;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel.CardValue {
    font-size: 24px;
    font-weight: 700;
    color: #0F172A;
    margin-top: 4px;
}

QProgressBar {
    background-color: #E2E8F0;
    border-radius: 4px;
    height: 10px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #2563EB;
    border-radius: 4px;
}

QPushButton.PrimaryButton {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: 600;
    padding: 10px 20px;
    border-radius: 6px;
    border: none;
}

QPushButton.PrimaryButton:hover {
    background-color: #1D4ED8;
}

QPushButton.SecondaryButton {
    background-color: #F1F5F9;
    color: #334155;
    font-weight: 500;
    padding: 8px 16px;
    border-radius: 6px;
    border: 1px solid #CBD5E1;
}

QPushButton.SecondaryButton:hover {
    background-color: #E2E8F0;
}

QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    gridline-color: #F1F5F9;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    font-weight: 600;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #E2E8F0;
}

QLineEdit, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0F172A;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #2563EB;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

/* Risk Pill Badges */
QLabel.BadgeLow {
    background-color: #D1FAE5;
    color: #065F46;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}

QLabel.BadgeConditional {
    background-color: #FEF3C7;
    color: #92400E;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}

QLabel.BadgeProtected {
    background-color: #DBEAFE;
    color: #1E40AF;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}
"""
