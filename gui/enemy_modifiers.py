"""Enemy Modifiers — per-class list + AI-tree combat stats.

Research / documentation panel only. Not wired into the main window
(block-405 writes refuse / crash launch). Character classes
(GermanSniper1, GermanGrunt, …) are identity stubs; combat numbers live
on the AI behaviour tree in common.asr block 405. See ENEMY_STATS.md.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QGroupBox, QScrollArea, QPushButton,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QMessageBox, QSplitter,
)

from gui.theme import TEXT_MUTED, SUCCESS, WARNING, muted_style
from gui.enemy_catalog import (
    ENEMY_TYPES, CATEGORIES, ROLE_LABELS, ROLE_PARAMS,
    types_in_category, get_type, EnemyType,
)
from gui import ai_tree
from gui.ai_tree import AI_PARAM_BY_KEY


class EnemyModifiersPanel(QWidget):
    """Browse every enemy class and edit the AI-tree stats for its role."""

    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_asr_path: str = ""
        self._current: EnemyType | None = None
        self._spins: dict[str, QDoubleSpinBox] = {}
        self._loaded: dict[str, float] = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        intro = QLabel(
            "Combat numbers come from the AI role (Sniper Combat, Close Combat, …). "
            "Types that share a role share values. Apply is refused — block 405 "
            "writes crash launch. Threat / Look-At ranges are engage distances "
            "(15–30 m), not vision. There is no 500 m sight-range field; use "
            "in-game Custom Difficulty → Enemy Perceptiveness."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(muted_style())
        layout.addWidget(intro)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Enemy types")
        self.tree.setMinimumWidth(220)
        self.tree.setMaximumWidth(340)
        self.tree.setUniformRowHeights(True)
        self.tree.setIndentation(16)
        self.tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.itemClicked.connect(self._on_item)
        splitter.addWidget(self.tree)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(6, 4, 4, 4)

        self.title = QLabel("Select an enemy type")
        self.title.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {TEXT_MUTED};")
        right_l.addWidget(self.title)

        self.meta = QLabel("")
        self.meta.setWordWrap(True)
        self.meta.setStyleSheet(muted_style())
        right_l.addWidget(self.meta)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        form_host = QWidget()
        self.form_layout = QVBoxLayout(form_host)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_group = QGroupBox("Combat role stats")
        self.stats_form = QFormLayout(self.stats_group)
        self.stats_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form_layout.addWidget(self.stats_group)
        self.form_layout.addStretch()
        scroll.setWidget(form_host)
        right_l.addWidget(scroll, 1)

        btns = QHBoxLayout()
        self.apply_btn = QPushButton("Apply Role Stats")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setToolTip(
            "Write the values below into common.asr (this role, all types).")
        self.apply_btn.clicked.connect(self._apply_current)
        btns.addWidget(self.apply_btn)

        self.reset_role_btn = QPushButton("Reset Role to Defaults")
        self.reset_role_btn.setEnabled(False)
        self.reset_role_btn.clicked.connect(self._reset_current)
        btns.addWidget(self.reset_role_btn)
        btns.addStretch()
        right_l.addLayout(btns)

        self.status = QLabel("Open a game folder to load common.asr")
        self.status.setStyleSheet(muted_style())
        right_l.addWidget(self.status)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self._fill_tree()

    def showEvent(self, event):
        super().showEvent(event)
        if self.base_asr_path:
            self._reload_values()
            if self._current:
                self._rebuild_form(self._current)

    def _fill_tree(self):
        self.tree.clear()
        for cat in CATEGORIES:
            types = types_in_category(cat)
            if not types:
                continue
            parent = QTreeWidgetItem(self.tree, [f"{cat} ({len(types)})"])
            parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            parent.setExpanded(True)
            for t in types:
                child = QTreeWidgetItem(parent, [t.display])
                child.setData(0, Qt.ItemDataRole.UserRole, t.entity)
                child.setToolTip(0, t.blurb)

    def set_asr_file(self, _asr_file=None, asrpatch_path: str = ""):
        """Reuse the main-window hook; we only need the sibling common.asr."""
        self.base_asr_path = ""
        if asrpatch_path:
            import os
            cand = os.path.join(os.path.dirname(asrpatch_path), "common.asr")
            if os.path.isfile(cand):
                self.base_asr_path = cand
        self._reload_values()
        if self.base_asr_path:
            self.status.setText(
                f"AI tree: {len(self._loaded)} parameters from common.asr")
            self.status.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
        else:
            self.status.setText("common.asr not found — open the game folder")
            self.status.setStyleSheet(muted_style())
        if self._current:
            self._show_type(self._current)

    def _reload_values(self):
        self._loaded = {}
        if not self.base_asr_path:
            return
        try:
            block = ai_tree.load_block(self.base_asr_path)
            self._loaded = ai_tree.read_all_params(block)
        except Exception as exc:
            self.status.setText(f"Failed to read AI tree: {exc}")
            self.status.setStyleSheet(f"color: {WARNING};")

    def _on_item(self, item: QTreeWidgetItem, _col: int):
        entity = item.data(0, Qt.ItemDataRole.UserRole)
        if not entity:
            return
        t = get_type(entity)
        if t:
            self._show_type(t)

    def _show_type(self, t: EnemyType):
        self._current = t
        self.title.setText(t.display)
        role_name = ROLE_LABELS.get(t.role, t.role)
        share = [x.display for x in ENEMY_TYPES if x.role == t.role]
        share_txt = ", ".join(share)
        self.meta.setText(
            f"<code>{t.entity}</code> · {role_name}. {t.blurb} "
            f"Shared with: {share_txt}."
        )
        self._rebuild_form(t)

    def _rebuild_form(self, t: EnemyType):
        while self.stats_form.rowCount():
            self.stats_form.removeRow(0)
        self._spins.clear()

        keys = ROLE_PARAMS.get(t.role, ())
        if not keys:
            self.stats_form.addRow(QLabel("No editable AI-tree stats for this role."))
            self.apply_btn.setEnabled(False)
            self.reset_role_btn.setEnabled(False)
            return

        ready = bool(self.base_asr_path and self._loaded)
        for key in keys:
            p = AI_PARAM_BY_KEY.get(key)
            if not p:
                continue
            spin = QDoubleSpinBox()
            spin.setRange(p.vmin, p.vmax)
            spin.setDecimals(p.decimals)
            spin.setSingleStep(p.step)
            current = self._loaded.get(key, p.default)
            spin.setValue(current)
            spin.setToolTip(p.tooltip + f"\n\nDefault: {p.default:g}")
            spin.setEnabled(ready)
            lbl = QLabel(p.label)
            lbl.setToolTip(p.tooltip)
            self.stats_form.addRow(lbl, spin)
            self._spins[key] = spin

        self.apply_btn.setEnabled(ready)
        self.reset_role_btn.setEnabled(ready)

    def _apply_current(self):
        if not self.base_asr_path or not self._spins:
            return
        values = {k: s.value() for k, s in self._spins.items()}
        n, msg = ai_tree.apply_params(self.base_asr_path, values)
        self._reload_values()
        if self._current:
            self._rebuild_form(self._current)
        if n:
            self.status.setText(msg + "  Restart the game.")
            self.status.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
            self.modified.emit()
        else:
            QMessageBox.information(self, "No Changes", msg)
            self.status.setText(msg)

    def _reset_current(self):
        if not self._current or not self.base_asr_path:
            return
        keys = list(ROLE_PARAMS.get(self._current.role, ()))
        if not keys:
            return
        reply = QMessageBox.question(
            self, "Reset Role",
            f"Reset {ROLE_LABELS.get(self._current.role)} stats to "
            "shipped defaults? This affects every type on that role.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        n, msg = ai_tree.reset_params(self.base_asr_path, keys)
        self._reload_values()
        self._rebuild_form(self._current)
        self.status.setText(msg + ("  Restart the game." if n else ""))
        if n:
            self.modified.emit()

