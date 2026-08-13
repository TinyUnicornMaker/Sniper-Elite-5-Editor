"""Player Stats — difficulty presets + skill magnitudes.

Research / documentation panel only. Not wired into the main window
(block-0 perk writes crash launch; real Custom Difficulty lives in
saves — see ``gui.save_difficulty``). Kept so the catalog and UI notes
remain readable.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QComboBox, QGroupBox, QScrollArea, QPushButton,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QMessageBox, QSplitter,
)

from gui.theme import TEXT_MUTED, TEXT_DIM, SUCCESS, ERROR, muted_style
from gui.player_catalog import (
    DIFF_SLIDERS, DIFFICULTY_PRESETS, DIFFICULTY_ORDER,
    SLIDER_STEPS, REGEN_STEPS, PLAYER_SKILLS, SKILL_CATEGORIES,
    skills_in, resilience_scale, MIN_SKILL_FLOAT,
)
from gui import player_io
from gui.property_editor import _pct_change, _SPIN_MAX_WIDTH, _SPIN_MIN_WIDTH

_COMBO_MAX = 180


class PlayerStatsPanel(QWidget):
    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_asr_path: str = ""
        self._mode: str = ""  # "diff:Cadet" or "skill:Health Boost 1"
        self._diff_combos: dict[str, QComboBox] = {}
        self._skill_spin: QDoubleSpinBox | None = None
        self._skill_values: dict[str, float] = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        intro = QLabel(
            "Perk floats in common.asr (Health Boost, Toughened, …). "
            "Apply is refused — block 0 writes crash launch. "
            "The real Custom Difficulty sliders live in the campaign / "
            "profile save. Use the Save Difficulty tab to patch those."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(muted_style())
        layout.addWidget(intro)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Player stats")
        self.tree.setMinimumWidth(220)
        self.tree.setMaximumWidth(340)
        self.tree.setUniformRowHeights(True)
        self.tree.setIndentation(16)
        self.tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.itemClicked.connect(self._on_item)
        splitter.addWidget(self.tree)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 4, 4, 4)
        self.title = QLabel("Select a difficulty or skill")
        self.title.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {TEXT_MUTED};")
        rl.addWidget(self.title)
        self.meta = QLabel("")
        self.meta.setWordWrap(True)
        self.meta.setStyleSheet(muted_style())
        rl.addWidget(self.meta)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        self.form_box = QVBoxLayout(host)
        self.form_box.setContentsMargins(0, 0, 0, 0)
        self.group = QGroupBox("Values")
        self.form = QFormLayout(self.group)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
        )
        self._delta_labels: dict[str, QLabel] = {}
        self.form_box.addWidget(self.group)
        self.form_box.addStretch()
        scroll.setWidget(host)
        rl.addWidget(scroll, 1)

        btns = QHBoxLayout()
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply)
        btns.addWidget(self.apply_btn)
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self._reset)
        btns.addWidget(self.reset_btn)
        btns.addStretch()
        rl.addLayout(btns)

        self.status = QLabel("Open a game folder to load common.asr")
        self.status.setStyleSheet(muted_style())
        rl.addWidget(self.status)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self._fill_tree()

    def _fill_tree(self):
        self.tree.clear()
        diffs = QTreeWidgetItem(self.tree, ["Difficulty"])
        diffs.setFlags(diffs.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        diffs.setExpanded(True)
        for name in DIFFICULTY_ORDER:
            it = QTreeWidgetItem(diffs, [name])
            it.setData(0, Qt.ItemDataRole.UserRole, f"diff:{name}")
        for cat in SKILL_CATEGORIES:
            parent = QTreeWidgetItem(self.tree, [cat])
            parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            parent.setExpanded(True)
            for s in skills_in(cat):
                it = QTreeWidgetItem(parent, [s.display])
                it.setData(0, Qt.ItemDataRole.UserRole, f"skill:{s.name}")
                it.setToolTip(0, s.tip)

    def set_asr_file(self, _asr=None, asrpatch_path: str = ""):
        import os
        self.base_asr_path = ""
        if asrpatch_path:
            cand = os.path.join(os.path.dirname(asrpatch_path), "common.asr")
            if os.path.isfile(cand):
                self.base_asr_path = cand
        self._reload_skills()
        if self.base_asr_path:
            self.status.setText(
                f"Loaded {len(self._skill_values)} skill values from common.asr")
            self.status.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
        else:
            self.status.setText("common.asr not found")
            self.status.setStyleSheet(muted_style())
        if self._mode:
            self._show(self._mode)

    def showEvent(self, event):
        super().showEvent(event)
        if self.base_asr_path:
            self._reload_skills()

    def _reload_skills(self):
        self._skill_values = {}
        if not self.base_asr_path:
            return
        try:
            block = player_io.load_skill_block(self.base_asr_path)
            self._skill_values = player_io.read_skills(block)
        except Exception as exc:
            self.status.setText(f"Read failed: {exc}")

    def _on_item(self, item: QTreeWidgetItem, _col: int):
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if key:
            self._show(key)

    def _clear_form(self):
        while self.form.rowCount():
            self.form.removeRow(0)
        self._diff_combos.clear()
        self._skill_spin = None
        self._delta_labels.clear()

    def _pct_widget(self, key: str, current, default, tip: str) -> QLabel:
        lab = QLabel()
        lab.setMinimumWidth(52)
        text, color = _pct_change(current, default)
        lab.setText(text)
        lab.setStyleSheet(f"color: {color}; font-size: 11px;")
        lab.setToolTip(tip)
        self._delta_labels[key] = lab
        return lab

    def _field_row(self, field: QWidget, pct: QLabel) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(field, 0)
        h.addWidget(pct, 0)
        h.addStretch(1)
        return row

    def _show(self, mode: str):
        self._mode = mode
        self._clear_form()
        ready = bool(self.base_asr_path)
        if mode.startswith("diff:"):
            name = mode[5:]
            self.title.setText(name)
            self.meta.setText(
                f"{name} starts from the stock preset. Change any slider "
                "individually, including Player Resilience, then Apply. "
                "Only the defensive perk floats are written. "
                f"Greatly Reduced scale = {resilience_scale(0):g} "
                f"(floor {MIN_SKILL_FLOAT:g}), not 0."
            )
            preset = DIFFICULTY_PRESETS[name]
            for sl in DIFF_SLIDERS:
                box = QComboBox()
                steps = REGEN_STEPS if sl.kind == "regen" else SLIDER_STEPS
                box.addItems(list(steps))
                box.setCurrentIndex(preset[sl.key])
                box.setMinimumWidth(120)
                box.setMaximumWidth(_COMBO_MAX)
                box.setToolTip(sl.tip)
                box.currentIndexChanged.connect(
                    lambda _i, k=sl.key, d=preset[sl.key], b=box, s=sl:
                    self._update_step_pct(k, b.currentIndex(), d, s)
                )
                lbl = QLabel(sl.label)
                lbl.setToolTip(sl.tip)
                stock = preset[sl.key]
                pct_tip = (
                    f"Vs {name} stock ({steps[stock]}). "
                    "You can pick any step; it is not locked to this difficulty."
                )
                pct = self._pct_widget(sl.key, 0, 0, pct_tip)
                self._update_step_pct(sl.key, box.currentIndex(), stock, sl)
                self.form.addRow(lbl, self._field_row(box, pct))
                self._diff_combos[sl.key] = box
            self.apply_btn.setEnabled(ready)
            self.reset_btn.setEnabled(ready)
        elif mode.startswith("skill:"):
            name = mode[6:]
            skill = next((s for s in PLAYER_SKILLS if s.name == name), None)
            if not skill:
                return
            self.title.setText(skill.display)
            self.meta.setText(skill.tip)
            spin = QDoubleSpinBox()
            spin.setRange(skill.vmin, skill.vmax)
            spin.setDecimals(2)
            spin.setSingleStep(1.0)
            spin.setMinimumWidth(_SPIN_MIN_WIDTH)
            spin.setMaximumWidth(_SPIN_MAX_WIDTH)
            spin.setAlignment(Qt.AlignmentFlag.AlignRight)
            current = self._skill_values.get(skill.name, skill.default)
            spin.setValue(current)
            spin.setEnabled(ready)
            spin.setToolTip(
                f"{skill.tip}\n\nDefault: {skill.default:g}\n"
                f"Internal: {skill.name}"
            )
            spin.valueChanged.connect(
                lambda v, k=skill.name, d=skill.default:
                self._update_skill_pct(k, v, d)
            )
            lbl = QLabel(skill.display)
            lbl.setToolTip(spin.toolTip())
            pct = self._pct_widget(
                skill.name, current, skill.default,
                f"Change vs game default ({skill.default:g}).",
            )
            self.form.addRow(lbl, self._field_row(spin, pct))
            self._skill_spin = spin
            self.apply_btn.setEnabled(ready)
            self.reset_btn.setEnabled(ready)

    def _update_skill_pct(self, key: str, current, default) -> None:
        lab = self._delta_labels.get(key)
        if not lab:
            return
        text, color = _pct_change(current, default)
        lab.setText(text)
        lab.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _update_step_pct(self, key: str, current: int, stock: int, sl) -> None:
        lab = self._delta_labels.get(key)
        if not lab:
            return
        # Treat slider steps as 0–4 so ±1 step = ±25% of the full scale.
        text, color = _pct_change(float(current), float(stock) if stock else None)
        if stock == 0:
            if current == 0:
                text, color = "0%", TEXT_MUTED
            else:
                text, color = f"+{current} step", SUCCESS
        lab.setText(text)
        lab.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _apply(self):
        if not self.base_asr_path or not self._mode:
            return
        if self._mode.startswith("diff:"):
            step = self._diff_combos["player_resilience"].currentIndex()
            n, msg = player_io.apply_resilience_step(self.base_asr_path, step)
        else:
            name = self._mode[6:]
            if not self._skill_spin:
                return
            n, msg = player_io.apply_skills(
                self.base_asr_path, {name: self._skill_spin.value()})
        self._reload_skills()
        self.status.setText(msg + ("  Restart the game." if n else ""))
        if n:
            self.status.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
            self.modified.emit()
        else:
            QMessageBox.information(self, "No Changes", msg)

    def _reset(self):
        if not self._mode or not self.base_asr_path:
            return
        if self._mode.startswith("diff:"):
            name = self._mode[5:]
            preset = DIFFICULTY_PRESETS[name]
            for k, box in self._diff_combos.items():
                box.setCurrentIndex(preset[k])
            self._apply()
        else:
            name = self._mode[6:]
            skill = next((s for s in PLAYER_SKILLS if s.name == name), None)
            if not skill:
                return
            n, msg = player_io.apply_skills(
                self.base_asr_path, {skill.name: skill.default})
            self._reload_skills()
            if self._skill_spin:
                self._skill_spin.setValue(
                    self._skill_values.get(skill.name, skill.default))
            self.status.setText(msg)
            if n:
                self.modified.emit()

