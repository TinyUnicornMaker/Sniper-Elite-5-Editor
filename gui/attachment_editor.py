"""Attachment editor panel — generic editor for barrels, magazines, ironsights,
suppressors, chokes, stocks, grips, muzzle brakes, and other attachments.

A single reusable panel class that accepts a category configuration and
displays all editable stats for that attachment type with the
green/yellow/red warning system.
"""
from __future__ import annotations

from typing import Optional, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QComboBox, QGroupBox, QScrollArea,
    QPushButton, QMessageBox,
)

from gui.theme import (
    muted_style, TEXT_MUTED, SUCCESS, WARNING, ERROR,
)
from gui.weapon_editor import _apply_warning_style
from gui.display_names import format_entity_label
from asr import AsrFile

# ── Property definitions for attachments ──────────────────────────────────
# Same format as weapon editor: (display, hash_name, min, max, decimals, step, tooltip, category)

ATTACHMENT_FLOAT_PROPS = [
    # ── Core stats ──
    ("Effective Range", "EffectiveRange", 0, 100000, 0, 10,
     "Range contribution in metres. Not infantry HP.", "stats"),
    ("Muzzle Velocity", "MuzzleVelocity", 0, 100000, 0, 10,
     "Bullet speed (m/s)", "stats"),
    ("Damage", "Damage", 0, 100000, 1, 1,
     "Listed score — not infantry HP. Prefer Power × (DamageMod).", "stats"),
    ("Damage Spread", "DamageSpread", 0, 100000, 1, 1,
     "Secondary damage/spread value.", "stats"),
    ("Wind Drop", "WindDrop", 0, 100, 4, 0.001,
     "How much wind affects the bullet.", "stats"),
    ("RPM", "RPM", 1, 10000, 0, 1,
     "Rounds per minute.", "stats"),
    ("Fire Rate", "FireRate", 0, 10000, 1, 1,
     "Alternative fire rate value.", "stats"),
    ("Damage Dropoff", "DamageDropoff", 0, 100000, 1, 1,
     "Distance at which damage begins to fall off.", "stats"),
    ("Audible Range Base", "AudibleRangeBase", 0, 10000, 1, 1,
     "Base distance at which the weapon can be heard.", "stats"),
    # ── Recoil ──
    ("Recoil (Vertical)", "Recoil1_Vertical", 0, 1000, 3, 0.1,
     "Vertical kick per shot.", "recoil"),
    ("Recoil (Horizontal)", "Recoil2_Horizontal", -1000, 1000, 3, 0.1,
     "Horizontal sway per shot.", "recoil"),
    ("Recoil Multiplier", "RecoilMult", 0, 1000, 3, 0.1,
     "Global multiplier applied to all recoil values.", "recoil"),
    ("Recoil Recovery Time", "RecoilRecoveryTime", 0, 1000, 2, 0.1,
     "Time for recoil to settle.", "recoil"),
    ("Recoil Reset Speed", "RecoilResetSpeed", 0, 10000, 3, 0.1,
     "How fast the crosshair resets after recoil.", "recoil"),
    # ── Aim / Scope ──
    ("Scope-In Speed", "ScopeInSpeed", 0.001, 100, 4, 0.01,
     "How fast the scope animation plays.", "aim"),
    ("Aim Stability", "AimStability", 0, 1000, 3, 0.1,
     "How stable the aim is.", "aim"),
    ("Scope Steady Time", "ScopeSteadyTime", 0, 1000, 3, 0.1,
     "How long the scope stays steady.", "aim"),
    ("Hold Breath Duration", "HoldBreathDuration", 0, 1000, 3, 0.1,
     "Hold breath duration (seconds).", "aim"),
    ("Zoom Minimum", "ZoomMin", 1.0, 1000.0, 1, 0.5,
     "Minimum zoom level.", "aim"),
    ("Zoom Maximum", "ZoomMax", 1.0, 1000.0, 1, 0.5,
     "Maximum zoom level.", "aim"),
    # ── Sway ──
    ("Sway Amount", "SwayAmount", 0, 100, 3, 0.01,
     "How much the scope sways.", "sway"),
    ("Sway Recovery", "SwayRecovery", 0, 100, 3, 0.01,
     "How fast sway settles.", "sway"),
    ("Sway Drift", "SwayDrift", 0, 100, 3, 0.01,
     "Continuous drift while aiming.", "sway"),
    ("Sway Decay", "SwayDecay", 0, 100, 3, 0.01,
     "How fast sway decays.", "sway"),
    ("Sway Per Shot", "SwayPerShot", 0, 1000, 3, 0.1,
     "Additional sway per shot.", "sway"),
    ("Sway (Walking)", "SwayWalk", 0, 100, 3, 0.01,
     "Sway multiplier while walking.", "sway"),
    ("Sway (Crouching)", "SwayCrouch", 0, 100, 3, 0.1,
     "Sway multiplier while crouching.", "sway"),
    ("Sway (Prone)", "SwayProne", 0, 100, 3, 0.01,
     "Sway multiplier while prone.", "sway"),
]

ATTACHMENT_INT_PROPS = [
    ("Magazine Capacity", "MagazineCapacity", 1, 1000,
     "Number of rounds per magazine."),
]

ATTACHMENT_CATEGORIES = [
    ("stats", "Statistics"),
    ("recoil", "Recoil"),
    ("aim", "Aiming & Zoom"),
    ("sway", "Sway"),
]


class AttachmentEditorPanel(QWidget):
    """Generic panel for editing attachment stats.

    Pass in a list of entity names and a panel title to create a tab
    for any attachment type (barrels, magazines, suppressors, etc.).
    """

    modified = Signal()

    def __init__(self, entity_names: List[str], panel_label: str,
                 parent=None):
        super().__init__(parent)
        self.entity_names = entity_names
        self.panel_label = panel_label
        self.asr_file: Optional[AsrFile] = None
        self.current_entity: str = ""
        self._spin_widgets = {}
        self._original_values = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Entity selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel(f"{self.panel_label}:"))
        self.entity_combo = QComboBox()
        self.entity_combo.setMinimumWidth(350)
        self.entity_combo.currentIndexChanged.connect(
            lambda idx: self._on_entity_selected(self.entity_combo.itemData(idx))
        )
        selector_layout.addWidget(self.entity_combo)
        selector_layout.addStretch()

        self.reset_btn = QPushButton("Reset to Original")
        self.reset_btn.setToolTip("Reset all properties of this item to their original values")
        self.reset_btn.clicked.connect(self._reset_entity)
        self.reset_btn.setEnabled(False)
        selector_layout.addWidget(self.reset_btn)

        layout.addLayout(selector_layout)

        # Legend
        legend = QHBoxLayout()
        legend.addStretch()
        legend.addWidget(self._make_legend_dot(SUCCESS, "Normal"))
        legend.addWidget(self._make_legend_dot(WARNING, "1.5x deviation"))
        legend.addWidget(self._make_legend_dot(ERROR, "2x+ deviation"))
        layout.addLayout(legend)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)

        self.status_label = QLabel("No file loaded")
        self.status_label.setStyleSheet(muted_style())
        layout.addWidget(self.status_label)

    def _make_legend_dot(self, color: str, text: str) -> QLabel:
        label = QLabel(f"  {text}")
        label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px;"
            f"border-left: 8px solid {color};"
            f"padding-left: 4px;"
        )
        return label

    def set_asr_file(self, asr_file: AsrFile):
        self.asr_file = asr_file
        self.entity_combo.clear()
        self._spin_widgets.clear()
        self._original_values.clear()

        if not asr_file:
            self.status_label.setText("No file loaded")
            return

        found = [n for n in self.entity_names if n in asr_file.entities]
        # Sort alphabetically, but strip common prefixes for readability
        for name in sorted(found):
            self.entity_combo.addItem(format_entity_label(name), name)

        if found:
            self.status_label.setText(f"Loaded {len(found)} {self.panel_label.lower()}")
            self._on_entity_selected(self.entity_combo.itemData(self.entity_combo.currentIndex()))
        else:
            self.status_label.setText(f"No {self.panel_label.lower()} found in file")

    def _on_entity_selected(self, entity_name: str):
        if not self.asr_file or not entity_name:
            return

        # Remove stale widget references for the previously selected entity.
        # The widgets are about to be deleted via deleteLater(), so keeping
        # them in _spin_widgets would leave dangling pointers.  We keep
        # _original_values so that reset still knows the true original.
        old_entity = self.current_entity
        if old_entity and old_entity != entity_name:
            for key in [k for k in self._spin_widgets if k[0] == old_entity]:
                del self._spin_widgets[key]

        self.current_entity = entity_name
        self.reset_btn.setEnabled(True)

        # Clear existing
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entity = self.asr_file.entities.get(entity_name)
        if not entity:
            label = QLabel(f"Entity '{entity_name}' not found")
            label.setStyleSheet(muted_style())
            self.content_layout.addWidget(label)
            return

        # ── Float properties grouped by category ──
        for cat_key, cat_label in ATTACHMENT_CATEGORIES:
            cat_props = [p for p in ATTACHMENT_FLOAT_PROPS if p[7] == cat_key]
            has_any = any(entity.get(p[1]) and entity.get(p[1]).is_float
                         for p in cat_props)
            if not has_any:
                continue

            group = QGroupBox(cat_label)
            form = QFormLayout(group)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

            for label_text, prop_name, vmin, vmax, decimals, step, tooltip, _cat in cat_props:
                prop = entity.get(prop_name)
                if prop and prop.is_float:
                    spin = QDoubleSpinBox()
                    spin.setRange(vmin, vmax)
                    spin.setDecimals(decimals)
                    spin.setSingleStep(step)
                    spin.setValue(prop.value)
                    spin.setToolTip(tooltip)
                    spin.valueChanged.connect(
                        lambda v, e=entity_name, p=prop_name: self._on_value_changed(e, p, v)
                    )
                    self._spin_widgets[(entity_name, prop_name)] = spin
                    self._original_values.setdefault(
                        (entity_name, prop_name), prop.value)

                    _apply_warning_style(spin, prop.value, prop.value, prop_name)

                    label = QLabel(label_text)
                    label.setToolTip(tooltip)
                    form.addRow(label, spin)

            self.content_layout.addWidget(group)

        # ── Integer properties (Magazine Capacity) ──
        has_int = any(entity.get(p[1]) and entity.get(p[1]).is_int
                      for p in ATTACHMENT_INT_PROPS)
        if has_int:
            int_group = QGroupBox("Ammunition")
            int_form = QFormLayout(int_group)
            int_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

            for label_text, prop_name, vmin, vmax, tooltip in ATTACHMENT_INT_PROPS:
                prop = entity.get(prop_name)
                if prop and prop.is_int:
                    spin = QSpinBox()
                    spin.setRange(vmin, vmax)
                    spin.setValue(prop.value)
                    spin.setToolTip(tooltip)
                    spin.valueChanged.connect(
                        lambda v, e=entity_name, p=prop_name: self._on_value_changed(e, p, v)
                    )
                    self._spin_widgets[(entity_name, prop_name)] = spin
                    self._original_values.setdefault(
                        (entity_name, prop_name), prop.value)

                    label = QLabel(label_text)
                    label.setToolTip(tooltip)
                    int_form.addRow(label, spin)

            self.content_layout.addWidget(int_group)

        self.content_layout.addStretch()

    def _on_value_changed(self, entity_name: str, prop_name: str, value):
        if not self.asr_file:
            return
        entity = self.asr_file.entities.get(entity_name)
        if not entity:
            return
        prop = entity.get(prop_name)
        if not prop:
            return

        if prop.is_float:
            self.asr_file.set_float(entity_name, prop_name, float(value))
        else:
            self.asr_file.set_int(entity_name, prop_name, int(value))

        spin = self._spin_widgets.get((entity_name, prop_name))
        if spin:
            original = self._original_values.get((entity_name, prop_name), value)
            _apply_warning_style(spin, float(value), float(original), prop_name)

        self.modified.emit()

    def _reset_entity(self):
        if not self.current_entity or not self.asr_file:
            return
        reply = QMessageBox.question(
            self, f"Reset {self.panel_label}",
            f"Reset all properties of {self.current_entity} to their original values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        for (e, p), original in self._original_values.items():
            if e != self.current_entity:
                continue
            if (e, p) in self._spin_widgets:
                widget = self._spin_widgets[(e, p)]
                widget.blockSignals(True)
                widget.setValue(original)
                widget.blockSignals(False)
                _apply_warning_style(widget, float(original), float(original), p)
            entity = self.asr_file.entities.get(e)
            if entity:
                prop = entity.get(p)
                if prop:
                    if prop.is_float:
                        self.asr_file.set_float(e, p, float(original))
                    else:
                        self.asr_file.set_int(e, p, int(original))

        self.modified.emit()

    def get_all_entity_names(self):
        """Build the list of all entity names for this panel in the file."""
        return [n for n in self.entity_names
                if n in self.asr_file.entities]
