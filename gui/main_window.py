"""Main window for Sniper Elite 5 Editor — weapon browser + Sniper Tweaks."""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtGui import QAction, QKeySequence, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QDialog,
    QTabWidget, QPushButton, QLabel, QStatusBar, QToolBar,
    QFileDialog, QMessageBox, QApplication, QProgressBar,
    QDialogButtonBox, QScrollArea, QFrame,
)

from asr import AsrFile, find_sibling_base_asr
from gui.asr_backup import ensure_backup, restore_backup
from gui.theme import TEXT, ACCENT
from gui.weapon_browser import WeaponBrowserPanel
from gui.sniper_tweaks import SniperTweaksPanel

# Research / documentation modules (not wired into the UI):
#   gui.player_stats, gui.player_catalog, gui.player_io
#   gui.save_difficulty_panel, gui.save_difficulty
#   gui.enemy_modifiers, gui.enemy_catalog, gui.ai_tree

# First-launch limitations notice. Bump the key if the text must be
# shown again after a major honesty / capability change.
_LIMITATIONS_SETTINGS_KEY = "ui/limitations_ack_v1"

# Compact sections: (heading, list of short bullets)
_LIMITATIONS_SECTIONS: list[tuple[str, list[str]]] = [
    (
        "The short version",
        [
            "SE5 is opaque — many field labels do not match combat.",
            "This editor can still edit the patch; results are uneven.",
        ],
    ),
    (
        "Damage edits are unreliable",
        [
            "Kills come from hit location (head / heart / lungs).",
            "Custom Difficulty → Enemy Resilience also matters.",
            "Loaded ammo type matters (Soft Point, AP, Match, Non-Lethal…).",
            "“Damage” / “Power” fields often do little or nothing to kills.",
            "Treat damage-related numbers as experimental.",
        ],
    ),
    (
        "What usually still works",
        [
            "Magazine capacity on the magazine entity (real mag size).",
            "Scope Zoom Min / Max on many optics.",
            "Handling feel: recoil, sway, range, velocity, audible range.",
        ],
    ),
    (
        "Shared parts",
        [
            "Scopes, magazines, barrels, suppressors are shared records.",
            "One edit applies to every gun that can equip that part.",
        ],
    ),
    (
        "After you edit",
        [
            "Save the patch, then fully quit and relaunch SE5.",
            "Use Restore from Backup if something breaks.",
            "Reopen this notice anytime: Help → Limitations.",
        ],
    ),
]


class MainWindow(QMainWindow):
    """Main application window with weapon browser and Sniper Tweaks."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sniper Elite 5 Editor")
        self.setMinimumSize(1100, 700)

        self.asr_file: AsrFile | None = None
        self.current_path: str = ""
        self.backup_path: str = ""
        self._is_modified = False
        self._info_shown = False  # Show the ASR guide popup only once per session
        self._limitations_pending = False

        self._build_ui()
        self._build_menu()
        self._refresh_status()
        self._update_window_title()
        # First-launch honesty notice (once per install; Help can re-show)
        if not QSettings().value(_LIMITATIONS_SETTINGS_KEY, False, type=bool):
            self._limitations_pending = True

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.open_game_action = QAction("Open Game Folder…", self)
        self.open_game_action.setShortcut(QKeySequence("Ctrl+O"))
        self.open_game_action.setToolTip(
            "Select the Sniper Elite 5 install (or its misc/ folder). "
            "The editor finds common.asr.asrpatch and common.asr automatically."
        )
        self.open_game_action.triggered.connect(self._open_game_folder)
        toolbar.addAction(self.open_game_action)

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
        self.restore_action.setToolTip(
            "Restore the open weapon patch and/or common.asr from a "
            "validated .bak. A damaged backup is refused."
        )
        self.restore_action.triggered.connect(self._restore_backup)
        self.restore_action.setEnabled(False)
        toolbar.addAction(self.restore_action)

        toolbar.addSeparator()

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setMaximumWidth(200)
        self._progress.setVisible(False)
        toolbar.addWidget(self._progress)

        # Tab widget — weapon browser + sniper tweaks
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.weapon_browser = WeaponBrowserPanel()
        self.weapon_browser.modified.connect(self._on_modified)
        self.tabs.addTab(self.weapon_browser, "Weapon Browser")

        # Sniper Tweaks writes common.asr itself (glint). Do not mark the
        # weapon patch dirty from that path — re-encoding asrpatch on Save
        # after unrelated base-file work is a separate concern.
        self.sniper_tweaks_panel = SniperTweaksPanel()
        self.tabs.addTab(self.sniper_tweaks_panel, "Sniper Tweaks")

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.open_game_action)
        file_menu.addSeparator()
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
        limitations_action = QAction("Limitations…", self)
        limitations_action.setToolTip(
            "What this editor can and cannot change in Sniper Elite 5"
        )
        limitations_action.triggered.connect(
            lambda: self._show_limitations(mark_seen=True)
        )
        help_menu.addAction(limitations_action)
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def showEvent(self, event):
        super().showEvent(event)
        if self._limitations_pending:
            self._limitations_pending = False
            # After the window is on screen so the dialog centers correctly
            QTimer.singleShot(0, lambda: self._show_limitations(mark_seen=True))

    def _show_limitations(self, mark_seen: bool = False):
        """Honest capability notice for SE5 weapon editing."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Editor Limitations")
        dlg.setModal(True)
        # Fixed, readable size — no QMessageBox icon column waste
        dlg.setMinimumWidth(420)
        dlg.setMaximumWidth(480)
        dlg.setMinimumHeight(360)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        title = QLabel("What this editor can and cannot change")
        title_font = QFont(title.font())
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setWordWrap(True)
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 4, 0)
        body_layout.setSpacing(12)

        for heading, bullets in _LIMITATIONS_SECTIONS:
            head = QLabel(heading)
            hf = QFont(head.font())
            hf.setBold(True)
            head.setFont(hf)
            head.setStyleSheet(f"color: {ACCENT}; margin-top: 2px;")
            body_layout.addWidget(head)

            for line in bullets:
                row = QLabel(f"•  {line}")
                row.setWordWrap(True)
                row.setStyleSheet(f"color: {TEXT};")
                body_layout.addWidget(row)

        body_layout.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dlg.accept)
        root.addWidget(buttons)

        dlg.exec()
        if mark_seen:
            QSettings().setValue(_LIMITATIONS_SETTINGS_KEY, True)

    @staticmethod
    def _game_install_candidates() -> list[str]:
        """Likely Sniper Elite 5 install roots (and misc/ subfolders)."""
        return [
            # Linux Steam
            "~/.steam/debian-installation/steamapps/common/Sniper Elite 5",
            "~/.steam/steam/steamapps/common/Sniper Elite 5",
            "~/.local/share/Steam/steamapps/common/Sniper Elite 5",
            # Windows Steam
            r"C:\Program Files (x86)\Steam\steamapps\common\Sniper Elite 5",
            r"C:\Program Files\Steam\steamapps\common\Sniper Elite 5",
            os.path.expandvars(
                r"%ProgramFiles(x86)%\Steam\steamapps\common\Sniper Elite 5"
            ),
            os.path.expandvars(
                r"%ProgramFiles%\Steam\steamapps\common\Sniper Elite 5"
            ),
        ]

    @classmethod
    def _default_open_dir(cls) -> str:
        """Best-effort guess of SE5 install / misc for the folder dialog."""
        for c in cls._game_install_candidates():
            # expandvars for %ProgramFiles(x86)% etc. on Windows; expanduser
            # for ~/… on Linux. Harmless no-ops when already absolute.
            path = os.path.expanduser(os.path.expandvars(c))
            if path and os.path.isdir(path):
                return path
            misc = os.path.join(path, "misc") if path else ""
            if misc and os.path.isdir(misc):
                return misc
        return os.path.expanduser("~")

    @staticmethod
    def _find_asrpatch_in_dir(directory: str) -> str | None:
        """Locate common.asr.asrpatch under *directory* or directory/misc."""
        if not directory or not os.path.isdir(directory):
            return None

        # Direct hits (user picked misc/ or the install root)
        candidates = [
            os.path.join(directory, "common.asr.asrpatch"),
            os.path.join(directory, "misc", "common.asr.asrpatch"),
        ]
        # Also accept if they selected a parent that contains "Sniper Elite 5"
        parent_misc = os.path.join(directory, "Sniper Elite 5", "misc",
                                   "common.asr.asrpatch")
        candidates.append(parent_misc)

        for path in candidates:
            if os.path.isfile(path):
                return os.path.normpath(path)

        # Shallow scan: look one level deep for misc/common.asr.asrpatch
        try:
            for name in os.listdir(directory):
                sub = os.path.join(directory, name)
                if not os.path.isdir(sub):
                    continue
                hit = os.path.join(sub, "common.asr.asrpatch")
                if os.path.isfile(hit):
                    return os.path.normpath(hit)
                hit = os.path.join(sub, "misc", "common.asr.asrpatch")
                if os.path.isfile(hit):
                    return os.path.normpath(hit)
        except OSError:
            pass
        return None

    def _open_game_folder(self):
        """Let the user pick the game install; auto-find required ASR files."""
        if not self._info_shown:
            self._info_shown = True
            QMessageBox.information(
                self, "Open Game Folder",
                "Pick the <b>Sniper Elite 5</b> install (or its <b>misc</b> "
                "folder). The editor loads <code>common.asr.asrpatch</code> "
                "and merges <code>common.asr</code>. A <code>.bak</code> "
                "is created on first open.",
            )

        start = self._default_open_dir()
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Sniper Elite 5 install folder (or misc/)",
            start,
        )
        if not directory:
            return

        patch = self._find_asrpatch_in_dir(directory)
        if not patch:
            QMessageBox.warning(
                self, "Game Files Not Found",
                f"No <code>common.asr.asrpatch</code> under "
                f"<code>{directory}</code>. "
                "Pick the install folder or <code>misc/</code>.",
            )
            return

        base = find_sibling_base_asr(patch)
        extras = []
        extras.append(f"Patch: <code>{patch}</code>")
        if base:
            extras.append(f"Base: <code>{base}</code> (auto-merged)")
        else:
            extras.append(
                "Base: <i>common.asr not found next to the patch "
                "(stats will come from the patch only)</i>"
            )
        self.status_label.setText(f"Found {os.path.basename(patch)}")
        self._load_file(patch)

    def _load_file(self, path: str):
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # Indeterminate
        QApplication.processEvents()

        try:
            new_asr = AsrFile(path)

            # Snapshot only a healthy file. Never freeze a broken archive
            # as the restore source.
            if not path.endswith(".bak"):
                self.backup_path = path + ".bak"
                _ok, bak_msg = ensure_backup(path)
                if "created" in bak_msg:
                    self.status_label.setText(
                        f"Loaded {os.path.basename(path)} — backup created"
                    )
                else:
                    self.status_label.setText(
                        f"Loaded {os.path.basename(path)}"
                    )
            else:
                # Opening a .bak directly: the backup IS this file.
                self.backup_path = path
                self.status_label.setText(f"Loaded backup: {os.path.basename(path)}")

            # Commit the new file only after successful parse + backup
            self.asr_file = new_asr
            self.current_path = path

            # Merge base common.asr stats (fills properties the patch omits).
            # Weapon tables live in ZBB blocks 0–1; scan is ~0.5s.
            base_msg = ""
            base_path = find_sibling_base_asr(path)
            if base_path and new_asr._format in ("ZLB", "RAW"):
                try:
                    def _prog(frac, msg):
                        self.status_label.setText(msg)
                        QApplication.processEvents()

                    summary = new_asr.merge_base_stats(
                        base_path, max_blocks=2, progress_callback=_prog
                    )
                    base_msg = (
                        f" · base common.asr: {summary['base_entities']} entities, "
                        f"+{summary['merged_props']} filled props"
                    )
                except Exception as base_err:
                    base_msg = f" · base merge skipped: {base_err}"

            # Point attachment discovery at loadout loc + base common.asr
            try:
                from gui.weapon_mapping import set_game_data_paths
                from gui.attachment_compat import discover_game_paths
                paths = discover_game_paths(path)
                common_for_mesh = paths.get("common_asr") or base_path
                set_game_data_paths(
                    loadout_dir=paths.get("loadout"),
                    common_asr=common_for_mesh,
                )
            except Exception:
                pass

            # Update panels
            # If a prior block-0 rewrite left first_comp stale, later
            # blocks (AI / glint) are unreadable and the game black-screens.
            if base_path:
                self._offer_restore_broken_common_asr(base_path)

            self.weapon_browser.set_asr_file(self.asr_file)
            self.sniper_tweaks_panel.set_asr_file(self.asr_file, path)

            self._is_modified = False
            self._refresh_actions()
            self._update_window_title()

            # Preserve load status with base-merge note
            if base_msg:
                current = self.status_label.text()
                if "Loaded" in current:
                    self.status_label.setText(current + base_msg)

            # Warn when the wrong container was opened even if magic matched.
            base = os.path.basename(path).lower()
            n_ent = len(new_asr.entities)
            if base == "common.asr" or (
                base.endswith(".asr")
                and not base.endswith(".asrpatch")
                and not base.endswith(".bak")
            ):
                QMessageBox.warning(
                    self, "Wrong File?",
                    f"Loaded <b>{os.path.basename(path)}</b> ({n_ent} entities). "
                    "Edit <b>common.asr.asrpatch</b> in <code>misc/</code>, "
                    "not the base <code>common.asr</code>.",
                )
            elif getattr(new_asr, "_format", "") == "RAW" and n_ent > 0:
                QMessageBox.information(
                    self, "Uncompressed Patch",
                    f"Loaded {n_ent} entities from an uncompressed archive. "
                    "Save writes a normal AsuraZlb patch.",
                )
            elif n_ent == 0:
                QMessageBox.warning(
                    self, "No Weapon Data",
                    f"<b>{os.path.basename(path)}</b> has no known weapon "
                    "entities. Use <code>misc/common.asr.asrpatch</code>.",
                )

        except Exception as e:
            # Reset state so the UI doesn't show stale/partial data
            self.asr_file = None
            self.current_path = ""
            self.backup_path = ""
            self._is_modified = False
            self._refresh_actions()
            self._update_window_title()
            QMessageBox.critical(self, "Error Loading File", str(e))
            self.status_label.setText(f"Error: {e}")
        finally:
            self._progress.setVisible(False)

    def _offer_restore_broken_common_asr(self, base_path: str) -> None:
        """Detect a broken ZBB index and offer to restore common.asr.bak."""
        from gui.zbb_util import validate_zbb
        try:
            with open(base_path, "rb") as fh:
                raw = fh.read()
            err = validate_zbb(raw)
        except Exception as exc:
            err = str(exc)
        if not err:
            return
        bak = base_path + ".bak"
        if os.path.isfile(bak):
            reply = QMessageBox.question(
                self, "common.asr looks broken",
                "The archive index in common.asr is invalid "
                f"({err}).\n\nThis usually follows a bad block rewrite "
                "(historical acquire-timer / lethal experiments) and "
                "causes a black loading screen.\n\nRestore common.asr "
                "from its .bak now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                ok, msg = restore_backup(base_path)
                if ok:
                    QMessageBox.information(
                        self, "Restored", msg + " Restart the game.")
                else:
                    QMessageBox.critical(self, "Restore failed", msg)
        else:
            QMessageBox.warning(
                self, "common.asr looks broken",
                f"The archive index is invalid ({err}) and no "
                "common.asr.bak was found. Verify game files in Steam.",
            )

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

            # Save As: snapshot the destination only if no healthy bak
            # exists yet. Never replace a good bak with the just-saved
            # (already edited) file.
            if not path.endswith(".bak"):
                self.backup_path = path + ".bak"
                ensure_backup(path)

            self._refresh_actions()
            self._update_window_title()
            self.status_label.setText(f"Saved to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error Saving File", str(e))
            self.status_label.setText(f"Save error: {e}")
        finally:
            self._progress.setVisible(False)

    def _restore_backup(self):
        targets: list[tuple[str, str]] = []
        if self.current_path and not self.current_path.endswith(".bak"):
            targets.append((
                self.current_path,
                "Weapon patch (common.asr.asrpatch) — loadout / weapon edits",
            ))
        base = find_sibling_base_asr(self.current_path) if self.current_path else ""
        if base:
            targets.append((
                base,
                "Base archive (common.asr) — glint, player skills",
            ))
        existing = [(p, label) for p, label in targets if os.path.isfile(p + ".bak")]
        if not existing:
            QMessageBox.warning(
                self, "No backup",
                "No validated .bak next to the open patch or common.asr. "
                "After a Steam verify, reopen the game folder so a fresh "
                "snapshot can be taken before the next edit.",
            )
            return

        lines = [
            "Restore which snapshot? A damaged .bak is refused.",
            "",
        ]
        for path, label in existing:
            lines.append(f"• {os.path.basename(path)} — {label}")
        lines.append("")
        lines.append("Yes restores every listed file. No cancels.")
        reply = QMessageBox.question(
            self, "Restore Backup",
            "\n".join(lines),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        QApplication.processEvents()
        messages: list[str] = []
        failed = False
        try:
            for path, _label in existing:
                ok, msg = restore_backup(path)
                messages.append(msg)
                if not ok:
                    failed = True
        finally:
            self._progress.setVisible(False)

        summary = "\n".join(messages)
        if failed:
            QMessageBox.critical(self, "Restore failed", summary)
            self.status_label.setText("Restore failed")
            return

        reload_path = self.current_path or existing[0][0]
        self._load_file(reload_path)
        if self.asr_file:
            self.status_label.setText(f"Restored from backup to {reload_path}")
        QMessageBox.information(self, "Restored", summary)

    def _on_modified(self):
        # Dirty flag alone is not enough: Save / Ctrl+S are gated by the
        # QAction enabled state. Without _refresh_actions the status bar
        # and close dialog see "modified" while Save stays greyed out.
        self._is_modified = True
        self.status_label.setText("Modified — press Ctrl+S to save")
        self._refresh_actions()
        self._update_window_title()

    def _refresh_actions(self):
        """Enable/disable toolbar actions based on current state."""
        has_file = self.asr_file is not None
        self.save_action.setEnabled(has_file and self._is_modified)
        self.save_as_action.setEnabled(has_file)
        self.restore_action.setEnabled(
            has_file
            and self.backup_path
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
            "<p>Edits weapon / attachment stats in "
            "<code>common.asr.asrpatch</code> and scope glint in "
            "<code>common.asr</code>.</p>"
            "<p>Sniper Elite 5 is opaque: many “damage” fields do not "
            "control kills. See <b>Help → Limitations</b> for an honest "
            "list of what still works (capacity, magnification, shared "
            "parts).</p>"
            "<p>Back up game files first. RPM, recoil, and magazine size "
            "can break animations. Fully restart the game after Save.</p>",
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
                if self._is_modified:
                    event.ignore()
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()
