"""
WinOptimize AI - Modern Theme Engine
Provides multiple distinct color themes:
- Dark Fluent (Default)
- Midnight Cyber (OLED Black)
- Nordic Cobalt (Deep Navy & Arctic Blue)
- Emerald Forest (Evergreen & Emerald)
- Sunset Amber (Obsidian & Golden Amber)
- Modern Light (Fluent Daylight)
"""

def _build_theme(
    bg_main: str,
    bg_surface: str,
    bg_card: str,
    border_color: str,
    text_primary: str,
    text_muted: str,
    accent_primary: str,
    accent_hover: str,
    accent_pressed: str,
    progress_chunk: str,
    badge_low_bg: str,
    badge_low_fg: str,
    badge_cond_bg: str,
    badge_cond_fg: str,
    badge_prot_bg: str,
    badge_prot_fg: str,
) -> str:
    return f"""
QMainWindow, QWidget {{
    background-color: {bg_main};
    color: {text_primary};
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
}}

QFrame#Sidebar {{
    background-color: {bg_surface};
    border-right: 1px solid {border_color};
}}

QLabel#AppTitle {{
    font-size: 18px;
    font-weight: 700;
    color: {accent_primary};
    padding: 12px 6px;
}}

QLabel#AppSubtitle {{
    font-size: 11px;
    color: {text_muted};
    padding-bottom: 12px;
}}

QPushButton.NavButton {{
    text-align: left;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    color: {text_primary};
    background-color: transparent;
    border: none;
    border-radius: 6px;
    margin: 2px 8px;
}}

QPushButton.NavButton:hover {{
    background-color: {border_color};
    color: #FFFFFF;
}}

QPushButton.NavButton:checked {{
    background-color: {accent_primary};
    color: #FFFFFF;
    font-weight: 600;
}}

QFrame.Card {{
    background-color: {bg_card};
    border: 1px solid {border_color};
    border-radius: 8px;
    padding: 14px;
}}

QLabel.CardTitle {{
    font-size: 12px;
    font-weight: 600;
    color: {text_muted};
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

QLabel.CardValue {{
    font-size: 24px;
    font-weight: 700;
    color: #FFFFFF;
    margin-top: 4px;
}}

QProgressBar {{
    background-color: {border_color};
    border-radius: 4px;
    height: 10px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {progress_chunk};
    border-radius: 4px;
}}

QPushButton.PrimaryButton {{
    background-color: {accent_primary};
    color: #FFFFFF;
    font-weight: 600;
    padding: 10px 20px;
    border-radius: 6px;
    border: none;
}}

QPushButton.PrimaryButton:hover {{
    background-color: {accent_hover};
}}

QPushButton.PrimaryButton:pressed {{
    background-color: {accent_pressed};
}}

QPushButton.SecondaryButton {{
    background-color: {bg_surface};
    color: {text_primary};
    font-weight: 500;
    padding: 8px 16px;
    border-radius: 6px;
    border: 1px solid {border_color};
}}

QPushButton.SecondaryButton:hover {{
    background-color: {border_color};
}}

QTableWidget {{
    background-color: {bg_surface};
    border: 1px solid {border_color};
    border-radius: 6px;
    gridline-color: {border_color};
    selection-background-color: {accent_primary};
    selection-color: #FFFFFF;
}}

QHeaderView::section {{
    background-color: {bg_card};
    color: {text_muted};
    font-weight: 600;
    padding: 8px;
    border: none;
    border-bottom: 1px solid {border_color};
}}

QLineEdit, QComboBox, QSpinBox, QTextEdit {{
    background-color: {bg_card};
    border: 1px solid {border_color};
    border-radius: 6px;
    padding: 6px 10px;
    color: {text_primary};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {{
    border: 1px solid {accent_primary};
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

/* Risk Badges */
QLabel.BadgeLow {{
    background-color: {badge_low_bg};
    color: {badge_low_fg};
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}}

QLabel.BadgeConditional {{
    background-color: {badge_cond_bg};
    color: {badge_cond_fg};
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}}

QLabel.BadgeProtected {{
    background-color: {badge_prot_bg};
    color: {badge_prot_fg};
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}}
"""

DARK_THEME = _build_theme(
    bg_main="#121417",
    bg_surface="#1A1D24",
    bg_card="#1E232D",
    border_color="#2D3748",
    text_primary="#E2E8F0",
    text_muted="#94A3B8",
    accent_primary="#2563EB",
    accent_hover="#1D4ED8",
    accent_pressed="#1E40AF",
    progress_chunk="#3B82F6",
    badge_low_bg="#064E3B",
    badge_low_fg="#34D399",
    badge_cond_bg="#78350F",
    badge_cond_fg="#FBBF24",
    badge_prot_bg="#1E3A8A",
    badge_prot_fg="#60A5FA",
)

MIDNIGHT_THEME = _build_theme(
    bg_main="#050505",
    bg_surface="#0B0D13",
    bg_card="#10141D",
    border_color="#1E293B",
    text_primary="#F8FAFC",
    text_muted="#64748B",
    accent_primary="#06B6D4",
    accent_hover="#0891B2",
    accent_pressed="#0E7490",
    progress_chunk="#06B6D4",
    badge_low_bg="#022C22",
    badge_low_fg="#10B981",
    badge_cond_bg="#451A03",
    badge_cond_fg="#F59E0B",
    badge_prot_bg="#172554",
    badge_prot_fg="#38BDF8",
)

NORDIC_THEME = _build_theme(
    bg_main="#0F172A",
    bg_surface="#1E293B",
    bg_card="#243048",
    border_color="#334155",
    text_primary="#F1F5F9",
    text_muted="#94A3B8",
    accent_primary="#38BDF8",
    accent_hover="#0EA5E9",
    accent_pressed="#0284C7",
    progress_chunk="#38BDF8",
    badge_low_bg="#064E3B",
    badge_low_fg="#34D399",
    badge_cond_bg="#78350F",
    badge_cond_fg="#FBBF24",
    badge_prot_bg="#1E3A8A",
    badge_prot_fg="#60A5FA",
)

EMERALD_THEME = _build_theme(
    bg_main="#041F1A",
    bg_surface="#062E27",
    bg_card="#093C33",
    border_color="#134E44",
    text_primary="#ECFDF5",
    text_muted="#6EE7B7",
    accent_primary="#10B981",
    accent_hover="#059669",
    accent_pressed="#047857",
    progress_chunk="#10B981",
    badge_low_bg="#064E3B",
    badge_low_fg="#34D399",
    badge_cond_bg="#78350F",
    badge_cond_fg="#FBBF24",
    badge_prot_bg="#134E4A",
    badge_prot_fg="#5EEAD4",
)

AMBER_THEME = _build_theme(
    bg_main="#181514",
    bg_surface="#231E1C",
    bg_card="#2F2825",
    border_color="#443934",
    text_primary="#FEF3C7",
    text_muted="#D97706",
    accent_primary="#F59E0B",
    accent_hover="#D97706",
    accent_pressed="#B45309",
    progress_chunk="#F59E0B",
    badge_low_bg="#064E3B",
    badge_low_fg="#34D399",
    badge_cond_bg="#78350F",
    badge_cond_fg="#FBBF24",
    badge_prot_bg="#451A03",
    badge_prot_fg="#FDBA74",
)

CYBERPUNK_THEME = _build_theme(
    bg_main="#0C0714",
    bg_surface="#160E24",
    bg_card="#201435",
    border_color="#3B1D61",
    text_primary="#F3E8FF",
    text_muted="#C084FC",
    accent_primary="#EC4899",
    accent_hover="#DB2777",
    accent_pressed="#BE185D",
    progress_chunk="#EC4899",
    badge_low_bg="#064E3B",
    badge_low_fg="#34D399",
    badge_cond_bg="#78350F",
    badge_cond_fg="#FBBF24",
    badge_prot_bg="#581C87",
    badge_prot_fg="#D8B4FE",
)

DRACULA_THEME = _build_theme(
    bg_main="#21222C",
    bg_surface="#282A36",
    bg_card="#343746",
    border_color="#44475A",
    text_primary="#F8F8F2",
    text_muted="#6272A4",
    accent_primary="#BD93F9",
    accent_hover="#A779E9",
    accent_pressed="#935ED8",
    progress_chunk="#BD93F9",
    badge_low_bg="#143A2B",
    badge_low_fg="#50FA7B",
    badge_cond_bg="#3D2B1F",
    badge_cond_fg="#FFB86C",
    badge_prot_bg="#32224A",
    badge_prot_fg="#FF79C6",
)

CRIMSON_THEME = _build_theme(
    bg_main="#14090B",
    bg_surface="#1E0E12",
    bg_card="#2A141A",
    border_color="#4C1D24",
    text_primary="#FFE4E6",
    text_muted="#FDA4AF",
    accent_primary="#E11D48",
    accent_hover="#BE123C",
    accent_pressed="#9F1239",
    progress_chunk="#E11D48",
    badge_low_bg="#064E3B",
    badge_low_fg="#34D399",
    badge_cond_bg="#78350F",
    badge_cond_fg="#FBBF24",
    badge_prot_bg="#4C1D24",
    badge_prot_fg="#FB7185",
)

TOKYO_NIGHT_THEME = _build_theme(
    bg_main="#16161E",
    bg_surface="#1A1B26",
    bg_card="#24283B",
    border_color="#363C52",
    text_primary="#C0CAF5",
    text_muted="#7AA2F7",
    accent_primary="#7AA2F7",
    accent_hover="#5B87E8",
    accent_pressed="#436FD6",
    progress_chunk="#7AA2F7",
    badge_low_bg="#0F3832",
    badge_low_fg="#73DACA",
    badge_cond_bg="#402D1E",
    badge_cond_fg="#E0AF68",
    badge_prot_bg="#2D274A",
    badge_prot_fg="#BB9AF7",
)

SOLARIZED_DARK_THEME = _build_theme(
    bg_main="#00212B",
    bg_surface="#002B36",
    bg_card="#073642",
    border_color="#0E4856",
    text_primary="#93A1A1",
    text_muted="#657B83",
    accent_primary="#2AA198",
    accent_hover="#268BD2",
    accent_pressed="#1E70A8",
    progress_chunk="#2AA198",
    badge_low_bg="#0B3728",
    badge_low_fg="#859900",
    badge_cond_bg="#3D2912",
    badge_cond_fg="#B58900",
    badge_prot_bg="#11334E",
    badge_prot_fg="#268BD2",
)

ROSE_PINE_THEME = _build_theme(
    bg_main="#14121F",
    bg_surface="#191724",
    bg_card="#211F30",
    border_color="#332E45",
    text_primary="#E0DEF4",
    text_muted="#908CAA",
    accent_primary="#EB6F92",
    accent_hover="#D9577D",
    accent_pressed="#C0446A",
    progress_chunk="#EB6F92",
    badge_low_bg="#19333A",
    badge_low_fg="#31748F",
    badge_cond_bg="#3D3226",
    badge_cond_fg="#F6C177",
    badge_prot_bg="#302444",
    badge_prot_fg="#C4A7E7",
)

LIGHT_THEME = """
QMainWindow, QWidget {
    background-color: #F8FAFC;
    color: #0F172A;
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
    color: #2563EB;
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
    color: #334155;
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

QPushButton.PrimaryButton:pressed {
    background-color: #1E40AF;
}

QPushButton.SecondaryButton {
    background-color: #F1F5F9;
    color: #1E293B;
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

QLineEdit, QComboBox, QSpinBox, QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0F172A;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {
    border: 1px solid #2563EB;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

/* Risk Badges */
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

THEMES = {
    "dark": DARK_THEME,
    "midnight": MIDNIGHT_THEME,
    "nordic": NORDIC_THEME,
    "emerald": EMERALD_THEME,
    "amber": AMBER_THEME,
    "cyberpunk": CYBERPUNK_THEME,
    "dracula": DRACULA_THEME,
    "crimson": CRIMSON_THEME,
    "tokyo_night": TOKYO_NIGHT_THEME,
    "solarized_dark": SOLARIZED_DARK_THEME,
    "rose_pine": ROSE_PINE_THEME,
    "light": LIGHT_THEME,
}
