#!/usr/bin/env python3
"""Sniper Elite 5 Editor — Desktop application for editing SE5 weapon/scope stats."""
import sys
import os

# In a PyInstaller bundle, sys._MEIPASS points to the _internal/ directory
# where data files are extracted.  When running from source, __file__'s
# directory is the project root.  Both resolve to the folder that contains
# assets/ and gui/.
_ROOT = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)

# Application identity — used for Windows taskbar grouping and Linux .desktop
APP_ID = "com.tinyunicornmaker.se5editor"
APP_NAME = "Sniper Elite 5 Editor"
from gui._version import APP_VERSION


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


def _set_windows_appusermodel_id():
    """Set the Windows AppUserModelID so the taskbar shows our icon.

    Without this, Windows groups the app under python.exe's identity and
    shows the default Python/PyInstaller icon in the taskbar instead of
    the window icon set via setWindowIcon().

    Must be called BEFORE QApplication is created.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def _install_linux_desktop_entry():
    """Install a .desktop file and hicolor icons for Linux taskbar integration.

    On X11, setWindowIcon() sets _NET_WM_ICON which works for older desktop
    environments.  But GNOME 46+ and Wayland compositors no longer read
    _NET_WM_ICON — they look up the app icon via the .desktop file and the
    freedesktop.org icon theme.  This function installs both so the custom
    icon appears in the taskbar/dash across all Linux DEs.

    Files are written to ~/.local/share/ (user-specific, no root needed).
    """
    if not sys.platform.startswith("linux"):
        return

    import shutil
    from pathlib import Path

    # Determine the executable path for the .desktop Exec= line
    if getattr(sys, "frozen", False):
        # PyInstaller bundle — use the actual executable
        exe_path = os.path.abspath(sys.executable)
    else:
        # Running from source — use the script path
        exe_path = os.path.abspath(__file__)

    home = Path.home()
    apps_dir = home / ".local" / "share" / "applications"
    apps_dir.mkdir(parents=True, exist_ok=True)
    desktop_path = apps_dir / f"{APP_ID}.desktop"

    # Install icons into the user hicolor theme
    icons_src = os.path.join(_ROOT, "assets", "icons", "hicolor")
    icons_dst_base = home / ".local" / "share" / "icons" / "hicolor"
    for size in (16, 24, 32, 48, 64, 128, 256):
        src = os.path.join(icons_src, f"{size}x{size}", "apps", "se5editor.png")
        if os.path.isfile(src):
            dst_dir = icons_dst_base / f"{size}x{size}" / "apps"
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst = dst_dir / f"{APP_ID}.png"
            try:
                if not dst.exists():
                    shutil.copy2(src, dst)
            except OSError:
                pass

    # Write the .desktop file (only if it doesn't exist or the exe path changed)
    desktop_content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        "Comment=Edit weapon, scope, and attachment stats in Sniper Elite 5\n"
        f"Exec={exe_path}\n"
        f"Icon={APP_ID}\n"
        "Terminal=false\n"
        "Categories=Game;Utility;\n"
        f"StartupWMClass={APP_ID}\n"
    )
    try:
        existing = ""
        if desktop_path.exists():
            existing = desktop_path.read_text()
        if existing != desktop_content:
            desktop_path.write_text(desktop_content)
            desktop_path.chmod(0o755)
    except OSError:
        pass


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
    # Windows: set AppUserModelID BEFORE creating QApplication
    _set_windows_appusermodel_id()

    # Linux: install .desktop file + icons for taskbar/dash integration
    _install_linux_desktop_entry()

    QApplication.setApplicationName(APP_NAME)
    QApplication.setOrganizationName("se5editor")
    QApplication.setDesktopFileName(APP_ID)
    QApplication.setApplicationVersion(APP_VERSION)

    _install_excepthook()

    app = QApplication(sys.argv)
    app.setApplicationDisplayName(APP_NAME)
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
