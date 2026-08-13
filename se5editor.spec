# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Sniper Elite 5 Editor.

Build a single-folder distribution with:

    pyinstaller se5editor.spec --noconfirm

The output is in dist/SniperElite5Editor/.
For a single-file binary, use --onefile but note that onefile mode has
slower startup (unpacks to temp dir on each run).

This spec is cross-platform: it works on both Windows and Linux.
The .ico icon is used on Windows; on Linux the PNG icons in
assets/icons/hicolor/ are used for the .desktop file integration.
"""

import os
import sys

block_cipher = None

# ── Data files to bundle ──────────────────────────────────────────────
datas = [
    ('assets/icons', 'assets/icons'),
    ('gui/display_names.py', 'gui'),
    ('gui/vanilla_defaults.json', 'gui'),
]

# ── Hidden imports (modules not auto-detected by PyInstaller) ─────────
hiddenimports = [
    # Core GUI modules (imported dynamically or via string-based imports)
    'gui.theme',
    'gui.main_window',
    'gui.weapon_browser',
    'gui.weapon_mapping',
    'gui.property_editor',
    'gui.sniper_tweaks',
    'gui.display_names',
    'gui.vanilla_defaults',
    'gui.asr_backup',
    'gui.zbb_util',
    'gui.deflate_patch',
    'gui.presets',
    # Legacy modules still imported by some code paths
    'gui.weapon_editor',
    'gui.scope_editor',
    'gui.attachment_editor',
    'gui.ammo_editor',
]

# ── Exclude unused Qt modules to reduce binary size ───────────────────
excludes = [
    'PySide6.Qt3D',
    'PySide6.QtCharts',
    'PySide6.QtDataVisualization',
    'PySide6.QtMultimedia',
    'PySide6.QtNetwork',
    'PySide6.QtOpenGL',
    'PySide6.QtQml',
    'PySide6.QtQuick',
    'PySide6.QtQuick3D',
    'PySide6.QtQuickWidgets',
    'PySide6.QtSql',
    'PySide6.QtTest',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtXml',
    # Other unused stdlib modules
    'tkinter',
    'unittest',
    'pydoc',
    'doctest',
]

a = Analysis(
    ['se5editor.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Icon: use .ico on Windows, .png on Linux ──────────────────────────
if sys.platform == 'win32':
    icon_path = os.path.join('assets', 'icons', 'se5editor.ico')
else:
    icon_path = os.path.join('assets', 'icons', 'se5editor.png')

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SniperElite5Editor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # GUI app — no console window
    icon=icon_path if os.path.isfile(icon_path) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        # Don't compress Qt plugins DLLs — can cause loading issues on Windows
        '*.dll',
        '*.pyd',
    ],
    name='SniperElite5Editor',
)
