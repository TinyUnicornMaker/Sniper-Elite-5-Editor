"""Main window for Sniper Elite 5 Editor — tabbed interface."""
from __future__ import annotations

import os
import sys
import shutil
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QStatusBar, QToolBar,
    QFileDialog, QMessageBox, QApplication, QProgressBar,
    QComboBox,
)

from asr import AsrFile
from gui.weapon_editor import WeaponEditorPanel
from gui.scope_editor import ScopeEditorPanel
from gui.attachment_editor import AttachmentEditorPanel
from gui.ammo_editor import AmmoEditorPanel
from asr import (
    BARREL_ENTITIES, MAGAZINE_ENTITIES, IRONSIGHT_ENTITIES,
    SUPPRESSOR_ENTITIES, CHOKE_ENTITIES, OTHER_ATTACHMENT_ENTITIES,
)


class MainWindow(QMainWindow):
    """Main application window with tabbed editor panels."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sniper Elite 5 Editor")
        self.setMinimumSize(1100, 700)

        self.asr_file: AsrFile | None = None
        self.current_path: str = ""
        self.backup_path: str = ""
        self._is_modified = False
        self._info_shown = False  # Show the ASR guide popup only once per session

        self._build_ui()
        self._build_menu()
        self._refresh_status()
        self._update_window_title()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.load_action = QAction("Open ASR File", self)
        self.load_action.setShortcut(QKeySequence("Ctrl+O"))
        self.load_action.triggered.connect(self._open_file)
        toolbar.addAction(self.load_action)

        toolbar.addSeparator()

        self.save_action = QAction("Save", self)
        self.save_action.setShortcut(QKeySequence("Ctrl+S"))
        self.save_action.triggered.connect(self._save_file)
        self.save_action.setEnabled(False)
        toolbar.addAction(self.save_action)

        self.save_as_action = QAction("Save As...", self)
        self.save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.save_as_action.triggered.connect(self._save_file_as)
        self.save_as_action.setEnabled(False)
        toolbar.addAction(self.save_as_action)

        toolbar.addSeparator()

        self.restore_action = QAction("Restore from Backup", self)
        self.restore_action.setToolTip("Restore the file from the .bak backup")
        self.restore_action.triggered.connect(self._restore_backup)
        self.restore_action.setEnabled(False)
        toolbar.addAction(self.restore_action)

        toolbar.addSeparator()

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setMaximumWidth(200)
        self._progress.setVisible(False)
        toolbar.addWidget(self._progress)

        # Global preset bar (above tabs)
        preset_bar = QHBoxLayout()
        preset_bar.addWidget(QLabel("Global Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(260)
        self.preset_combo.addItem("— Select Preset —", "")
        self.preset_combo.addItem("Default (Reset All to Original)", "default")
        self.preset_combo.addItem("Extended Strengths & Weaknesses", "extended_sw")
        self.preset_combo.setEnabled(False)
        preset_bar.addWidget(self.preset_combo)

        self.apply_all_btn = QPushButton("Apply to All & Save")
        self.apply_all_btn.setToolTip(
            "Apply the selected preset to ALL weapons, scopes, and attachments\n"
            "at once, then save the file automatically.\n\n"
            "Extended: exaggerates strengths (1.2x–1.5x) and slightly worsens\n"
            "weaknesses (10–20%) for every item.\n"
            "Default: resets ALL items to their original values."
        )
        self.apply_all_btn.setEnabled(False)
        self.apply_all_btn.clicked.connect(self._global_apply_preset)
        preset_bar.addWidget(self.apply_all_btn)

        preset_bar.addStretch()
        layout.addLayout(preset_bar)

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create panels
        self.weapon_panel = WeaponEditorPanel()
        self.weapon_panel.modified.connect(self._on_modified)
        self.tabs.addTab(self.weapon_panel, "Weapons")

        self.scope_panel = ScopeEditorPanel()
        self.scope_panel.modified.connect(self._on_modified)
        self.tabs.addTab(self.scope_panel, "Scopes")

        self.barrel_panel = AttachmentEditorPanel(BARREL_ENTITIES, "Barrel")
        self.barrel_panel.modified.connect(self._on_modified)
        self.tabs.addTab(self.barrel_panel, "Barrels")

        self.magazine_panel = AttachmentEditorPanel(MAGAZINE_ENTITIES, "Magazine")
        self.magazine_panel.modified.connect(self._on_modified)
        self.tabs.addTab(self.magazine_panel, "Magazines")

        self.suppressor_panel = AttachmentEditorPanel(SUPPRESSOR_ENTITIES, "Suppressor")
        self.suppressor_panel.modified.connect(self._on_modified)
        self.tabs.addTab(self.suppressor_panel, "Suppressors")

        self.ironsight_panel = AttachmentEditorPanel(IRONSIGHT_ENTITIES, "Ironsight")
        self.ironsight_panel.modified.connect(self._on_modified)
        self.tabs.addTab(self.ironsight_panel, "Ironsights")

        self.choke_panel = AttachmentEditorPanel(CHOKE_ENTITIES, "Choke")
        self.choke_panel.modified.connect(self._on_modified)
        self.tabs.addTab(self.choke_panel, "Chokes")

        self.other_panel = AttachmentEditorPanel(OTHER_ATTACHMENT_ENTITIES, "Attachment")
        self.other_panel.modified.connect(self._on_modified)
        self.tabs.addTab(self.other_panel, "Stocks & Grips")

        self.ammo_panel = AmmoEditorPanel()
        self.ammo_panel.modified.connect(self._on_modified)
        self.tabs.addTab(self.ammo_panel, "Ammo & Damage")

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.load_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.restore_action)
        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _open_file(self):
        # Show info popup explaining which files are needed (only once per session)
        if not self._info_shown:
            self._info_shown = True
            QMessageBox.information(
                self, "Which ASR File Do I Need?",
                "<h3>ASR File Guide</h3>"
                "<p>To edit weapon and scope stats, you need to open:</p>"
                "<ul>"
                "<li><b>common.asr.asrpatch</b> — Weapons, scopes, suppressors, "
                "magazines, barrels, and all gameplay stats.<br>"
                "<i>This is the only file the editor supports.</i></li>"
                "</ul>"
                "<p><b>Location:</b></p>"
                "<p><code>Sniper Elite 5/misc/common.asr.asrpatch</code></p>"
                "<p>The editor will automatically create a <b>.bak</b> backup "
                "the first time you open a file, so you can always restore "
                "the original.</p>"
                "<p><b>Note:</b> Do not open <code>common.asr</code> (the large "
                "489MB base file) — always use the <code>.asrpatch</code> file, "
                "which contains the override values the game loads on top.</p>",
            )

        # Default to the SE5 misc directory
        default_dir = os.path.expanduser(
            "~/.steam/debian-installation/steamapps/common/Sniper Elite 5/misc"
        )
        if not os.path.isdir(default_dir):
            default_dir = os.path.expanduser("~")

        path, _ = QFileDialog.getOpenFileName(
            self, "Open common.asr.asrpatch",
            default_dir,
            "ASR Patch Files (common.asr.asrpatch);;All Files (*)",
        )
        if not path:
            return

        self._load_file(path)

    def _load_file(self, path: str):
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # Indeterminate
        QApplication.processEvents()

        try:
            new_asr = AsrFile(path)

            # Create backup if it doesn't exist
            if not path.endswith(".bak"):
                self.backup_path = path + ".bak"
                if not os.path.exists(self.backup_path):
                    shutil.copy2(path, self.backup_path)
                    self.status_label.setText(
                        f"Loaded {os.path.basename(path)} — backup created"
                    )
                else:
                    self.status_label.setText(
                        f"Loaded {os.path.basename(path)}"
                    )
            else:
                # Opening a .bak directly: the backup IS this file.
                # backup_path points to itself so restore is correctly disabled.
                self.backup_path = path
                self.status_label.setText(f"Loaded backup: {os.path.basename(path)}")

            # Commit the new file only after successful parse + backup
            self.asr_file = new_asr
            self.current_path = path

            # Update panels
            self.weapon_panel.set_asr_file(self.asr_file)
            self.scope_panel.set_asr_file(self.asr_file)
            self.barrel_panel.set_asr_file(self.asr_file)
            self.magazine_panel.set_asr_file(self.asr_file)
            self.suppressor_panel.set_asr_file(self.asr_file)
            self.ironsight_panel.set_asr_file(self.asr_file)
            self.choke_panel.set_asr_file(self.asr_file)
            self.other_panel.set_asr_file(self.asr_file)
            self.ammo_panel.set_asr_file(self.asr_file)

            self._is_modified = False
            self.preset_combo.setEnabled(True)
            self.apply_all_btn.setEnabled(True)
            self._refresh_actions()
            self._update_window_title()

        except Exception as e:
            # Reset state so the UI doesn't show stale/partial data
            self.asr_file = None
            self.current_path = ""
            self.backup_path = ""
            self._is_modified = False
            self.preset_combo.setEnabled(False)
            self.apply_all_btn.setEnabled(False)
            self._refresh_actions()
            self._update_window_title()
            QMessageBox.critical(self, "Error Loading File", str(e))
            self.status_label.setText(f"Error: {e}")
        finally:
            self._progress.setVisible(False)

    def _save_file(self):
        if not self.asr_file or not self.current_path:
            return
        self._do_save(self.current_path)

    def _save_file_as(self):
        if not self.asr_file:
            return
        default_name = os.path.basename(self.current_path)
        if default_name.endswith(".bak"):
            default_name = default_name[:-4]

        path, _ = QFileDialog.getSaveFileName(
            self, "Save ASR File As",
            os.path.join(os.path.dirname(self.current_path), default_name),
            "ASR Files (*.asr *.asrpatch);;All Files (*)",
        )
        if not path:
            return
        self._do_save(path)

    def _do_save(self, path: str):
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        QApplication.processEvents()

        try:
            self.asr_file.save(path)
            self.current_path = path
            self._is_modified = False

            # Update backup_path for the new save location (Save As).
            # Create a fresh backup so Restore works for the new file too.
            if not path.endswith(".bak"):
                new_backup = path + ".bak"
                if new_backup != self.backup_path:
                    self.backup_path = new_backup
                    if not os.path.exists(new_backup):
                        shutil.copy2(path, new_backup)

            self._refresh_actions()
            self._update_window_title()
            self.status_label.setText(f"Saved to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error Saving File", str(e))
            self.status_label.setText(f"Save error: {e}")
        finally:
            self._progress.setVisible(False)

    def _restore_backup(self):
        if not self.backup_path or not os.path.exists(self.backup_path):
            return
        # The original (non-bak) file is the backup path with .bak stripped.
        # backup_path is always either "<original>.bak" or the .bak file itself.
        if self.backup_path.endswith(".bak"):
            original = self.backup_path[:-4]
        else:
            original = self.backup_path

        reply = QMessageBox.question(
            self, "Restore Backup",
            f"Restore {os.path.basename(original)} from backup?\n"
            f"This will discard all unsaved changes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        QApplication.processEvents()
        try:
            # Copy the backup over the original file, then reload it.
            shutil.copy2(self.backup_path, original)
        except Exception as e:
            QMessageBox.critical(self, "Error Restoring Backup", str(e))
            self.status_label.setText(f"Restore error: {e}")
            return
        finally:
            self._progress.setVisible(False)

        self._load_file(original)
        if self.asr_file:
            self.status_label.setText(f"Restored from backup to {original}")

    def _global_apply_preset(self):
        """Apply the selected preset to ALL panels at once, then save."""
        if not self.asr_file:
            return

        preset_id = self.preset_combo.currentData()
        if not preset_id:
            QMessageBox.information(
                self, "Select Preset",
                "Please select a preset from the dropdown first.",
            )
            return

        # Collect all panels and their entity names
        panels = [
            (self.weapon_panel, "Weapon"),
            (self.scope_panel, "Scope"),
            (self.barrel_panel, "Barrel"),
            (self.magazine_panel, "Magazine"),
            (self.suppressor_panel, "Suppressor"),
            (self.ironsight_panel, "Ironsight"),
            (self.choke_panel, "Choke"),
            (self.other_panel, "Attachment"),
            (self.ammo_panel, "Ammo"),
        ]

        # Count total entities for the confirmation message
        total_entities = 0
        for panel, _label in panels:
            names = panel.get_all_entity_names()
            total_entities += len(names)

        if preset_id == "default":
            preset_name = "Default (Reset All to Original)"
            confirm_msg = (
                f"Reset ALL {total_entities} items across all tabs to their\n"
                f"original values, then save?\n\n"
                f"This undoes every edit in every panel."
            )
        else:
            preset_name = "Extended Strengths & Weaknesses"
            confirm_msg = (
                f"Apply 'Extended Strengths & Weaknesses' to ALL {total_entities}\n"
                f"items across all tabs, then save?\n\n"
                f"This will exaggerate strengths (1.2x–1.5x) and slightly worsen\n"
                f"weaknesses (10–20%) for every weapon, scope, and attachment.\n"
                f"You can undo with 'Restore from Backup'."
            )

        reply = QMessageBox.question(
            self, "Apply Preset to All",
            f"Apply '{preset_name}'?\n\n{confirm_msg}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Show progress
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        QApplication.processEvents()

        try:
            from gui.presets import apply_preset_to_all, reset_all_entities

            total_changes = 0
            for panel, label in panels:
                entity_names = panel.get_all_entity_names()
                if not entity_names:
                    continue
                if preset_id == "default":
                    reset_all_entities(
                        panel, self.asr_file, entity_names,
                        panel_label=label,
                    )
                else:
                    # Suppress the per-panel confirmation dialog
                    from PySide6.QtWidgets import QMessageBox as _QMB
                    _orig = _QMB.question
                    _QMB.question = staticmethod(
                        lambda *a, **kw: _QMB.StandardButton.Yes
                    )
                    try:
                        apply_preset_to_all(
                            panel, self.asr_file, entity_names,
                            "extended_sw", panel_label=label,
                        )
                    finally:
                        _QMB.question = _orig
                total_changes += len(entity_names)

            # Auto-save
            self.asr_file.save(self.current_path)
            self._is_modified = False
            self._refresh_actions()
            self._update_window_title()
            self.status_label.setText(
                f"Applied '{preset_name}' to {total_changes} items "
                f"across all tabs — saved to {os.path.basename(self.current_path)}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error Applying Preset", str(e))
            self.status_label.setText(f"Preset error: {e}")
        finally:
            self._progress.setVisible(False)

    def _on_modified(self):
        self._is_modified = True
        self.status_label.setText("Modified — press Ctrl+S to save")
        self._update_window_title()

    def _refresh_actions(self):
        """Enable/disable toolbar actions based on current state."""
        has_file = self.asr_file is not None
        self.save_action.setEnabled(has_file)
        self.save_as_action.setEnabled(has_file)
        self.restore_action.setEnabled(
            has_file
            and bool(self.backup_path)
            and os.path.exists(self.backup_path)
            and self.backup_path != self.current_path
        )

    def _update_window_title(self):
        """Show the current file name and modified marker in the window title."""
        title = "Sniper Elite 5 Editor"
        if self.current_path:
            name = os.path.basename(self.current_path)
            marker = " *" if self._is_modified else ""
            title = f"{name}{marker} — {title}"
        self.setWindowTitle(title)

    def _refresh_status(self):
        if not self.asr_file:
            self.status_label.setText("No file loaded — press Ctrl+O to open")

    def _show_about(self):
        QMessageBox.information(
            self, "About Sniper Elite 5 Editor",
            "<h3>Sniper Elite 5 Editor</h3>"
            "<p>A tool for editing weapon, scope, and attachment stats "
            "in Sniper Elite 5 ASR/ASRpatch files.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Edit weapon damage, range, muzzle velocity, RPM</li>"
            "<li>Adjust recoil (vertical, horizontal, recovery)</li>"
            "<li>Modify scope-in speed and sway parameters</li>"
            "<li>Change magazine capacity</li>"
            "<li>Edit scope zoom levels (min/max)</li>"
            "<li>Edit barrels, magazines, suppressors, ironsights</li>"
            "<li>Edit chokes, stocks, grips, and muzzle brakes</li>"
            "</ul>"
            "<p><b>Warning:</b> Always back up your game files before modding. "
            "Some changes (RPM, recoil, magazine) can cause animation bugs.</p>",
        )

    def closeEvent(self, event):
        if self._is_modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_file()
                # If the save failed, _is_modified is still True — don't close.
                if self._is_modified:
                    event.ignore()
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()
