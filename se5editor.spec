# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Sniper Elite 5 Editor.

Build a Windows binary with:

    pyinstaller se5editor.spec

The output is a single-folder distribution in dist/SniperElite5Editor/.
For a single-file exe, change COLLECT to EXE with --onefile, but note
that onefile mode has slower startup (unpacks to temp dir on each run).
"""

import os

block_cipher = None

a = Analysis(
    ['se5editor.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Bundle the icon assets and display names with the executable
        ('assets/icons', 'assets/icons'),
        ('gui/display_names.py', 'gui'),
    ],
    hiddenimports=[
        'gui.theme',
        'gui.main_window',
        'gui.weapon_editor',
        'gui.scope_editor',
        'gui.attachment_editor',
        'gui.ammo_editor',
        'gui.display_names',
        'gui.presets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unused Qt modules to reduce binary size
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
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    icon=os.path.join('assets', 'icons', 'se5editor.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SniperElite5Editor',
)
