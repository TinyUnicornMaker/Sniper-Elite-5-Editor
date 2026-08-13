"""Save Difficulty — patch Custom Difficulty tokens in campaign / profile saves.

Research / documentation panel only. Not wired into the main window.
Core token map and write helpers remain in ``gui.save_difficulty`` and
ENEMY_STATS.md for reference.
"""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QComboBox, QGroupBox, QPushButton, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QMessageBox, QSplitter, QFileDialog, QCheckBox,
)

from gui.theme import TEXT_MUTED, SUCCESS, ERROR, muted_style
from gui import save_difficulty as sd

_COMBO_MAX = 260


class SaveDifficultyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._profile_dir = ""
        self._slots: list[sd.SaveSlot] = []
        self._current: sd.SaveSlot | None = None
        self._combos: dict[str, QComboBox] = {}
        self._build_ui()
        self.reload()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        intro = QLabel(
            "Real Custom Difficulty lives in the save, not common.asr. "
            "This tab patches the 4-byte tokens we mapped from your Island "
            "session. Only two observed steps per slider — not the full "
            "in-game range. Quit the game before Apply or an autosave "
            "will overwrite the patch."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(muted_style())
        layout.addWidget(intro)

        path_row = QHBoxLayout()
        self.path_lab = QLabel("")
        self.path_lab.setStyleSheet(muted_style())
        self.path_lab.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        path_row.addWidget(self.path_lab, 1)
        browse = QPushButton("Profile folder…")
        browse.clicked.connect(self._browse)
        path_row.addWidget(browse)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.reload)
        path_row.addWidget(refresh)
        layout.addLayout(path_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Slot", "When", "Map"])
        self.tree.setMinimumWidth(280)
        self.tree.setUniformRowHeights(True)
        self.tree.setRootIsDecorated(False)
        hdr = self.tree.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tree.itemClicked.connect(self._on_item)
        splitter.addWidget(self.tree)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 4, 4, 4)
        self.title = QLabel("Select a save")
        self.title.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {TEXT_MUTED};")
        rl.addWidget(self.title)
        self.meta = QLabel("")
        self.meta.setWordWrap(True)
        self.meta.setStyleSheet(muted_style())
        rl.addWidget(self.meta)

        self.group = QGroupBox("Observed slider tokens")
        self.form = QFormLayout(self.group)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form.setFieldGrowthPolicy(
            self.form.FieldGrowthPolicy.FieldsStayAtSizeHint
        )
        for sl in sd.SLIDERS:
            box = QComboBox()
            box.setMinimumWidth(160)
            box.setMaximumWidth(_COMBO_MAX)
            box.setToolTip(sl.tip)
            lbl = QLabel(sl.label)
            lbl.setToolTip(sl.tip)
            self.form.addRow(lbl, box)
            self._combos[sl.key] = box
        rl.addWidget(self.group)

        self.also_profile = QCheckBox("Also write profile slot0")
        self.also_profile.setChecked(True)
        self.also_profile.setToolTip(
            "slot0 holds the live Custom Difficulty the menu shows. "
            "A campaign slot only snapshots what that save stored."
        )
        rl.addWidget(self.also_profile)

        btns = QHBoxLayout()
        self.deadly_btn = QPushButton("Fill deadliest known")
        self.deadly_btn.setToolTip(
            "Sets the combos to the hardest incoming-fire tokens we have: "
            "more vulnerable player, less regen, harder enemy combat. "
            "Leaves Enemy Resilience alone. Perceptiveness only goes as "
            "far as Normal — Increased is not mapped."
        )
        self.deadly_btn.clicked.connect(self._fill_deadly)
        btns.addWidget(self.deadly_btn)
        self.apply_btn = QPushButton("Apply to save")
        self.apply_btn.clicked.connect(self._apply)
        btns.addWidget(self.apply_btn)
        self.restore_btn = QPushButton("Restore backup")
        self.restore_btn.clicked.connect(self._restore)
        btns.addWidget(self.restore_btn)
        btns.addStretch()
        rl.addLayout(btns)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(muted_style())
        rl.addWidget(self.status)
        rl.addStretch()
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self._set_enabled(False)

    def _set_enabled(self, on: bool):
        for box in self._combos.values():
            box.setEnabled(on)
        self.apply_btn.setEnabled(on)
        self.deadly_btn.setEnabled(on)
        self.restore_btn.setEnabled(
            on and self._current is not None
            and os.path.isfile(sd.bak_path(self._current.path))
        )

    def _browse(self):
        start = self._profile_dir or sd.find_profile_dir() or os.path.expanduser("~")
        directory = QFileDialog.getExistingDirectory(
            self, "Select PC_ProfileSaves/<steamid> folder", start)
        if directory:
            self._profile_dir = directory
            self.reload()

    def reload(self):
        if not self._profile_dir:
            self._profile_dir = sd.find_profile_dir()
        self.tree.clear()
        self._slots = sd.list_slots(self._profile_dir) if self._profile_dir else []
        if not self._profile_dir:
            self.path_lab.setText("No SE5 profile folder found — browse to PC_ProfileSaves/<id>")
        else:
            self.path_lab.setText(self._profile_dir)
        for slot in self._slots:
            when = datetime.fromtimestamp(slot.mtime).strftime("%H:%M")
            kind = "Profile" if slot.kind == "profile" else slot.name
            map_s = slot.mission or ("—" if slot.table_off is None else "table")
            if slot.table_off is None:
                map_s = "no table"
            it = QTreeWidgetItem([kind, when, map_s])
            it.setData(0, Qt.ItemDataRole.UserRole, slot.path)
            if slot.table_off is None:
                it.setForeground(0, Qt.GlobalColor.gray)
                it.setForeground(2, Qt.GlobalColor.gray)
            self.tree.addTopLevelItem(it)
        self.status.setText(f"{len(self._slots)} slots")
        if self._current:
            path = self._current.path
            match = next((s for s in self._slots if s.path == path), None)
            if match:
                self._show(match)
            else:
                self._current = None
                self._set_enabled(False)

    def _on_item(self, item: QTreeWidgetItem, _col: int):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        slot = next((s for s in self._slots if s.path == path), None)
        if slot:
            self._show(slot)

    def _fill_combo(self, sl: sd.Slider, current: int | None):
        box = self._combos[sl.key]
        box.blockSignals(True)
        box.clear()
        tokens_in = {step.token for step in sl.steps}
        if current is not None and current not in tokens_in:
            box.addItem(f"Unmapped 0x{current:08X}", current)
        for step in sl.steps:
            box.addItem(step.label, step.token)
        if current is not None:
            idx = box.findData(current)
            if idx >= 0:
                box.setCurrentIndex(idx)
        box.blockSignals(False)

    def _show(self, slot: sd.SaveSlot):
        self._current = slot
        kind = "Profile" if slot.kind == "profile" else "Campaign"
        self.title.setText(f"{slot.name}  ·  {kind}")
        if slot.table_off is None:
            self.meta.setText(
                "No token table in this slot. slot1-style wrappers and "
                "empty autosaves cannot be patched."
            )
            for sl in sd.SLIDERS:
                self._fill_combo(sl, None)
            self._set_enabled(False)
            return
        when = datetime.fromtimestamp(slot.mtime).strftime("%Y-%m-%d %H:%M:%S")
        self.meta.setText(
            f"{slot.mission or 'Unknown map'}  ·  table @{slot.table_off}  ·  {when}"
        )
        for sl in sd.SLIDERS:
            self._fill_combo(sl, slot.tokens.get(sl.key))
        self._set_enabled(True)
        self.also_profile.setEnabled(slot.kind != "profile")

    def _wanted_from_combos(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for key, box in self._combos.items():
            token = box.currentData()
            if isinstance(token, int):
                out[key] = token
        return out

    def _fill_deadly(self):
        want = sd.deadly_tokens()
        for key, token in want.items():
            box = self._combos.get(key)
            if not box:
                continue
            idx = box.findData(token)
            if idx < 0:
                step = sd.step_for_token(sd.SLIDER_BY_KEY[key], token)
                box.addItem(step.label if step else f"0x{token:08X}", token)
                idx = box.findData(token)
            if idx >= 0:
                box.setCurrentIndex(idx)
        self.status.setText(
            "Combos set to the deadliest mapped incoming-fire tokens. "
            "Enemy Resilience unchanged. Apply to write."
        )

    def _apply(self):
        if not self._current or self._current.table_off is None:
            return
        if QMessageBox.question(
            self, "Write save?",
            "Quit the game first. This overwrites "
            f"<b>{os.path.basename(self._current.path)}</b> "
            "(a <code>.se5edit.bak</code> is kept on first write).",
        ) != QMessageBox.StandardButton.Yes:
            return
        wanted = self._wanted_from_combos()
        n, msg = sd.apply_tokens(self._current.path, wanted)
        extra = ""
        if n and self.also_profile.isChecked() and self._current.kind != "profile":
            prof = next(
                (s for s in self._slots
                 if s.kind == "profile" and s.table_off is not None
                 and s.name.lower() == "slot0.sav"),
                None,
            )
            if prof:
                pn, pmsg = sd.apply_tokens(prof.path, wanted)
                extra = f"  Profile: {pmsg}"
                n += pn
        self.reload()
        self.status.setText(msg + extra)
        self.status.setStyleSheet(
            f"color: {SUCCESS if n else ERROR}; font-size: 12px;")
        if not n:
            QMessageBox.information(self, "No Changes", msg + extra)

    def _restore(self):
        if not self._current:
            return
        ok, msg = sd.restore_save(self._current.path)
        self.reload()
        self.status.setText(msg)
        self.status.setStyleSheet(
            f"color: {SUCCESS if ok else ERROR}; font-size: 12px;")
