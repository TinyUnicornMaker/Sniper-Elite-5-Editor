"""Weapon editor panel — edit rifle/SMG/pistol stats in the ASR patch file.

Includes a green/yellow/red warning system that highlights values
which deviate significantly from the original (default) values.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QComboBox, QGroupBox,
    QScrollArea, QPushButton, QMessageBox,
)

from gui.theme import (
    TEXT_MUTED, SUCCESS, WARNING, ERROR,
    muted_style,
)
from gui.display_names import format_entity_label
from asr import AsrFile, ALL_WEAPON_ENTITIES, SCOPE_ENTITIES
from asr import (
    BARREL_ENTITIES, MAGAZINE_ENTITIES, IRONSIGHT_ENTITIES,
    SUPPRESSOR_ENTITIES, CHOKE_ENTITIES, OTHER_ATTACHMENT_ENTITIES,
)

# All non-weapon entity names (used to exclude attachments from weapon list)
NON_WEAPON_ENTITIES = set(
    SCOPE_ENTITIES + BARREL_ENTITIES + MAGAZINE_ENTITIES
    + IRONSIGHT_ENTITIES + SUPPRESSOR_ENTITIES + CHOKE_ENTITIES
    + OTHER_ATTACHMENT_ENTITIES
)

# ── Property definitions ─────────────────────────────────────────────────
# (display_name, hash_name, min, max, decimals, step, tooltip, category)
# category: "stats", "recoil", "aim", "sway"
# Properties exempt from color warning: MagazineCapacity

WEAPON_FLOAT_PROPS = [
    # ── Core stats ──
    ("Effective Range", "EffectiveRange", 0, 100000, 0, 10,
     "Stored reach in metres. Not infantry HP.", "stats"),
    ("Muzzle Velocity", "MuzzleVelocity", 0, 100000, 0, 10,
     "Bullet speed — higher means less lead needed (m/s)", "stats"),
    ("Damage", "Damage", 0, 100000, 1, 1,
     "Listed score — not infantry HP. Prefer Power × on the magazine.", "stats"),
    ("Damage Spread", "DamageSpread", 0, 100000, 1, 1,
     "Secondary damage/spread value. For shotguns, may represent pellet spread.", "stats"),
    ("Wind Drop", "WindDrop", 0, 100, 4, 0.001,
     "How much wind affects the bullet. Lower = less wind drift.", "stats"),
    ("RPM", "RPM", 1, 10000, 0, 1,
     "Rounds per minute. Higher = faster fire rate. "
     "WARNING: changing this can cause reload animation pauses.", "stats"),
    ("Fire Rate", "FireRate", 0, 10000, 1, 1,
     "Alternative fire rate value (used by some weapons instead of RPM).", "stats"),
    ("Damage Dropoff", "DamageDropoff", 0, 100000, 1, 1,
     "Distance at which damage begins to fall off.", "stats"),
    # ── Recoil ──
    ("Recoil (Vertical)", "Recoil1_Vertical", 0, 1000, 3, 0.1,
     "Vertical kick per shot. WARNING: values above ~3 can cause "
     "long delays between shots due to recoil recovery time.", "recoil"),
    ("Recoil (Horizontal)", "Recoil2_Horizontal", -1000, 1000, 3, 0.1,
     "Horizontal sway per shot.", "recoil"),
    ("Recoil Multiplier", "RecoilMult", 0, 1000, 3, 0.1,
     "Global multiplier applied to all recoil values.", "recoil"),
    ("Recoil Recovery Time", "RecoilRecoveryTime", -100, 1000, 2, 0.1,
     "Time for recoil to settle. Can be slightly negative (Sten = −0.6). "
     "WARNING: high values can cause reload animation bugs.", "recoil"),
    ("Recoil Reset Speed", "RecoilResetSpeed", 0, 10000, 3, 0.1,
     "How fast the crosshair resets after recoil.", "recoil"),
    # ── Aim / Scope ──
    ("Scope-In Speed", "ScopeInSpeed", 0.001, 100, 4, 0.01,
     "How fast the scope animation plays. "
     "M1903/SREM ~0.65 (fast), Kar98k/Mosin ~0.05 (slow).", "aim"),
    ("Aim Stability", "AimStability", 0, 1000, 3, 0.1,
     "How stable the aim is when holding the weapon.", "aim"),
    ("Scope Steady Time", "ScopeSteadyTime", 0, 1000, 3, 0.1,
     "How long the scope stays steady before sway begins.", "aim"),
    ("Hold Breath Duration", "HoldBreathDuration", 0, 1000, 3, 0.1,
     "How long you can hold breath to stabilize aim (seconds).", "aim"),
    # ── Sway ──
    ("Sway Amount", "SwayAmount", 0, 100, 3, 0.01,
     "How much the scope sways when aiming.", "sway"),
    ("Sway Recovery", "SwayRecovery", 0, 100, 3, 0.01,
     "How fast sway settles after moving.", "sway"),
    ("Sway Drift", "SwayDrift", 0, 100, 3, 0.01,
     "Continuous drift while aiming.", "sway"),
    ("Sway Decay", "SwayDecay", 0, 100, 3, 0.01,
     "How fast sway decays over time.", "sway"),
    ("Sway Per Shot", "SwayPerShot", 0, 1000, 3, 0.1,
     "Additional sway added per shot fired.", "sway"),
    ("Sway (Walking)", "SwayWalk", 0, 100, 3, 0.01,
     "Sway multiplier while walking.", "sway"),
    ("Sway (Crouching)", "SwayCrouch", 0, 100, 3, 0.1,
     "Sway multiplier while crouching.", "sway"),
    ("Sway (Prone)", "SwayProne", 0, 100, 3, 0.01,
     "Sway multiplier while prone.", "sway"),
]

WEAPON_INT_PROPS = [
    ("Magazine Capacity", "MagazineCapacity", 1, 100,
     "Number of rounds per magazine. WARNING: changing this "
     "may cause reload animation issues."),
]

# Properties exempt from the green/yellow/red warning system
NO_COLOR_PROPS = {"MagazineCapacity", "ZoomMin", "ZoomMax", "ZoomDefault"}

# Category labels and order
CATEGORIES = [
    ("stats", "Weapon Statistics"),
    ("recoil", "Recoil"),
    ("aim", "Aiming & Scope"),
    ("sway", "Sway"),
]


def _warning_color(current: float, original: float) -> str:
    """Return a color hint based on how far current is from original.

    Green: within 1.5x of original (0.667x to 1.5x)
    Yellow: 1.5x to 2x outside (0.5x to 0.667x, or 1.5x to 2x)
    Red: 2x+ outside (< 0.5x or > 2x)

    For original values near zero, use absolute tolerance instead.
    """
    if original == 0:
        return "green" if abs(current) < 0.01 else ("yellow" if abs(current) < 0.1 else "red")

    ratio = current / original
    if 0.667 <= ratio <= 1.5:
        return "green"
    elif 0.5 <= ratio <= 2.0:
        return "yellow"
    else:
        return "red"


def _apply_warning_style(spin: QDoubleSpinBox, current: float, original: float,
                         prop_name: str):
    """Apply green/yellow/red border color to a spinbox based on deviation."""
    if prop_name in NO_COLOR_PROPS:
        return

    level = _warning_color(current, original)
    if level == "green":
        color = SUCCESS
    elif level == "yellow":
        color = WARNING
    else:
        color = ERROR

    spin.setStyleSheet(
        f"QDoubleSpinBox, QSpinBox {{"
        f"  border: 2px solid {color};"
        f"  border-radius: 5px;"
        f"}}"
        f"QDoubleSpinBox:focus, QSpinBox:focus {{"
        f"  border: 2px solid {color};"
        f"}}"
    )


class WeaponEditorPanel(QWidget):
    """Panel for editing individual weapon stats."""

    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.asr_file: Optional[AsrFile] = None
        self.current_weapon: str = ""
        self._spin_widgets = {}  # (weapon, prop_name) -> widget
        self._original_values = {}  # (weapon, prop_name) -> original value
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Weapon selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Weapon:"))
        self.weapon_combo = QComboBox()
        self.weapon_combo.setMinimumWidth(300)
        self.weapon_combo.currentIndexChanged.connect(
            lambda idx: self._on_weapon_selected(self.weapon_combo.itemData(idx))
        )
        selector_layout.addWidget(self.weapon_combo)
        selector_layout.addStretch()

        self.reset_btn = QPushButton("Reset to Original")
        self.reset_btn.setToolTip("Reset all properties of this weapon to their original values")
        self.reset_btn.clicked.connect(self._reset_weapon)
        self.reset_btn.setEnabled(False)
        selector_layout.addWidget(self.reset_btn)

        layout.addLayout(selector_layout)

        # Legend for color warning system
        legend = QHBoxLayout()
        legend.addStretch()
        legend.addWidget(self._make_legend_dot(SUCCESS, "Normal"))
        legend.addWidget(self._make_legend_dot(WARNING, "1.5x deviation"))
        legend.addWidget(self._make_legend_dot(ERROR, "2x+ deviation"))
        layout.addLayout(legend)

        # Scroll area for property editors
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)

        # Status label
        self.status_label = QLabel("No file loaded")
        self.status_label.setStyleSheet(muted_style())
        layout.addWidget(self.status_label)

    def _make_legend_dot(self, color: str, text: str) -> QLabel:
        """Create a small colored dot + label for the legend."""
        label = QLabel(f"  {text}")
        label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px;"
            f"border-left: 8px solid {color};"
            f"padding-left: 4px;"
        )
        return label

    def set_asr_file(self, asr_file: AsrFile):
        self.asr_file = asr_file
        self.weapon_combo.blockSignals(True)
        self.weapon_combo.clear()
        self._original_values.clear()
        self._spin_widgets.clear()
        self._clear_content_layout()

        if not asr_file:
            self.weapon_combo.blockSignals(False)
            self.current_weapon = ""
            self.reset_btn.setEnabled(False)
            self.status_label.setText("No file loaded")
            return

        # Populate weapon combo with found entities
        found_weapons = []
        for name in ALL_WEAPON_ENTITIES:
            if name in asr_file.entities:
                found_weapons.append(name)
        # Also add any other entities that have weapon-like properties
        # but are NOT attachments (barrels, magazines, scopes, etc.)
        for name, entity in sorted(asr_file.entities.items()):
            if name not in found_weapons and name not in NON_WEAPON_ENTITIES:
                # Check if entity has Damage or RPM property
                if entity.get("Damage") or entity.get("RPM") or entity.get("FireRate"):
                    found_weapons.append(name)

        for w in sorted(found_weapons):
            self.weapon_combo.addItem(format_entity_label(w), w)
        self.weapon_combo.blockSignals(False)

        if found_weapons:
            self.status_label.setText(f"Loaded {len(found_weapons)} weapons")
            self._on_weapon_selected(self.weapon_combo.itemData(self.weapon_combo.currentIndex()))
        else:
            self.current_weapon = ""
            self.reset_btn.setEnabled(False)
            self.status_label.setText("No weapons found in file")

    def _clear_content_layout(self):
        """Remove and delete all widgets from the content layout."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_weapon_selected(self, weapon_name: str):
        if not self.asr_file or not weapon_name:
            return

        # Clean up _spin_widgets entries for the previous weapon so we don't
        # retain references to widgets that are about to be deleted.
        if self.current_weapon and self.current_weapon != weapon_name:
            stale_keys = [k for k in self._spin_widgets if k[0] == self.current_weapon]
            for k in stale_keys:
                del self._spin_widgets[k]

        self.current_weapon = weapon_name
        self.reset_btn.setEnabled(True)

        # Clear existing widgets
        self._clear_content_layout()

        entity = self.asr_file.entities.get(weapon_name)
        if not entity:
            label = QLabel(f"Entity '{weapon_name}' not found")
            label.setStyleSheet(muted_style())
            self.content_layout.addWidget(label)
            return

        # ── Group properties by category ──
        for cat_key, cat_label in CATEGORIES:
            cat_props = [p for p in WEAPON_FLOAT_PROPS if p[7] == cat_key]
            has_any = any(entity.get(p[1]) and entity.get(p[1]).is_float for p in cat_props)
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
                        lambda v, w=weapon_name, p=prop_name: self._on_value_changed(w, p, v)
                    )
                    self._spin_widgets[(weapon_name, prop_name)] = spin
                    self._original_values.setdefault((weapon_name, prop_name), prop.value)

                    # Apply initial warning color
                    _apply_warning_style(spin, prop.value, prop.value, prop_name)

                    label = QLabel(label_text)
                    label.setToolTip(tooltip)
                    form.addRow(label, spin)

            self.content_layout.addWidget(group)

        # ── Integer properties group (Magazine — no color warning) ──
        has_int = any(entity.get(p[1]) and entity.get(p[1]).is_int for p in WEAPON_INT_PROPS)
        if has_int:
            int_group = QGroupBox("Ammunition")
            int_form = QFormLayout(int_group)
            int_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

            for label_text, prop_name, vmin, vmax, tooltip in WEAPON_INT_PROPS:
                prop = entity.get(prop_name)
                if prop and prop.is_int:
                    spin = QSpinBox()
                    spin.setRange(vmin, vmax)
                    spin.setValue(prop.value)
                    spin.setToolTip(tooltip)
                    spin.valueChanged.connect(
                        lambda v, w=weapon_name, p=prop_name: self._on_value_changed(w, p, v)
                    )
                    self._spin_widgets[(weapon_name, prop_name)] = spin
                    self._original_values.setdefault((weapon_name, prop_name), prop.value)

                    label = QLabel(label_text)
                    label.setToolTip(tooltip)
                    int_form.addRow(label, spin)

            self.content_layout.addWidget(int_group)

        self.content_layout.addStretch()

    def _on_value_changed(self, weapon: str, prop_name: str, value):
        if not self.asr_file:
            return
        entity = self.asr_file.entities.get(weapon)
        if not entity:
            return
        prop = entity.get(prop_name)
        if not prop:
            return

        if prop.is_float:
            self.asr_file.set_float(weapon, prop_name, float(value))
        else:
            self.asr_file.set_int(weapon, prop_name, int(value))

        # Update warning color on the spinbox
        spin = self._spin_widgets.get((weapon, prop_name))
        if spin:
            original = self._original_values.get((weapon, prop_name), value)
            _apply_warning_style(spin, float(value), float(original), prop_name)

        self.modified.emit()

    def _reset_weapon(self):
        if not self.current_weapon or not self.asr_file:
            return
        reply = QMessageBox.question(
            self, "Reset Weapon",
            f"Reset all properties of {self.current_weapon} to their original values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        for (w, p), original in self._original_values.items():
            if w != self.current_weapon:
                continue
            if (w, p) in self._spin_widgets:
                widget = self._spin_widgets[(w, p)]
                widget.blockSignals(True)
                widget.setValue(original)
                widget.blockSignals(False)
                # Reset color to green (original = current)
                _apply_warning_style(widget, float(original), float(original), p)
            entity = self.asr_file.entities.get(w)
            if entity:
                prop = entity.get(p)
                if prop:
                    if prop.is_float:
                        self.asr_file.set_float(w, p, float(original))
                    else:
                        self.asr_file.set_int(w, p, int(original))

        self.modified.emit()

    def get_all_entity_names(self):
        """Build the list of all weapon entity names in the current file."""
        from asr import ALL_WEAPON_ENTITIES
        weapon_names = []
        for name in ALL_WEAPON_ENTITIES:
            if name in self.asr_file.entities:
                weapon_names.append(name)
        for name, entity in sorted(self.asr_file.entities.items()):
            if name not in weapon_names and name not in NON_WEAPON_ENTITIES:
                if entity.get("Damage") or entity.get("RPM") or entity.get("FireRate"):
                    weapon_names.append(name)
        return weapon_names
