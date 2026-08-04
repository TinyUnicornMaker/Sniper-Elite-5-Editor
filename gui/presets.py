"""Shared preset logic for all editor panels.

Provides the "Extended Strengths & Weaknesses" and "Default" presets
that can be applied to any entity (weapon, scope, or attachment).

Each property is classified as "higher is better" or "lower is better".
For each entity, its values are compared to the median across all
entities of the same type. Strengths are exaggerated (1.2x-1.5x)
and weaknesses are slightly worsened (10-20%).
"""
from __future__ import annotations

import random
from typing import Optional

from PySide6.QtWidgets import (
    QLabel, QComboBox, QPushButton, QMessageBox,
)

from asr import AsrFile
from gui.weapon_editor import _apply_warning_style, NO_COLOR_PROPS

# ── Property classification ──────────────────────────────────────────────
# "higher_better" — high values are a strength (e.g. Damage, EffectiveRange)
# "lower_better"  — low values are a strength (e.g. Recoil, Sway, WindDrop)

HIGHER_BETTER_PROPS = {
    "EffectiveRange", "MuzzleVelocity", "Damage", "DamageDropoff",
    "RPM", "FireRate",
    "AimStability", "ScopeSteadyTime", "HoldBreathDuration", "ScopeInSpeed",
    "SwayDecay", "SwayRecovery",
    "RecoilResetSpeed",
    "ZoomMin", "ZoomMax", "ZoomMax2",
}

LOWER_BETTER_PROPS = {
    "WindDrop", "DamageSpread",
    "Recoil1_Vertical", "Recoil2_Horizontal", "RecoilMult",
    "RecoilRecoveryTime",
    "SwayAmount", "SwayDrift", "SwayPerShot",
    "SwayWalk", "SwayCrouch", "SwayProne",
    "AudibleRangeBase",
}

# Properties exempt from presets
# MagazineCapacity: modifying it on non-magazine entities breaks ammo pickup
# ZoomDefault: not shown in UI, no meaningful adjustment
PRESET_EXEMPT_PROPS = {"MagazineCapacity", "ZoomDefault"}


def compute_medians(asr_file: AsrFile, entity_names: list[str]) -> dict:
    """Compute median values for each property across the given entities.

    Includes both float and int properties (except exempt ones).
    Returns {prop_name: median_value}.
    """
    prop_vals = {}  # prop_name -> [values]
    for name in entity_names:
        entity = asr_file.entities.get(name)
        if not entity:
            continue
        for p in entity.properties:
            if p.name in PRESET_EXEMPT_PROPS:
                continue
            # Include both float and int properties
            prop_vals.setdefault(p.name, []).append(p.value)

    medians = {}
    for pname, vals in prop_vals.items():
        if len(vals) >= 3:  # Need enough samples for a meaningful median
            sorted_vals = sorted(vals)
            n = len(sorted_vals)
            medians[pname] = sorted_vals[n // 2]
    return medians


def generate_preset_values(asr_file: AsrFile, entity_name: str,
                           medians: dict, rng: random.Random,
                           visible_props: Optional[set] = None) -> dict:
    """Generate preset values for a single entity.

    For each property (float or int):
    - Compare the entity's value to the median.
    - If it's a strength: exaggerate by 1.2x-1.5x (random).
    - If it's a weakness: worsen by 10-20% (random).
    - Properties in INTEGER_PROPS are rounded to the nearest integer
      (minimum 1, since 0 would break the weapon).

    If visible_props is provided, only properties in that set are modified
    (this ensures the preset only affects properties shown in the panel).

    Returns {prop_name: new_value}.
    """
    entity = asr_file.entities.get(entity_name)
    if not entity:
        return {}

    result = {}
    for p in entity.properties:
        if p.name in PRESET_EXEMPT_PROPS:
            continue
        if p.name not in HIGHER_BETTER_PROPS and p.name not in LOWER_BETTER_PROPS:
            continue
        if visible_props is not None and p.name not in visible_props:
            continue

        median = medians.get(p.name)
        if median is None:
            continue

        orig = p.value
        if orig == 0:
            continue

        is_higher_better = p.name in HIGHER_BETTER_PROPS

        # Determine if this property is a strength or weakness
        if is_higher_better:
            is_strength = orig >= median
        else:
            is_strength = orig <= median

        if is_strength:
            # Exaggerate strength: 1.2x-1.5x
            factor = rng.uniform(1.2, 1.5)
            if is_higher_better:
                new_val = orig * factor
            else:
                new_val = orig / factor
        else:
            # Worsen weakness: 10-20% worse
            factor = rng.uniform(1.10, 1.20)
            if is_higher_better:
                new_val = orig / factor
            else:
                new_val = orig * factor

        result[p.name] = new_val

    return result


# ── Preset IDs ──
PRESET_DEFAULT = "default"
PRESET_EXTENDED_SW = "extended_sw"


def build_preset_selector(parent_layout) -> tuple:
    """Add a preset combo + buttons to a layout.

    Returns (preset_combo, apply_btn, apply_all_btn, reset_all_btn).
    """
    parent_layout.addWidget(QLabel("Preset:"))
    preset_combo = QComboBox()
    preset_combo.setMinimumWidth(220)
    preset_combo.addItem("— Select Preset —", "")
    preset_combo.addItem("Default (Reset to Original)", PRESET_DEFAULT)
    preset_combo.addItem("Extended Strengths & Weaknesses", PRESET_EXTENDED_SW)
    preset_combo.setEnabled(False)
    parent_layout.addWidget(preset_combo)

    apply_btn = QPushButton("Apply")
    apply_btn.setToolTip(
        "Apply the selected preset to the current item.\n"
        "Default: reset all stats to their original values.\n"
        "Extended Strengths & Weaknesses: exaggerates strengths (1.2x–1.5x)\n"
        "and slightly worsens weaknesses (10–20%)."
    )
    apply_btn.setEnabled(False)
    parent_layout.addWidget(apply_btn)

    apply_all_btn = QPushButton("Apply to All")
    apply_all_btn.setToolTip(
        "Apply the selected preset to ALL items in this panel at once.\n"
        "Extended: exaggerates strengths/worsens weaknesses for every item.\n"
        "Default: resets ALL items to their original values."
    )
    apply_all_btn.setEnabled(False)
    parent_layout.addWidget(apply_all_btn)

    reset_all_btn = QPushButton("Reset All")
    reset_all_btn.setToolTip(
        "Reset ALL items in this panel to their original values.\n"
        "This undoes all edits across every item, not just the current one."
    )
    reset_all_btn.setEnabled(False)
    parent_layout.addWidget(reset_all_btn)

    return preset_combo, apply_btn, apply_all_btn, reset_all_btn


def apply_preset_to_entity(panel, asr_file: AsrFile, entity_name: str,
                           all_entity_names: list[str],
                           preset_id: str, panel_label: str = "Item"):
    """Apply a preset to the current entity in a panel.

    The panel must have:
    - _spin_widgets: dict[(entity, prop)] -> widget
    - _original_values: dict[(entity, prop)] -> original value
    - modified: Signal
    - status_label: QLabel

    Returns True if the preset was applied, False if cancelled or no changes.
    """
    if not entity_name or not asr_file:
        return False

    if not preset_id:
        QMessageBox.information(
            panel, "Select Preset",
            "Please select a preset from the dropdown first.",
        )
        return False

    if preset_id == PRESET_DEFAULT:
        preset_name = "Default (Reset to Original)"
        confirm_msg = (
            f"Reset all properties of {entity_name} to their\n"
            f"original values?"
        )
    elif preset_id == PRESET_EXTENDED_SW:
        preset_name = "Extended Strengths & Weaknesses"
        confirm_msg = (
            f"This will modify the {panel_label.lower()}'s stats to exaggerate\n"
            f"its strengths (1.2x–1.5x) and slightly worsen its weaknesses\n"
            f"(10–20%). You can still undo with 'Reset to Original'."
        )
    else:
        return False

    reply = QMessageBox.question(
        panel, "Apply Preset",
        f"Apply '{preset_name}' to {entity_name}?\n\n{confirm_msg}",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return False

    # ── Default preset: reset all properties to original values ──
    if preset_id == PRESET_DEFAULT:
        count = 0
        for (e, p), original in panel._original_values.items():
            if e != entity_name:
                continue
            entity = asr_file.entities.get(e)
            if entity:
                prop = entity.get(p)
                if prop:
                    if prop.is_float:
                        asr_file.set_float(e, p, float(original))
                    else:
                        asr_file.set_int(e, p, int(original))
            spin = panel._spin_widgets.get((e, p))
            if spin:
                spin.blockSignals(True)
                spin.setValue(original)
                spin.blockSignals(False)
                _apply_warning_style(spin, float(original), float(original), p)
            count += 1
        panel.modified.emit()
        panel.status_label.setText(
            f"Reset {entity_name} to original values ({count} properties)"
        )
        return True

    # ── Extended Strengths & Weaknesses preset ──
    # Only modify properties that are visible (have spinboxes) in the panel
    visible_props = {p for (e, p) in panel._spin_widgets if e == entity_name}
    medians = compute_medians(asr_file, all_entity_names)
    rng = random.Random()  # Non-deterministic — different each apply
    new_values = generate_preset_values(
        asr_file, entity_name, medians, rng, visible_props=visible_props
    )

    if not new_values:
        QMessageBox.information(
            panel, "No Changes",
            f"No applicable properties found for {entity_name}.",
        )
        return False

    for prop_name, new_val in new_values.items():
        asr_file.set_float(entity_name, prop_name, new_val)
        spin = panel._spin_widgets.get((entity_name, prop_name))
        if spin:
            spin.blockSignals(True)
            spin.setValue(new_val)
            spin.blockSignals(False)
            original = panel._original_values.get(
                (entity_name, prop_name), new_val
            )
            _apply_warning_style(spin, float(new_val), float(original), prop_name)

    panel.modified.emit()
    panel.status_label.setText(
        f"Applied '{preset_name}' to {entity_name} "
        f"({len(new_values)} properties modified)"
    )
    return True


def _populate_original_values(panel, asr_file: AsrFile,
                              all_entity_names: list[str]) -> None:
    """Ensure _original_values has entries for every property of every entity.

    This is called before bulk operations (reset all / apply to all) so that
    'Reset to Original' works even for entities the user never clicked on.
    """
    for entity_name in all_entity_names:
        entity = asr_file.entities.get(entity_name)
        if not entity:
            continue
        for p in entity.properties:
            key = (entity_name, p.name)
            panel._original_values.setdefault(key, p.value)


def reset_all_entities(panel, asr_file: AsrFile,
                       all_entity_names: list[str],
                       panel_label: str = "Item") -> bool:
    """Reset ALL entities in the panel to their original values.

    Returns True if applied, False if cancelled.
    """
    if not asr_file or not all_entity_names:
        return False

    reply = QMessageBox.question(
        panel, "Reset All",
        f"Reset ALL {len(all_entity_names)} {panel_label.lower()}s "
        f"to their original values?\n\n"
        f"This undoes every edit across every {panel_label.lower()} in this panel.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return False

    _populate_original_values(panel, asr_file, all_entity_names)

    count = 0
    for entity_name in all_entity_names:
        entity = asr_file.entities.get(entity_name)
        if not entity:
            continue
        for p in entity.properties:
            key = (entity_name, p.name)
            original = panel._original_values.get(key)
            if original is None:
                continue
            if p.is_float:
                asr_file.set_float(entity_name, p.name, float(original))
            else:
                asr_file.set_int(entity_name, p.name, int(original))
            spin = panel._spin_widgets.get(key)
            if spin:
                spin.blockSignals(True)
                spin.setValue(original)
                spin.blockSignals(False)
                _apply_warning_style(spin, float(original), float(original), p.name)
            count += 1

    panel.modified.emit()
    panel.status_label.setText(
        f"Reset all {panel_label.lower()}s to original values "
        f"({count} properties across {len(all_entity_names)} entities)"
    )
    return True


def apply_preset_to_all(panel, asr_file: AsrFile,
                        all_entity_names: list[str],
                        preset_id: str,
                        panel_label: str = "Item") -> bool:
    """Apply a preset to ALL entities in the panel at once.

    For PRESET_DEFAULT, delegates to reset_all_entities.
    For PRESET_EXTENDED_SW, applies the extended preset to every entity.

    Returns True if applied, False if cancelled or no changes.
    """
    if not asr_file or not all_entity_names:
        return False

    if not preset_id:
        QMessageBox.information(
            panel, "Select Preset",
            "Please select a preset from the dropdown first.",
        )
        return False

    if preset_id == PRESET_DEFAULT:
        return reset_all_entities(
            panel, asr_file, all_entity_names, panel_label
        )

    if preset_id != PRESET_EXTENDED_SW:
        return False

    reply = QMessageBox.question(
        panel, "Apply to All",
        f"Apply 'Extended Strengths & Weaknesses' to ALL "
        f"{len(all_entity_names)} {panel_label.lower()}s?\n\n"
        f"This will exaggerate strengths (1.2x–1.5x) and slightly worsen "
        f"weaknesses (10–20%) for every {panel_label.lower()}.\n"
        f"You can undo with 'Reset All' or individual 'Reset to Original'.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return False

    # Store original values for ALL entities before modifying anything
    _populate_original_values(panel, asr_file, all_entity_names)

    medians = compute_medians(asr_file, all_entity_names)
    rng = random.Random()

    total_changes = 0
    for entity_name in all_entity_names:
        entity = asr_file.entities.get(entity_name)
        if not entity:
            continue

        # Use visible_props from spinboxes if the entity is currently
        # displayed; otherwise pass None to modify all applicable props.
        visible_props = {p for (e, p) in panel._spin_widgets if e == entity_name}
        if not visible_props:
            visible_props = None

        new_values = generate_preset_values(
            asr_file, entity_name, medians, rng, visible_props=visible_props
        )

        for prop_name, new_val in new_values.items():
            asr_file.set_float(entity_name, prop_name, new_val)
            spin = panel._spin_widgets.get((entity_name, prop_name))
            if spin:
                spin.blockSignals(True)
                spin.setValue(new_val)
                spin.blockSignals(False)
                original = panel._original_values.get(
                    (entity_name, prop_name), new_val
                )
                _apply_warning_style(spin, float(new_val), float(original), prop_name)
            total_changes += 1

    panel.modified.emit()
    panel.status_label.setText(
        f"Applied 'Extended' to all {panel_label.lower()}s "
        f"({total_changes} properties across {len(all_entity_names)} entities)"
    )
    return True
