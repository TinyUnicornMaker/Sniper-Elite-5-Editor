#!/usr/bin/env python3
"""Sniper Elite 5 Editor — Desktop application for editing SE5 weapon/scope stats."""
import sys
import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)


def _clear_stale_caches(root_dir: str):
    """Remove all __pycache__ dirs and .pyc files to prevent stale bytecode."""
    import shutil
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if os.path.basename(dirpath) == "__pycache__":
            try:
                shutil.rmtree(dirpath)
            except OSError:
                pass
            dirnames.clear()
        else:
            for f in filenames:
                if f.endswith(".pyc"):
                    try:
                        os.remove(os.path.join(dirpath, f))
                    except OSError:
                        pass


_CLEAR_STALE_CACHES_AT_STARTUP = True
if _CLEAR_STALE_CACHES_AT_STARTUP:
    _clear_stale_caches(_ROOT)

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from gui.theme import apply_theme
from gui.main_window import MainWindow


def _install_excepthook():
    """Surface exceptions raised inside PySide6 signal slots."""
    import traceback

    def _hook(exc_type, exc_value, exc_tb):
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(tb_text, file=sys.stderr, flush=True)
        try:
            QMessageBox.critical(None, "Unhandled Error", tb_text)
        except Exception:
            pass

    sys.excepthook = _hook


def _app_icon() -> QIcon:
    """Load multi-resolution app icon from assets/icons."""
    icon = QIcon()
    icons_dir = os.path.join(_ROOT, "assets", "icons")
    hicolor = os.path.join(icons_dir, "hicolor")
    for size in (16, 24, 32, 48, 64, 128, 256):
        path = os.path.join(hicolor, f"{size}x{size}", "apps", "se5editor.png")
        if os.path.isfile(path):
            icon.addFile(path)
    master = os.path.join(icons_dir, "se5editor.png")
    if os.path.isfile(master):
        icon.addFile(master)
    return icon


def main():
    QApplication.setApplicationName("Sniper Elite 5 Editor")
    QApplication.setOrganizationName("se5editor")
    QApplication.setDesktopFileName("se5editor")

    _install_excepthook()

    app = QApplication(sys.argv)
    app.setApplicationDisplayName("Sniper Elite 5 Editor")
    app_icon = _app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    apply_theme(app)

    window = MainWindow()
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
