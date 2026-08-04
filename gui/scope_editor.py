"""Scope editor panel — edit scope zoom and aim stats.

Includes the green/yellow/red warning system for non-zoom properties.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QComboBox, QGroupBox, QScrollArea,
    QPushButton, QMessageBox,
)

from gui.theme import (
    muted_style, TEXT_MUTED, SUCCESS, WARNING, ERROR,
)
from gui.display_names import format_entity_label
from asr import AsrFile, SCOPE_ENTITIES
from asr import (
    BARREL_ENTITIES, MAGAZINE_ENTITIES, IRONSIGHT_ENTITIES,
    SUPPRESSOR_ENTITIES, CHOKE_ENTITIES, OTHER_ATTACHMENT_ENTITIES,
)
from gui.weapon_editor import _apply_warning_style

# All non-scope entity names (used to exclude attachments from scope list)
NON_SCOPE_ENTITIES = set(
    BARREL_ENTITIES + MAGAZINE_ENTITIES + IRONSIGHT_ENTITIES
    + SUPPRESSOR_ENTITIES + CHOKE_ENTITIES + OTHER_ATTACHMENT_ENTITIES
)

# Scope-specific float properties
# (display_name, hash_name, min, max, decimals, step, tooltip, category)
SCOPE_FLOAT_PROPS = [
    # ── Zoom (no color warning) ──
    ("Zoom Minimum", "ZoomMin", 1.0, 1000.0, 1, 0.5,
     "Minimum zoom level when using the scroll wheel. "
     "Fixed-zoom scopes only have this value.", "zoom"),
    ("Zoom Maximum", "ZoomMax", 1.0, 1000.0, 1, 0.5,
     "Maximum zoom level. Fixed-zoom scopes do not have this property.", "zoom"),
    ("Zoom Max 2", "ZoomMax2", 1.0, 1000.0, 1, 0.5,
     "Secondary zoom level used by some scopes (A1, A2, M1913) "
     "that don't have a regular ZoomMax. This is the 'second zoom "
     "setting' visible in-game.", "zoom"),
    # ── Aim ──
    ("Scope-In Speed", "ScopeInSpeed", 0.001, 100, 4, 0.01,
     "How fast the scope animation plays.", "aim"),
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

SCOPE_CATEGORIES = [
    ("zoom", "Magnification"),
    ("aim", "Aiming"),
    ("sway", "Sway"),
]


class ScopeEditorPanel(QWidget):
    """Panel for editing scope magnification and aim stats."""

    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.asr_file: Optional[AsrFile] = None
        self.current_scope: str = ""
        self._spin_widgets = {}
        self._original_values = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Scope selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Scope:"))
        self.scope_combo = QComboBox()
        self.scope_combo.setMinimumWidth(300)
        self.scope_combo.currentIndexChanged.connect(
            lambda idx: self._on_scope_selected(self.scope_combo.itemData(idx))
        )
        selector_layout.addWidget(self.scope_combo)
        selector_layout.addStretch()

        self.reset_btn = QPushButton("Reset to Original")
        self.reset_btn.setToolTip("Reset all properties of this scope to their original values")
        self.reset_btn.clicked.connect(self._reset_scope)
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
        self.scope_combo.clear()
        self._spin_widgets.clear()
        self._original_values.clear()

        if not asr_file:
            self.status_label.setText("No file loaded")
            return

        found_scopes = []
        for name in SCOPE_ENTITIES:
            if name in asr_file.entities:
                found_scopes.append(name)
        # Also add any entities with ZoomMin property
        # but exclude attachments (barrels, magazines, etc.)
        for name, entity in sorted(asr_file.entities.items()):
            if name not in found_scopes and name not in NON_SCOPE_ENTITIES:
                if entity.get("ZoomMin"):
                    found_scopes.append(name)

        for s in sorted(found_scopes):
            self.scope_combo.addItem(format_entity_label(s), s)

        if found_scopes:
            self.status_label.setText(f"Loaded {len(found_scopes)} scopes")
            self._on_scope_selected(self.scope_combo.itemData(self.scope_combo.currentIndex()))
        else:
            self.status_label.setText("No scopes found in file")

    def _on_scope_selected(self, scope_name: str):
        if not self.asr_file or not scope_name:
            return

        # Remove stale widget references for the previously selected scope.
        # The widgets are about to be deleted via deleteLater(), so keeping
        # them in _spin_widgets would leave dangling pointers.  We keep
        # _original_values so that reset still knows the true original.
        old_scope = self.current_scope
        if old_scope and old_scope != scope_name:
            for key in [k for k in self._spin_widgets if k[0] == old_scope]:
                del self._spin_widgets[key]

        self.current_scope = scope_name
        self.reset_btn.setEnabled(True)

        # Clear existing
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entity = self.asr_file.entities.get(scope_name)
        if not entity:
            label = QLabel(f"Entity '{scope_name}' not found")
            label.setStyleSheet(muted_style())
            self.content_layout.addWidget(label)
            return

        # Group by category
        for cat_key, cat_label in SCOPE_CATEGORIES:
            cat_props = [p for p in SCOPE_FLOAT_PROPS if p[7] == cat_key]
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
                        lambda v, s=scope_name, p=prop_name: self._on_value_changed(s, p, v)
                    )
                    self._spin_widgets[(scope_name, prop_name)] = spin
                    self._original_values.setdefault((scope_name, prop_name), prop.value)

                    # Apply initial warning color
                    _apply_warning_style(spin, prop.value, prop.value, prop_name)

                    label = QLabel(label_text)
                    label.setToolTip(tooltip)
                    form.addRow(label, spin)

            self.content_layout.addWidget(group)

        self.content_layout.addStretch()

    def _on_value_changed(self, scope: str, prop_name: str, value):
        if not self.asr_file:
            return
        self.asr_file.set_float(scope, prop_name, float(value))

        # Update warning color
        spin = self._spin_widgets.get((scope, prop_name))
        if spin:
            original = self._original_values.get((scope, prop_name), value)
            _apply_warning_style(spin, float(value), float(original), prop_name)

        self.modified.emit()

    def _reset_scope(self):
        if not self.current_scope or not self.asr_file:
            return
        reply = QMessageBox.question(
            self, "Reset Scope",
            f"Reset all properties of {self.current_scope} to their original values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        for (s, p), original in self._original_values.items():
            if s != self.current_scope:
                continue
            if (s, p) in self._spin_widgets:
                widget = self._spin_widgets[(s, p)]
                widget.blockSignals(True)
                widget.setValue(original)
                widget.blockSignals(False)
                _apply_warning_style(widget, float(original), float(original), p)
            self.asr_file.set_float(s, p, float(original))

        self.modified.emit()

    def get_all_entity_names(self):
        """Build the list of all scope entity names in the current file."""
        scope_names = []
        for name in SCOPE_ENTITIES:
            if name in self.asr_file.entities:
                scope_names.append(name)
        for name, entity in sorted(self.asr_file.entities.items()):
            if name not in scope_names and name not in NON_SCOPE_ENTITIES:
                if entity.get("ZoomMin"):
                    scope_names.append(name)
        return scope_names
