"""Military olive/amber theme for the Sniper Elite 5 Editor GUI.

Color palette (tactical field):
- BG           #1a1f14   dark olive base
- BG_ALT       #232b1d   panel body
- BG_HOVER     #3a4a2a   hover wash
- BG_INPUT     #1e2519   inputs
- BG_GLASS     #2a3520   frosted card
- TEXT         #e8e8d8   primary body (field tan)
- TEXT_MUTED   #9aa888   secondary text
- TEXT_DIM     #5a6a4a   disabled / meta
- ACCENT       #d4a843   primary interactive (brass/amber)
- ACCENT_LIGHT #f0c860   hover / light accent
- ACCENT_DIM   #8a6f20   selection fill / pressed
- ACCENT_RED   #c44a3a   danger / recoil warning
- BORDER       #4a5a3a   olive edge
- BORDER_LIGHT #6a8a5a   soft highlight edge
- ERROR        #ff6b6b   error
- SUCCESS      #6bcf8e   success
- PLAYER_WEAPON #7ec8e0  loadout / gunsmith weapons
- LEVEL_WEAPON #e0a060   mission pickups
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication

# ── Color constants ──────────────────────────────────────────────────────

BG = "#1a1f14"
BG_ALT = "#232b1d"
BG_HOVER = "#3a4a2a"
BG_INPUT = "#1e2519"
BG_GLASS = "#2a3520"
TEXT = "#e8e8d8"
TEXT_MUTED = "#9aa888"
TEXT_DIM = "#5a6a4a"
ACCENT = "#d4a843"
ACCENT_LIGHT = "#f0c860"
ACCENT_DIM = "#8a6f20"
ACCENT_RED = "#c44a3a"
BORDER = "#4a5a3a"
BORDER_LIGHT = "#6a8a5a"
ERROR = "#ff6b6b"
SUCCESS = "#6bcf8e"
WARNING = "#e8c84a"
WARNING_BG = "#2a2a14"
WARNING_BORDER = "#8a7a20"
# Weapon browser: loadout / gunsmith guns vs mission pickups
PLAYER_WEAPON = "#7ec8e0"
LEVEL_WEAPON = "#e0a060"
# Unverified / playtest-candidate fields (temporary debug highlight)
TEST_FIELD = "#ff9f43"
TEST_FIELD_BG = "rgba(255, 159, 67, 0.12)"

_GLASS_BORDER = "rgba(160, 180, 120, 0.25)"
_GLASS_PANEL = "rgba(35, 43, 29, 0.65)"
_GLASS_LIGHT = "rgba(42, 53, 32, 0.50)"
_TABLE_BG = "rgba(26, 31, 20, 0.55)"
_TABLE_ALT = "rgba(20, 25, 16, 0.42)"

# ── Font family ──────────────────────────────────────────────────────────

FONT_REGULAR = "DejaVu Sans"
FONT_MONO = "DejaVu Sans Mono"

# ── Stylesheet ───────────────────────────────────────────────────────────

_STYLESHEET = f"""
QWidget {{
    background: transparent;
    color: {TEXT};
    font-family: "{FONT_REGULAR}", sans-serif;
    font-size: 13px;
    font-weight: 400;
}}

QMainWindow {{
    background: {BG};
}}

QWidget:disabled {{
    color: {TEXT_DIM};
}}

QToolTip {{
    background: {BG_ALT};
    color: {TEXT};
    border: 1px solid {_GLASS_BORDER};
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 12px;
}}

QLabel {{
    background: transparent;
    color: {TEXT};
    font-weight: 400;
}}

QGroupBox {{
    background: {_GLASS_PANEL};
    border: 1px solid {_GLASS_BORDER};
    border-radius: 8px;
    margin-top: 20px;
    padding: 16px 8px 8px 8px;
    font-weight: 700;
    font-size: 13px;
    color: {ACCENT};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {ACCENT};
    font-weight: 700;
    background: transparent;
}}

QTabWidget::pane {{
    border: 1px solid {_GLASS_BORDER};
    border-radius: 0 8px 8px 8px;
    background: transparent;
    top: -1px;
}}
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: {_GLASS_LIGHT};
    color: {TEXT_MUTED};
    border: 1px solid {_GLASS_BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 7px 16px;
    margin-right: 3px;
    font-weight: 500;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background: rgba(35, 43, 29, 0.72);
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    background: {BG_HOVER};
    color: {TEXT};
}}

QPushButton {{
    background: {BG_ALT};
    color: {TEXT};
    border: 1px solid {_GLASS_BORDER};
    border-radius: 6px;
    padding: 5px 14px;
    font-weight: 500;
    font-size: 12px;
}}
QPushButton:hover {{
    background: {BG_HOVER};
    border-color: {ACCENT};
    color: {ACCENT_LIGHT};
}}
QPushButton:pressed {{
    background: {ACCENT_DIM};
    color: white;
    border-color: {ACCENT};
}}
QPushButton:disabled {{
    background: {BG_ALT};
    color: {TEXT_DIM};
    border-color: {BORDER};
}}
QPushButton:checked {{
    background: {ACCENT_DIM};
    color: {TEXT};
    border-color: {ACCENT};
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 3px 6px;
    font-weight: 400;
    font-size: 13px;
    selection-background-color: {ACCENT_DIM};
    selection-color: white;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: {BG_ALT};
    border: none;
    width: 16px;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    border-top-right-radius: 5px;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    border-top: 1px solid {BORDER};
    border-bottom-right-radius: 5px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {BG_HOVER};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: none;
    width: 8px;
    height: 8px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {ACCENT};
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    width: 8px;
    height: 8px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {ACCENT};
}}
QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {{
    border-bottom-color: {ACCENT_LIGHT};
}}
QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {{
    border-top-color: {ACCENT_LIGHT};
}}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled,
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{
    border-top-color: {TEXT_DIM};
    border-bottom-color: {TEXT_DIM};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
    background: {BG_ALT};
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 10px;
    height: 10px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {ACCENT};
}}
QComboBox::down-arrow:hover {{
    border-top-color: {ACCENT_LIGHT};
}}
QComboBox::down-arrow:disabled {{
    border-top-color: {TEXT_DIM};
}}
QComboBox QAbstractItemView {{
    background: {BG_ALT};
    color: {TEXT};
    border: 1px solid {_GLASS_BORDER};
    selection-background-color: {ACCENT_DIM};
    selection-color: white;
    outline: 0;
}}
QComboBox QAbstractItemView::item {{
    padding: 3px 8px;
}}
QComboBox QAbstractItemView::item:hover {{
    background: {BG_HOVER};
    color: {TEXT};
}}
QComboBox QAbstractItemView::item:selected {{
    background: {ACCENT_DIM};
    color: white;
}}

QCheckBox {{
    color: {TEXT};
    font-weight: 400;
    spacing: 6px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background: {BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT_LIGHT};
}}

QRadioButton {{
    color: {TEXT};
    spacing: 6px;
    background: transparent;
}}
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER};
    border-radius: 7px;
    background: {BG_INPUT};
}}
QRadioButton::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {BORDER_LIGHT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {BORDER_LIGHT};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QTreeView, QTableView, QTreeWidget, QTableWidget {{
    background: {_TABLE_BG};
    color: {TEXT};
    border: 1px solid {_GLASS_BORDER};
    border-radius: 6px;
    gridline-color: {BORDER};
    font-weight: 400;
    font-size: 12px;
    selection-background-color: {ACCENT_DIM};
    selection-color: white;
    alternate-background-color: {_TABLE_ALT};
}}
QTreeView::item, QTableView::item, QTreeWidget::item, QTableWidget::item {{
    padding: 2px 4px;
}}
QTreeView::item:selected, QTableView::item:selected,
QTreeWidget::item:selected, QTableWidget::item:selected {{
    background: {ACCENT_DIM};
    color: white;
}}
QHeaderView::section {{
    background: {BG};
    color: {ACCENT};
    padding: 4px 6px;
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    font-weight: 600;
    font-size: 11px;
}}

QPlainTextEdit, QTextEdit, QTextBrowser {{
    background: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    font-weight: 400;
    font-size: 12px;
    selection-background-color: {ACCENT_DIM};
    selection-color: white;
}}

QMenuBar {{
    background: {BG_ALT};
    color: {TEXT};
    font-weight: 500;
    border-bottom: 1px solid {_GLASS_BORDER};
}}
QMenuBar::item {{
    background: transparent;
    padding: 4px 10px;
}}
QMenuBar::item:selected {{
    background: {BG_HOVER};
    color: {ACCENT_LIGHT};
}}
QMenu {{
    background: {BG_ALT};
    color: {TEXT};
    border: 1px solid {_GLASS_BORDER};
    border-radius: 6px;
}}
QMenu::item {{
    padding: 5px 28px 5px 16px;
    border-radius: 3px;
    margin: 1px 4px;
}}
QMenu::item:selected {{
    background: {ACCENT_DIM};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}

QToolBar {{
    background: {BG_ALT};
    border-bottom: 1px solid {_GLASS_BORDER};
    spacing: 4px;
    padding: 3px;
}}
QToolBar::separator {{
    background: {BORDER};
    width: 1px;
    margin: 4px 4px;
}}

QStatusBar {{
    background: {BG_ALT};
    color: {TEXT_MUTED};
    font-weight: 400;
    font-size: 12px;
    border-top: 1px solid {_GLASS_BORDER};
}}
QStatusBar::item {{ border: none; }}

QProgressBar {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    text-align: center;
    color: {TEXT};
    font-weight: 500;
    font-size: 11px;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 4px;
}}

QFrame {{
    background: transparent;
    color: {TEXT};
}}
QFrame[frameShape="4"], QFrame[frameShape="5"], QFrame[frameShape="6"] {{
    background: {_GLASS_LIGHT};
    border: 1px solid {_GLASS_BORDER};
    border-radius: 6px;
}}

QSplitter::handle {{
    background: {BORDER};
}}
QSplitter::handle:horizontal {{ width: 2px; }}
QSplitter::handle:vertical {{ height: 2px; }}

QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QDialog {{
    background: {BG};
    color: {TEXT};
}}

QMessageBox {{
    background: {BG_ALT};
}}
QMessageBox QLabel {{
    color: {TEXT};
    font-size: 13px;
    background: transparent;
}}

QListWidget, QListView {{
    background: {BG_ALT};
    color: {TEXT};
    border: 1px solid {_GLASS_BORDER};
    border-radius: 6px;
    selection-background-color: {ACCENT_DIM};
    selection-color: white;
    outline: 0;
}}
QListWidget::item:selected, QListView::item:selected {{
    background: {ACCENT_DIM};
    color: white;
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: {BG_INPUT};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 14px;
    margin: -5px 0;
    background: {ACCENT};
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT_DIM};
    border-radius: 3px;
}}
"""


def qcolor(hex_str: str, alpha: int = 255) -> QColor:
    c = QColor(hex_str)
    if alpha < 255:
        c.setAlpha(alpha)
    return c


def apply_theme(app: QApplication) -> None:
    font = QFont(FONT_REGULAR, 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    app.setStyleSheet(_STYLESHEET)


def title_font(weight: int = 800) -> QFont:
    f = QFont(FONT_REGULAR)
    f.setWeight(_qt_weight(weight))
    return f


def header_font(weight: int = 700) -> QFont:
    f = QFont(FONT_REGULAR)
    f.setWeight(_qt_weight(weight))
    return f


def data_font() -> QFont:
    return QFont(FONT_MONO)


def muted_style(extra: str = "") -> str:
    base = f"color: {TEXT_MUTED};"
    return f"{base} {extra}".strip() if extra else base


def accent_style(extra: str = "") -> str:
    base = f"color: {ACCENT};"
    return f"{base} {extra}".strip() if extra else base


def warning_chip_style() -> str:
    return (
        f"color: {WARNING}; background: {WARNING_BG}; "
        f"border: 1px solid {WARNING_BORDER}; border-radius: 6px; "
        f"padding: 6px 10px;"
    )


def _qt_weight(css_weight: int) -> QFont.Weight:
    mapping = {
        100: QFont.Weight.Thin,
        200: QFont.Weight.ExtraLight,
        300: QFont.Weight.Light,
        400: QFont.Weight.Normal,
        500: QFont.Weight.Medium,
        600: QFont.Weight.DemiBold,
        700: QFont.Weight.Bold,
        800: QFont.Weight.ExtraBold,
        900: QFont.Weight.Black,
    }
    return mapping.get(css_weight, QFont.Weight.Normal)
