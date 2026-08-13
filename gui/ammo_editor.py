"""Ammo/weapon damage editor panel.

Lists every entity in the asrpatch that has a Damage property and allows
editing damage-related stats (Damage, EffectiveRange, MuzzleVelocity,
DamageSpread, DamageDropoff, FireRate, AudibleRangeBase).

This is especially useful for weapons like the HS.22 (HDM) whose damage
is not exposed in the standard weapon/attachment tabs.
"""
from __future__ import annotations

from typing import Optional, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QComboBox, QGroupBox, QScrollArea,
    QPushButton, QMessageBox,
)

from gui.theme import (
    muted_style, TEXT_MUTED, SUCCESS, WARNING, ERROR,
)
from gui.weapon_editor import _apply_warning_style
from gui.display_names import format_entity_label
from asr import AsrFile

# ── Property definitions ──────────────────────────────────────────────────
# (display, hash_name, min, max, decimals, step, tooltip, category)

AMMO_FLOAT_PROPS = [
    # ── Damage ──
    ("Listed Damage", "Damage", 0, 100000, 6, 0.001,
     "Listed score — not infantry HP. 0 or 3× stock does not change "
     "how shots kill. Prefer Power × (DamageMod) on magazines.", "damage"),
    ("2nd Score / Spread", "DamageSpread", 0, 100000, 6, 0.001,
     "Second listed score (rifles 75–150) or a tiny cone term "
     "(Sjögren 0.025). Two encodings, not one unit.", "damage"),
    ("Drop-off / Alt. Score", "DamageDropoff", 0, 100000, 6, 0.001,
     "Alternate listed score on some bolt rifles (145–150) or a "
     "~1.0 fraction on others. Not kill HP.", "damage"),
    # ── Ballistics ──
    ("Effective Range", "EffectiveRange", 0, 100000, 3, 1,
     "Range contribution in metres. Not infantry HP.", "ballistics"),
    ("Muzzle Velocity", "MuzzleVelocity", 0, 100000, 3, 1,
     "Bullet speed (m/s). Higher = flatter trajectory, less lead needed.", "ballistics"),
    ("Fire Rate", "FireRate", 0, 10000, 3, 1,
     "Fire rate value (units vary by weapon type).", "ballistics"),
    ("RPM", "RPM", 0, 10000, 6, 0.001,
     "Rounds per minute multiplier.", "ballistics"),
    # ── Stealth ──
    ("Audible Range Base", "AudibleRangeBase", -1000, 10000, 6, 0.001,
     "Base distance at which the weapon can be heard. "
     "Negative values = quieter (suppressed).", "stealth"),
    ("Wind Drop", "WindDrop", 0, 100, 6, 0.001,
     "How much wind affects the bullet trajectory.", "stealth"),
]

AMMO_CATEGORIES = [
    ("damage", "Damage"),
    ("ballistics", "Ballistics"),
    ("stealth", "Stealth & Detection"),
]


class AmmoEditorPanel(QWidget):
    """Panel for editing damage and ballistics stats of any entity that has
    a Damage property.

    Unlike the weapon/attachment panels which use fixed entity lists, this
    panel dynamically discovers all entities with a Damage property when a
    file is loaded.
    """

    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.asr_file: Optional[AsrFile] = None
        self.current_entity: str = ""
        self.entity_names: List[str] = []
        self._spin_widgets = {}
        self._original_values = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Entity selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Weapon/Ammo:"))
        self.entity_combo = QComboBox()
        self.entity_combo.setMinimumWidth(350)
        self.entity_combo.currentIndexChanged.connect(
            lambda idx: self._on_entity_selected(self.entity_combo.itemData(idx))
        )
        selector_layout.addWidget(self.entity_combo)
        selector_layout.addStretch()

        self.reset_btn = QPushButton("Reset to Original")
        self.reset_btn.setToolTip(
            "Reset all properties of this item to their original values")
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

        # Dynamically discover all entities that have a Damage property
        self.entity_names = sorted(
            name for name, ent in asr_file.entities.items()
            if ent.get("Damage") is not None
        )

        for name in self.entity_names:
            self.entity_combo.addItem(format_entity_label(name), name)

        if self.entity_names:
            self.status_label.setText(
                f"Loaded {len(self.entity_names)} weapons with damage stats")
            self._on_entity_selected(
                self.entity_combo.itemData(self.entity_combo.currentIndex()))
        else:
            self.status_label.setText("No weapons with damage stats found")

    def _on_entity_selected(self, entity_name: str):
        if not self.asr_file or not entity_name:
            return

        # Remove stale widget references for the previously selected entity
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

        # Float properties grouped by category
        for cat_key, cat_label in AMMO_CATEGORIES:
            cat_props = [p for p in AMMO_FLOAT_PROPS if p[7] == cat_key]
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
            self, "Reset Weapon/Ammo",
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
        return self.entity_names
