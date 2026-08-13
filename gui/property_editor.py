"""Reusable property editor widget for entity stats.

A generic widget that displays and edits the properties of a single ASR
entity, grouped by category, with the green/yellow/red warning system.

This is the building block for the weapon browser's per-weapon tabs.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QGroupBox, QScrollArea, QPushButton,
)

from gui.theme import TEXT_MUTED, TEXT_DIM, SUCCESS, WARNING, ERROR, muted_style
from gui.display_names import format_entity_label
from gui.vanilla_defaults import get_default
from asr import AsrFile, prop_label

# Keep value spinboxes compact — they should not grow with the window.
_SPIN_MAX_WIDTH = 130
_SPIN_MIN_WIDTH = 100


def _size_spin(spin: QDoubleSpinBox | QSpinBox) -> None:
    """Fixed-ish width so modifier columns stay readable and short."""
    spin.setMinimumWidth(_SPIN_MIN_WIDTH)
    spin.setMaximumWidth(_SPIN_MAX_WIDTH)
    spin.setAlignment(Qt.AlignmentFlag.AlignRight)


# Hover help for attachment / generic modifier properties (All Modifiers box
# and any prop not covered by the curated PROPERTY_SETS lists).
MODIFIER_TOOLTIPS: dict[str, str] = {
    "DamageMod": (
        "Power multiplier — this is the field the gunsmith means by "
        "“Boosts / Reduces Damage” and “Overpressure Power”.\n"
        "1.0 = no change. Overpressure magazines/barrels store ~1.2–1.4; "
        "Reduced-Load stores 0.85; Match / AP ammo entities in common.asr "
        "use the same hash.\n"
        "Editing the weapon’s Listed Damage does not do this."
    ),
    "DamageModB": (
        "Second power multiplier (pairs with Power × on overpressure / "
        "AP / Match). Typical 1.1–1.4 on those parts.\n"
        "1.0 = no change."
    ),
    "RecoilHorizontalMod": (
        "Multiplier on horizontal recoil.\n"
        "Lower than 1.0 = less side-to-side kick; higher = more kick."
    ),
    "Recoil1_Vertical": (
        "Primary kick, often felt as muzzle rise.\n"
        "Some shotguns (e.g. Sjögren) have no override for this hash — "
        "vertical kick then comes from Recoil Recovery Time, Sway, and "
        "attachment Climb/Kick mods instead."
    ),
    "Recoil2_Horizontal": (
        "Second recoil axis. On many guns this is side-to-side kick; "
        "on some (shotguns especially) it can feel diagonal "
        "(e.g. down-right) rather than pure left/right."
    ),
    "RecoilMult": (
        "Global multiplier applied to recoil. On magazine entities this "
        "is often a large factor (Sjögren standard mag stores 0.37)."
    ),
    "RecoilRecoveryMod": (
        "Multiplier on how fast recoil settles after firing.\n"
        "Higher can mean longer recovery (more camera hang); lower settles sooner."
    ),
    "RecoilRecoveryTime": (
        "How long recoil recovery lasts after a shot. High values feel "
        "like a long camera hang. Sjögren vanilla is 50 — much longer "
        "than most rifles (often under 1)."
    ),
    "RecoilResetSpeed": (
        "How quickly the sight picture returns after recoil."
    ),
    "LoudnessMod": (
        "Affects how loud the weapon is (audible range to enemies).\n"
        "On suppressors this is often a large negative delta or a strong "
        "reduction multiplier — lower loudness = quieter shots."
    ),
    "AudibleRangeBase": (
        "Base distance at which shots can be heard by enemies."
    ),
    "MobilityMod": (
        "Movement speed / mobility while this part is equipped.\n"
        "Lower = slower movement (heavier build); higher = freer movement."
    ),
    "HandlingMod": (
        "General handling (equip/ADS feel and responsiveness).\n"
        "Higher is usually snappier; lower feels heavier."
    ),
    "StabilityMod": (
        "Aim stability multiplier.\n"
        "Higher = steadier reticle; lower = more wobble."
    ),
    "ControlMod": (
        "Overall control while firing (recoil/spread feel).\n"
        "Higher generally means easier to keep on target."
    ),
    "DropMod": (
        "Bullet drop multiplier.\n"
        "Higher = more drop at range; lower = flatter trajectory."
    ),
    "VelocityMod": (
        "Muzzle velocity / bullet speed multiplier.\n"
        "Higher = faster projectile, less lead needed."
    ),
    "RangeMod": (
        "Effective range multiplier.\n"
        "Higher = damage/accuracy holds farther; lower shortens reach."
    ),
    "SwayMod": (
        "Scope/aim sway multiplier.\n"
        "Lower = less sway; higher = more bob while aiming."
    ),
    "AimSpeedMod": (
        "Aim-down-sights speed multiplier.\n"
        "Higher = faster ADS; lower = slower to bring sights up."
    ),
    "HipfireMod": (
        "Hip-fire accuracy / spread when not ADS.\n"
        "Lower often means tighter hipfire; higher is looser."
    ),
    "SpreadMod": (
        "Shot spread / accuracy multiplier.\n"
        "Lower = tighter grouping; higher = more dispersion."
    ),
    "FireRateMod": (
        "Rate-of-fire multiplier.\n"
        "Higher = faster cyclic rate; lower = slower.\n"
        "Large changes can desync fire animations."
    ),
    "CycleTimeMod": (
        "Multiplier on bolt/cycle time between shots.\n"
        "Lower = faster follow-up; higher = slower cycling."
    ),
    "BulletDropMod": (
        "Bullet trajectory drop multiplier (similar to Drop Mod).\n"
        "Affects how much you must aim high at long range."
    ),
    "PenetrationMod": (
        "Material penetration multiplier.\n"
        "Higher punches through cover better; lower is stopped more easily."
    ),
    "AimStabilityMod": (
        "ADS stability multiplier (steadiness of the reticle)."
    ),
    "ScopeInMod": (
        "Scope-in / zoom animation speed multiplier.\n"
        "Higher = faster scope-in; lower = slower."
    ),
    "ZoomStabilityMod": (
        "Stability while scoped / at zoom.\n"
        "Higher = less scoped wobble."
    ),
    "FollowUpMod": (
        "Follow-up shot readiness (time or ease of successive shots).\n"
        "Higher usually helps multi-shot control."
    ),
    "AdsMoveMod": (
        "Movement speed while aiming down sights.\n"
        "Lower = slower ADS walk; higher = freer ADS movement."
    ),
    "StrafeMod": (
        "Strafing / lateral movement feel while this part is equipped."
    ),
    "PowerMod": (
        "General “power” stat used by the loadout bars.\n"
        "Often tied to damage/stopping power presentation."
    ),
    "KickMod": (
        "Perceived kick / impulse when firing.\n"
        "Higher = more kick; lower = softer impulse."
    ),
    "GripMod": (
        "Grip contribution to control and handling.\n"
        "Often improves ADS stability or recoil when >1 on grips."
    ),
    "BurstMod": (
        "Burst-fire or multi-shot grouping behaviour.\n"
        "Relevant on automatic / burst-capable setups."
    ),
    "ClimbMod": (
        "Recoil climb (muzzle rise over a string of shots).\n"
        "Lower = less climb; higher = more vertical climb."
    ),
    "FlinchMod": (
        "How much this setup flinches targets (or self-flinch feedback).\n"
        "Higher usually means more flinch effect."
    ),
    "CompensatorMod": (
        "Compensator effectiveness on muzzle climb/recoil."
    ),
    "MuzzleMod": (
        "General muzzle-device influence (brake/hider/comp)."
    ),
    "BrakeMod": (
        "Muzzle brake contribution — typically reduces felt recoil."
    ),
    "LighteningMod": (
        "Weight-reduction contribution (lighter furniture).\n"
        "Usually improves mobility/handling at a cost to stability."
    ),
    "MassMod": (
        "Mass / weight contribution.\n"
        "Higher mass often steadies recoil but hurts mobility."
    ),
    "BarrelHarmonicsMod": (
        "Barrel vibration / harmonics — can affect accuracy consistency."
    ),
    "HeatMod": (
        "Heat build-up from firing.\n"
        "Higher heat can worsen accuracy or handling on sustained fire."
    ),
    "PressureMod": (
        "Chamber/pressure contribution (overpressure loads, hot ammo)."
    ),
    "BoltMod": (
        "Bolt / action behaviour — cycle speed or lockup feel on receivers."
    ),
    "GasMod": (
        "Gas-system contribution (semi-auto / automatic cycling)."
    ),
    "ReceiverMod": (
        "Receiver / action contribution to reliability or control."
    ),
    "FlashMod": (
        "Muzzle flash visibility.\n"
        "Lower flash is harder for enemies to spot at night."
    ),
    "BaffleMod": (
        "Suppressor baffle effectiveness — noise/flash reduction trade-offs."
    ),
    "ChokeModA": (
        "Shotgun choke factor A — pellet pattern / constriction contribution."
    ),
    "ChokeModB": (
        "Shotgun choke factor B — pellet pattern / constriction contribution."
    ),
    "ChokeModC": (
        "Shotgun choke factor C — pellet pattern / constriction contribution."
    ),
    "ChokeModD": (
        "Shotgun choke factor D — pellet pattern / constriction contribution."
    ),
    "ChokeModE": (
        "Shotgun choke factor E — pellet pattern / constriction contribution."
    ),
    "PatternMod": (
        "Shot pattern size/shape for shotguns (pellet distribution)."
    ),
    "BalanceMod": (
        "Weapon balance / point-of-balance contribution to handling."
    ),
    "MagazineCapacity": (
        "On a *magazine* entity this is usually the real mag size.\n"
        "On a *weapon* entity it is almost never the HUD magazine — it is "
        "starting reserve or max inventory stack (Kar98K weapon=60 vs "
        "DefaultMagazine=5; Panzerfaust=10 vs 1 rocket in the tube; "
        "flare gun and mines use the same hash as a carry limit).\n"
        "Large changes can break reload / pickup."
    ),
    "EffectiveRange": (
        "Stored reach in metres (Sjögren 50, M.1903 600). Affects how "
        "far listed power / accuracy is treated as “in range”. It is "
        "not enemy HP and will not turn a limb hit into a kill."
    ),
    "MuzzleVelocity": (
        "Projectile speed in m/s (Sjögren 300, M.1903 850). Changes "
        "drop and lead, not infantry hit-location lethality."
    ),
    "Damage": (
        "Listed damage score — NOT infantry hit points.\n"
        "Playtest: 0, 3× stock, and Sjögren 0.2→20 did not change "
        "how shots kill. SE5 drops enemies by hit location (head / "
        "heart / lungs) × Custom Difficulty Enemy Resilience × the "
        "loaded ammo type (Soft Point, AP, Match, buckshot…).\n"
        "Two stored encodings, not one HP scale:\n"
        "  • rifles / some pistols / AT: ~100–250\n"
        "  • SMGs / many pistols / Sjögren stock: ~0.05–0.5\n"
        "Many bolt rifles omit this hash in the patch and store a "
        "145–150 score on Drop-off / Alt. Score instead.\n"
        "To change stopping power, edit Power × (DamageMod) on the "
        "magazine / overpressure part, or change ammo type."
    ),
    "DamageSpread": (
        "Second listed score — two encodings share this hash.\n"
        "  • rifles / many pistols: 75–150, sits next to Listed Damage "
        "(M.1903 135 beside 130). Treat as a companion HUD/score, "
        "not a cone angle.\n"
        "  • some shotguns / a few pistols: tiny fractions "
        "(Sjögren 0.025, Derringer 0.026) that look like a pellet/"
        "cone term.\n"
        "Do not compare 135 to 0.025 as the same unit."
    ),
    "WindDrop": (
        "How much wind deflects the bullet. Lower = less drift."
    ),
    "RPM": (
        "On a *weapon* this is rarely present (the game uses FireRate).\n"
        "On an *attachment* it is a fire-rate change, not a new cyclic rate:\n"
        "Bramit = −90, Extended Carbine = +150. Values near 0.3–1.5 are "
        "the same kind of multiplier as Fire Rate (mod)."
    ),
    "FireRate": (
        "Cyclic rate field. Encoding is not consistent:\n"
        "  • most guns: rounds per minute (Kar98k=32, G43=400, Thompson=680)\n"
        "  • a few guns: seconds between shots (MG42=0.10, M712=0.06, "
        "Auto Burglar=0.33)\n"
        "Values under 2 are almost never RPM."
    ),
    "DamageDropoff": (
        "Drop-off / alternate listed score — two encodings share this hash.\n"
        "  • Kar98K / Mosin / Lee Enfield / Winchester / Type 1: 125–150 "
        "and these guns often have NO Listed Damage in the patch. Same "
        "numeric family as rifle Listed Damage, not a metre drop-off.\n"
        "  • SREM / M12 / Welrod / Derringer: ~0.96–1.0, which looks like "
        "a remaining-damage fraction.\n"
        "Editing this will not make torso shots start or stop killing."
    ),
    "ScopeInSpeed": (
        "How fast the ADS / scope animation plays."
    ),
    "AimStability": (
        "How steady the aim is when holding still."
    ),
    "ScopeSteadyTime": (
        "How long the sight stays steady before sway builds."
    ),
    "HoldBreathDuration": (
        "How long empty-lung / hold-breath stabilisation lasts."
    ),
    "SwayAmount": (
        "Base amount of aim sway."
    ),
    "SwayRecovery": (
        "How quickly sway settles after movement."
    ),
    "SwayDrift": (
        "Continuous drift of the reticle while aiming."
    ),
    "SwayDecay": (
        "How fast sway decays over time."
    ),
    "SwayPerShot": (
        "Extra sway added with each shot."
    ),
    "SwayWalk": (
        "Sway multiplier while walking."
    ),
    "SwayCrouch": (
        "Sway multiplier while crouching."
    ),
    "SwayProne": (
        "Sway multiplier while prone."
    ),
    "ZoomMin": (
        "Minimum optic magnification (scroll-wheel zoom floor)."
    ),
    "ZoomMax": (
        "Maximum optic magnification."
    ),
    "ZoomMax2": (
        "Secondary zoom step used by some multi-stage scopes."
    ),
}


def tooltip_for_prop(prop_name: str, prop_hash: int | None = None) -> str:
    """Return a hover explanation for any known property name."""
    tip = MODIFIER_TOOLTIPS.get(prop_name)
    if tip:
        base = tip
    elif prop_name.startswith("Mod_0x"):
        base = (
            "Unmapped float stored on this entity. The hash is not in the "
            "named stat table, so the in-game role is unconfirmed.\n"
            "On the Panzerfaust these extras are the only payload-like "
            "numbers besides carry capacity — change them only if you "
            "are testing."
        )
    elif prop_name.endswith("Mod") or prop_name.endswith("ModB"):
        pretty = prop_label(prop_name)
        base = (
            f"{pretty}.\n"
            "Attachment modifier — usually a multiplier applied while this "
            "part is equipped.\n"
            "1.0 ≈ no change; values under 1.0 reduce the effect; above 1.0 "
            "increase it. Typical range ~0.5–1.5 (suppressors may use large "
            "loudness deltas)."
        )
    else:
        base = (
            f"{prop_label(prop_name)}.\n"
            "Raw property from the weapon/attachment definition. "
            "Exact in-game meaning may vary by part."
        )
    if prop_hash is not None:
        base += f"\n\nInternal: `{prop_name}` (0x{prop_hash:08X})"
    else:
        base += f"\n\nInternal: `{prop_name}`"
    return base


def implausible_reason(prop_name: str, value, is_int: bool = False) -> str | None:
    """Explain stored numbers that are almost certainly not the labelled unit."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if prop_name in ("ZoomMin", "ZoomMax", "ZoomMax2"):
        if is_int or v > 50:
            return (
                "Not optical magnification. On M81/A1 this hash is 2–16×. "
                "PK Berlin and ZF39 store integers 300 / 500 here "
                "(range marking or a colliding int). Nearby unmapped "
                "floats around 5–12 look more like real zoom."
            )
        if v > 20:
            return (
                "Unusually high for a magnification field (typical 2–16×). "
                "Treat as unconfirmed."
            )
    if prop_name == "Recoil1_Vertical" and v > 15:
        return (
            "Far outside typical recoil (0–4). On the W&S M1913 this is "
            "70 — likely a hash collision. Use Recoil Horizontal (mod) "
            "for the real scope recoil tweak."
        )
    if prop_name == "SwayCrouch" and v > 5:
        return (
            "Far outside typical sway (0–1). On the W&S M1913 this is "
            "40 — likely a hash collision."
        )
    if prop_name == "Damage" and v > 500:
        return (
            "Far above the rifle listed-score band (100–250). Super "
            "Thompson stores 2000 — not infantry HP. This hash does not "
            "drive kill outcome."
        )
    if prop_name == "Damage" and v == 0:
        return (
            "Zero listed damage. Head / heart / lung hits still kill; "
            "this field is not infantry HP."
        )
    return None


def present_prop(
    prop_name: str,
    label_text: str,
    tooltip: str,
    value,
    is_int: bool = False,
) -> tuple[str, str]:
    """Adjust label/tooltip for known encodings and implausible values."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = None

    if prop_name == "FireRate" and v is not None and 0 < abs(v) < 2.0:
        label_text = "Cycle Interval (FireRate)"
        tooltip = (
            "Stored as FireRate. Values under 2 are seconds between shots, "
            f"not RPM. This one is {v:g} s "
            f"(≈ {60.0 / v:.0f} cyclic if it is a period).\n"
            "MG42=0.10, M712=0.06, Auto Burglar=0.33."
        )

    if prop_name == "Damage" and v is not None:
        if 0 < abs(v) < 2.0:
            label_text = "Listed Damage (fraction scale)"
        elif abs(v) >= 50:
            label_text = "Listed Damage (score scale)"

    reason = implausible_reason(prop_name, value, is_int=is_int)
    if reason:
        label_text = f"⚠ {label_text}"
        tooltip = f"{tooltip}\n\n⚠ {reason}"
    return label_text, tooltip


# ── Property definition tuples ─────────────────────────────────────────────
# (display_name, hash_name, min, max, decimals, step, tooltip, category)
# For int props: (display_name, hash_name, min, max, tooltip)

# Weapon stats (used for weapon entities)
WEAPON_FLOAT_PROPS = [
    ("Listed Damage", "Damage", 0, 100000, 3, 0.001,
     "Listed score — not infantry HP. 0 or 3× stock (and Sjögren "
     "0.2→20) does not change how shots kill. Kills are hit location × "
     "Enemy Resilience × ammo type. Rifles/AT ~100–250; SMG/shotgun "
     "often 0.05–0.5. To change power, edit Power × on the magazine.",
     "listed"),
    ("2nd Score / Spread", "DamageSpread", 0, 100000, 3, 0.001,
     "Second listed score. Rifles 75–150 sit next to Listed Damage "
     "(not a cone). Sjögren 0.025 looks like a pellet/cone term. "
     "Do not treat both as the same unit.", "listed"),
    ("Drop-off / Alt. Score", "DamageDropoff", 0, 100000, 3, 0.001,
     "Kar98K / Mosin / Lee Enfield store 145–150 here and often have "
     "no Listed Damage in the patch. SREM / M12 store ~1.0 (fraction). "
     "Not a reliable metre drop-off, and not kill HP.", "listed"),
    ("Effective Range", "EffectiveRange", 0, 100000, 0, 10,
     "Stored reach in metres (Sjögren 50, M.1903 600). Not enemy HP.",
     "stats"),
    ("Muzzle Velocity", "MuzzleVelocity", 0, 100000, 0, 10,
     "Projectile speed in m/s. Changes drop and lead, not kill HP.",
     "stats"),
    ("Wind Drop", "WindDrop", 0, 100, 4, 0.001,
     "How much wind deflects the bullet. Lower = less drift.", "stats"),
    ("RPM", "RPM", 1, 10000, 0, 1,
     "Rounds per minute. Higher = faster fire rate. "
     "WARNING: changing this can cause reload animation pauses.", "stats"),
    ("Fire Rate", "FireRate", 0, 10000, 3, 0.01,
     "Cyclic rate. Most guns store rounds/min (Kar98k=32, G43=400). "
     "A few store seconds between shots (MG42=0.10, M712=0.06) — "
     "values under 2 are not RPM.", "stats"),
    ("Audible Range", "AudibleRangeBase", -1000, 10000, 2, 0.1,
     "Base distance at which shots can be heard by enemies. "
     "SREM=120, M12=30, Welrod≈0.21, Derringer=−0.5 (quieter).", "stats"),
    ("Recoil (Vertical)", "Recoil1_Vertical", 0, 1000, 3, 0.1,
     "Primary kick / muzzle rise when present. Some shotguns have no "
     "override here — then recovery time, sway, and attachment Climb/Kick "
     "drive the vertical feel. Values above ~3 can delay follow-up shots.", "recoil"),
    ("Recoil (Horizontal)", "Recoil2_Horizontal", -1000, 1000, 3, 0.1,
     "Second recoil axis. May feel pure side kick or diagonal "
     "(e.g. down-right on some shotguns), not always pure left/right.", "recoil"),
    ("Recoil Multiplier", "RecoilMult", 0, 1000, 3, 0.1,
     "Global multiplier on recoil. On magazines this is often a large "
     "factor (Sjögren standard mag = 0.37).", "recoil"),
    ("Recoil Recovery Time", "RecoilRecoveryTime", -100, 1000, 2, 0.1,
     "How long recoil hang lasts. Sjögren vanilla is 50 (very long). "
     "Sten can be slightly negative (−0.6). High values can desync reload.", "recoil"),
    ("Recoil Reset Speed", "RecoilResetSpeed", 0, 10000, 3, 0.1,
     "How fast the crosshair resets after recoil.", "recoil"),
    ("Scope-In Speed", "ScopeInSpeed", 0.001, 100, 4, 0.01,
     "How fast the scope animation plays. "
     "M1903/SREM ~0.65 (fast), Kar98k/Mosin ~0.05 (slow).", "aim"),
    ("Aim Stability", "AimStability", 0, 1000, 3, 0.1,
     "How stable the aim is when holding the weapon.", "aim"),
    ("Scope Steady Time", "ScopeSteadyTime", 0, 1000, 3, 0.1,
     "How long the scope stays steady before sway begins.", "aim"),
    ("Hold Breath Duration", "HoldBreathDuration", 0, 1000, 3, 0.1,
     "How long you can hold breath to stabilize aim (seconds).", "aim"),
    ("Sway Amount", "SwayAmount", 0, 100, 3, 0.01,
     "Aim wobble while holding still. On guns with no Recoil (Vertical) "
     "override, high sway can also feel like post-shot kick.", "sway"),
    ("Sway Recovery", "SwayRecovery", 0, 100, 3, 0.01,
     "How fast sway settles after moving.", "sway"),
    ("Sway Drift", "SwayDrift", 0, 100, 3, 0.01,
     "Continuous drift while aiming.", "sway"),
    ("Sway Decay", "SwayDecay", 0, 100, 3, 0.01,
     "How fast sway decays over time.", "sway"),
    ("Sway Per Shot", "SwayPerShot", 0, 1000, 3, 0.1,
     "Extra sway added with each shot (can feel like vertical kick).", "sway"),
    ("Sway (Walking)", "SwayWalk", 0, 100, 3, 0.01,
     "Sway multiplier while walking.", "sway"),
    ("Sway (Crouching)", "SwayCrouch", 0, 100, 3, 0.1,
     "Sway multiplier while crouching.", "sway"),
    ("Sway (Prone)", "SwayProne", 0, 100, 3, 0.01,
     "Sway multiplier while prone.", "sway"),
]

WEAPON_INT_PROPS = [
    ("Reserve / max carry", "MagazineCapacity", 1, 200,
     "NOT rounds in the magazine.\n"
     "On the weapon record this hash is starting reserve or max inventory "
     "stack. Kar98K stores 60 here but the mag entity is 5. The "
     "Panzerfaust stores 10 — that is how many launchers you can hold, "
     "not a 10-round tube (in-game it fires 1 rocket; the flare gun and "
     "mines use the same hash as a stack limit).\n"
     "True mag size is on the magazine entity (Ammo tab) when that value "
     "is an integer. No separate chamber-size field was found on the "
     "Panzerfaust.\n"
     "WARNING: changing this on weapons can break ammo pickups."),
]

# Per-entity label/tooltip for the same hash when the generic name would lie.
INT_PROP_OVERRIDES: dict[str, dict[str, tuple[str, str]]] = {
    "Panzerfaust": {
        "MagazineCapacity": (
            "Max carry (not chamber)",
            "The Panzerfaust is a 1-shot disposable launcher. This value "
            "(vanilla 10) is the inventory stack limit — the same hash is "
            "10 on the flare gun and 12–14 on mines. It is not rounds in "
            "the tube. No 1-round chamber field exists on this entity.",
        ),
    },
    "Pzb39": {
        "MagazineCapacity": (
            "Reserve / max carry (not mag)",
            "The PzB 39 is loaded one round at a time. This 10 is a "
            "reserve/pool number (same pattern as Kar98K weapon=60 vs "
            "mag=5). Spare AT rounds are on Pzb39Ammo, not a 10-round clip.",
        ),
    },
    "Pzb39Ammo": {
        "MagazineCapacity": (
            "AT round pool",
            "Reserve of anti-tank rounds you can carry, not rounds in the "
            "rifle. The PzB 39 itself is single-load.",
        ),
    },
    "MG42": {
        "MagazineCapacity": (
            "Reserve / belt pool",
            "Weapon-level pool (vanilla 200). The belt entity "
            "MG42_DefaultMagazine stores 1; MG42(HalfAmmo) stores 50. "
            "This is not a 200-round HUD magazine by itself.",
        ),
    },
}

# Scope properties (used for scope entities)
SCOPE_FLOAT_PROPS = [
    ("Zoom Minimum", "ZoomMin", 0.0, 1000.0, 1, 0.5,
     "Optical magnification floor (scroll-wheel zoom). Typical 2–16×. "
     "Integer 300 on PK Berlin / ZF39 is not magnification.", "zoom"),
    ("Zoom Maximum", "ZoomMax", 0.0, 1000.0, 1, 0.5,
     "Optical magnification ceiling. Typical 4–16×. "
     "Fixed-zoom scopes often omit this.", "zoom"),
    ("Zoom Max 2", "ZoomMax2", 0.0, 1000.0, 1, 0.5,
     "Secondary zoom step on some scopes (A1=14, A2=16, M1913=11.8). "
     "Values above ~20 are unconfirmed as magnification.", "zoom"),
    ("Scope-In Speed", "ScopeInSpeed", 0.001, 100, 4, 0.01,
     "How fast the scope animation plays.", "aim"),
    ("Aim Stability", "AimStability", 0, 1000, 3, 0.1,
     "How stable the aim is when holding the weapon.", "aim"),
    ("Scope Steady Time", "ScopeSteadyTime", 0, 1000, 3, 0.1,
     "How long the scope stays steady before sway begins.", "aim"),
    ("Hold Breath Duration", "HoldBreathDuration", 0, 1000, 3, 0.1,
     "How long you can hold breath to stabilize aim (seconds).", "aim"),
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

# Attachment properties (barrels, magazines, suppressors, stocks, etc.)
ATTACHMENT_FLOAT_PROPS = [
    ("Power ×", "DamageMod", 0, 100000, 3, 0.001,
     "Power multiplier — gunsmith “Boosts / Reduces Damage” and "
     "Overpressure Power write this (typically 1.2–1.4 or 0.85). "
     "This is the field that actually scales stopping power.", "power"),
    ("Power × B", "DamageModB", 0, 100000, 3, 0.001,
     "Second power multiplier (AP / Match / overpressure).", "power"),
    ("Penetration ×", "PenetrationMod", 0, 100000, 3, 0.001,
     "Material penetration multiplier. AP / overpressure store ~1.2.",
     "power"),
    ("Power score (mod)", "PowerMod", -1000, 100000, 3, 0.001,
     "Gunsmith power-bar contribution. Overpressure parts often store "
     "10–12 here — not the same 1.x scale as Power ×.", "power"),
    ("Listed Damage", "Damage", 0, 100000, 3, 0.001,
     "Listed score on this part — not infantry HP. Prefer Power ×.",
     "listed"),
    ("2nd Score / Spread", "DamageSpread", 0, 100000, 3, 0.001,
     "Second listed score or leftover from a neighbouring record.",
     "listed"),
    ("Drop-off / Alt. Score", "DamageDropoff", 0, 100000, 3, 0.001,
     "Alternate listed score or leftover. Not kill HP.", "listed"),
    ("Effective Range", "EffectiveRange", 0, 100000, 0, 10,
     "Range contribution in metres (or a leftover absolute).", "stats"),
    ("Muzzle Velocity", "MuzzleVelocity", 0, 100000, 0, 10,
     "Velocity contribution in m/s (or a leftover absolute).", "stats"),
    ("Wind Drop", "WindDrop", 0, 100, 4, 0.001,
     "How much wind affects the bullet.", "stats"),
    ("RPM (delta)", "RPM", -10000, 10000, 1, 1,
     "Fire-rate change when this part is equipped — not a new cyclic rate. "
     "Bramit = −90, Extended Carbine = +150. Prefer Fire Rate (mod) when "
     "that field is also present.", "stats"),
    ("Fire Rate", "FireRate", 0, 10000, 3, 0.01,
     "Fire-rate value on this part. Often a leftover; Fire Rate (mod) is "
     "the usual attachment multiplier.", "stats"),
    ("Audible Range", "AudibleRangeBase", -1000, 10000, 2, 0.1,
     "Base distance at which the weapon can be heard. Negative = quieter.", "stats"),
    ("Recoil (Vertical)", "Recoil1_Vertical", -1000, 1000, 3, 0.1,
     "Vertical kick per shot. Values above ~15 on a scope are likely a "
     "hash collision (use Recoil Horizontal (mod) instead).", "recoil"),
    ("Recoil (Horizontal)", "Recoil2_Horizontal", -1000, 1000, 3, 0.1,
     "Horizontal sway per shot.", "recoil"),
    ("Recoil Multiplier", "RecoilMult", 0, 1000, 3, 0.1,
     "Global multiplier applied to all recoil values.", "recoil"),
    ("Recoil Recovery Time", "RecoilRecoveryTime", -100, 1000, 2, 0.1,
     "Time for recoil to settle. Can be slightly negative.", "recoil"),
    ("Recoil Reset Speed", "RecoilResetSpeed", 0, 10000, 3, 0.1,
     "How fast the crosshair resets after recoil.", "recoil"),
    ("Scope-In Speed", "ScopeInSpeed", 0.001, 100, 4, 0.01,
     "How fast the scope animation plays.", "aim"),
    ("Aim Stability", "AimStability", 0, 1000, 3, 0.1,
     "How stable the aim is.", "aim"),
    ("Scope Steady Time", "ScopeSteadyTime", 0, 1000, 3, 0.1,
     "How long the scope stays steady.", "aim"),
    ("Hold Breath Duration", "HoldBreathDuration", 0, 1000, 3, 0.1,
     "How long you can hold breath to stabilize aim (seconds).", "aim"),
    ("Zoom Minimum", "ZoomMin", 1.0, 1000.0, 1, 0.5,
     "Minimum zoom level (ironsights/scoped barrels).", "zoom"),
    ("Zoom Maximum", "ZoomMax", 1.0, 1000.0, 1, 0.5,
     "Maximum zoom level.", "zoom"),
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

ATTACHMENT_INT_PROPS = [
    ("Magazine Capacity", "MagazineCapacity", 1, 100,
     "Number of rounds per magazine."),
]

# Ammo / magazine properties. Power × is the real output scaler.
AMMO_FLOAT_PROPS = [
    ("Power ×", "DamageMod", 0, 100000, 6, 0.001,
     "Power multiplier on this magazine / conversion. Overpressure "
     "stores 1.2–1.4; Reduced-Load stores 0.85. This is what the "
     "gunsmith labels as boosting or cutting damage.", "power"),
    ("Power × B", "DamageModB", 0, 100000, 6, 0.001,
     "Second power multiplier (often pairs with Power ×).", "power"),
    ("Penetration ×", "PenetrationMod", 0, 100000, 6, 0.001,
     "Penetration multiplier. AP / overpressure store ~1.2.", "power"),
    ("Power score (mod)", "PowerMod", -1000, 100000, 6, 0.001,
     "Gunsmith power-bar contribution (often 10–12 on overpressure, "
     "not a 1.x multiplier).", "power"),
    ("Listed Damage", "Damage", 0, 100000, 6, 0.001,
     "Listed score if present — not infantry HP. Prefer Power ×.",
     "listed"),
    ("2nd Score / Spread", "DamageSpread", 0, 100000, 6, 0.001,
     "Second listed score or leftover. Two encodings (75–150 vs 0.02).",
     "listed"),
    ("Drop-off / Alt. Score", "DamageDropoff", 0, 100000, 6, 0.001,
     "Alternate listed score or leftover. Not kill HP.", "listed"),
    ("Effective Range", "EffectiveRange", 0, 100000, 3, 1,
     "Range contribution in metres.", "ballistics"),
    ("Muzzle Velocity", "MuzzleVelocity", 0, 100000, 3, 1,
     "Velocity contribution in m/s.", "ballistics"),
    ("Fire Rate", "FireRate", 0, 10000, 3, 1,
     "Fire-rate leftover or RPM. Values under 2 are seconds, not RPM.",
     "ballistics"),
    ("RPM", "RPM", 0, 10000, 6, 0.001,
     "Fire-rate change on this part (often a multiplier / leftover).",
     "ballistics"),
    ("Audible Range Base", "AudibleRangeBase", -1000, 10000, 6, 0.001,
     "How far this load is heard. Reduced-Load stores a large negative "
     "loudness mod separately.", "stealth"),
    ("Wind Drop", "WindDrop", 0, 100, 6, 0.001,
     "How much wind affects the bullet trajectory.", "stealth"),
]

# Category labels for each property set
WEAPON_CATEGORIES = [
    ("listed", "Listed scores — not infantry lethality"),
    ("stats", "Ballistics & loudness"),
    ("recoil", "Recoil"),
    ("aim", "Aiming & Scope"),
    ("sway", "Sway / post-shot kick"),
]

SCOPE_CATEGORIES = [
    ("zoom", "Magnification"),
    ("aim", "Aiming"),
    ("sway", "Sway"),
]

ATTACHMENT_CATEGORIES = [
    ("power", "Power (this scales output)"),
    ("listed", "Listed scores — not infantry lethality"),
    ("stats", "Ballistics & loudness"),
    ("recoil", "Recoil"),
    ("aim", "Aiming & Zoom"),
    ("sway", "Sway"),
]

AMMO_CATEGORIES = [
    ("power", "Power (this scales output)"),
    ("listed", "Listed scores — not infantry lethality"),
    ("ballistics", "Ballistics"),
    ("stealth", "Stealth & Detection"),
]

# Magazine / ammo entities carry capacity as an int property
AMMO_INT_PROPS = [
    ("Magazine Capacity", "MagazineCapacity", 1, 200,
     "Number of rounds per magazine / tube. "
     "WARNING: changing this may cause reload animation issues."),
]

# Properties exempt from color warning
NO_COLOR_PROPS = {"MagazineCapacity", "ZoomMin", "ZoomMax", "ZoomDefault"}

# Fields that actually scale stopping power / penetration. Listed Damage
# is deliberately excluded — playtests show it does not change kills.
DAMAGE_RELATED_PROPS = {
    "DamageMod", "DamageModB", "PenetrationMod", "PressureMod",
}

DAMAGE_EMOJI = "💥"

# Property set presets for different entity types
PROPERTY_SETS = {
    "weapon":     (WEAPON_FLOAT_PROPS, WEAPON_INT_PROPS, WEAPON_CATEGORIES),
    "scope":      (SCOPE_FLOAT_PROPS, [], SCOPE_CATEGORIES),
    "attachment": (ATTACHMENT_FLOAT_PROPS, ATTACHMENT_INT_PROPS, ATTACHMENT_CATEGORIES),
    "ammo":       (AMMO_FLOAT_PROPS, AMMO_INT_PROPS, AMMO_CATEGORIES),
}


# ── Warning color system ───────────────────────────────────────────────────

def _warning_color(current: float, original: float) -> str:
    """Return color level based on deviation from original."""
    if original == 0:
        return "green" if abs(current) < 0.01 else ("yellow" if abs(current) < 0.1 else "red")
    ratio = current / original
    if 0.667 <= ratio <= 1.5:
        return "green"
    elif 0.5 <= ratio <= 2.0:
        return "yellow"
    else:
        return "red"


def _apply_warning_style(spin, current: float, original: float, prop_name: str):
    """Apply green/yellow/red border color to a spinbox."""
    if prop_name in NO_COLOR_PROPS:
        return
    level = _warning_color(current, original)
    color = {"green": SUCCESS, "yellow": WARNING, "red": ERROR}[level]
    spin.setStyleSheet(
        f"QDoubleSpinBox, QSpinBox {{"
        f"  border: 2px solid {color};"
        f"  border-radius: 5px;"
        f"}}"
        f"QDoubleSpinBox:focus, QSpinBox:focus {{"
        f"  border: 2px solid {color};"
        f"}}"
    )


def _pct_change(current: float, default: float | None) -> tuple[str, str]:
    """Return (label, color) for current vs vanilla default."""
    if default is None:
        return "—", TEXT_DIM
    try:
        cur = float(current)
        dflt = float(default)
    except (TypeError, ValueError):
        return "—", TEXT_DIM
    if dflt == 0:
        if cur == 0:
            return "0%", TEXT_MUTED
        return "n/a", TEXT_DIM
    pct = (cur - dflt) / abs(dflt) * 100.0
    if abs(pct) < 0.05:
        return "0%", TEXT_MUTED
    sign = "+" if pct > 0 else ""
    if abs(pct - round(pct)) < 0.05:
        text = f"{sign}{pct:.0f}%"
    else:
        text = f"{sign}{pct:.1f}%"
    return text, (SUCCESS if pct > 0 else ERROR)


def _row_label(display: str, prop_name: str, src: str = "patch") -> QLabel:
    prefix = f"{DAMAGE_EMOJI} " if prop_name in DAMAGE_RELATED_PROPS else ""
    suffix = " (base)" if src == "base" else ""
    lbl = QLabel(prefix + display + suffix)
    return lbl


def _baseline(entity_name: str, prop_name: str, fallback) -> float:
    van = get_default(entity_name, prop_name)
    return fallback if van is None else van


# ── Entity property editor widget ──────────────────────────────────────────

class EntityPropertyEditor(QWidget):
    """Edits all properties of a single entity, grouped by category.

    Args:
        prop_set: One of "weapon", "scope", "attachment", "ammo".
    """

    modified = Signal()

    def __init__(self, prop_set: str = "weapon", parent=None):
        super().__init__(parent)
        self.asr_file: Optional[AsrFile] = None
        self.entity_name: str = ""
        self.prop_set = prop_set
        self.float_props, self.int_props, self.categories = PROPERTY_SETS[prop_set]
        self._spin_widgets = {}       # prop_name → widget
        self._delta_labels = {}       # prop_name → QLabel (% vs vanilla)
        self._original_values = {}    # prop_name → vanilla / load-time value
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Legend
        legend = QHBoxLayout()
        dmg = QLabel(f"{DAMAGE_EMOJI} power ×")
        dmg.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        dmg.setToolTip(
            "Marks Power × / Penetration × — the fields that actually "
            "scale stopping power. Listed Damage is not one of them."
        )
        legend.addWidget(dmg)
        legend.addStretch()
        legend.addWidget(self._make_legend_dot(SUCCESS, "Normal"))
        legend.addWidget(self._make_legend_dot(WARNING, "1.5x deviation"))
        legend.addWidget(self._make_legend_dot(ERROR, "2x+ deviation"))
        layout.addLayout(legend)

        self.model_note = QLabel()
        self.model_note.setWordWrap(True)
        self.model_note.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; padding: 6px;"
            f"background: rgba(0,0,0,40); border-radius: 4px;"
        )
        if self.prop_set == "weapon":
            self.model_note.setText(
                "Kills are hit location (head / heart / lungs) × Custom "
                "Difficulty Enemy Resilience × the loaded ammo type "
                "(Soft Point, AP, Match, buckshot…). "
                "<b>Listed Damage on this page does not change that</b> — "
                "0 or 3× stock still drops the same. "
                "To change stopping power open the Ammo tab and edit "
                "<b>Power ×</b> (DamageMod) on the magazine, or equip "
                "Overpressure / Reduced-Load / a different ammo type."
            )
        elif self.prop_set == "ammo":
            self.model_note.setText(
                "On a magazine, <b>Power ×</b> is the real output scaler "
                "(Overpressure 1.2–1.4, Reduced-Load 0.85). "
                "Listed Damage here is the same unused-for-kills score "
                "as on the weapon. Magazine Capacity on this tab is the "
                "real mag size when it is an integer."
            )
        elif self.prop_set == "attachment":
            self.model_note.setText(
                "Gunsmith lines like “Boosts Damage” / “Overpressure Power” "
                "write <b>Power ×</b> (DamageMod), not Listed Damage. "
                "Parts that only show leftover Listed Damage / Spread "
                "scores are not changing lethality."
            )
        else:
            self.model_note.hide()
        layout.addWidget(self.model_note)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)

    def _make_legend_dot(self, color: str, text: str) -> QLabel:
        label = QLabel(f"  {text}")
        label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px;"
            f"border-left: 8px solid {color};"
            f"padding-left: 4px;"
        )
        return label

    def _value_row(self, spin, prop_name: str, current, default) -> QWidget:
        """Spinbox plus a compact ±% label vs the shipped vanilla default."""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        row_layout.addWidget(spin, 0)
        delta = QLabel()
        delta.setMinimumWidth(52)
        delta.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        text, color = _pct_change(current, default)
        delta.setText(text)
        delta.setStyleSheet(f"color: {color}; font-size: 11px;")
        if default is None:
            delta.setToolTip("No shipped vanilla default for this property.")
        else:
            delta.setToolTip(
                f"Change vs vanilla default ({default:g}).\n"
                "Permanent factory values shipped with the editor."
            )
        row_layout.addWidget(delta, 0)
        row_layout.addStretch(1)
        self._delta_labels[prop_name] = delta
        return row

    def _update_delta(self, prop_name: str, current) -> None:
        delta = self._delta_labels.get(prop_name)
        if not delta:
            return
        original = self._original_values.get(prop_name)
        text, color = _pct_change(current, original)
        delta.setText(text)
        delta.setStyleSheet(f"color: {color}; font-size: 11px;")

    def set_asr_file(self, asr_file: AsrFile):
        self.asr_file = asr_file
        self._clear()

    def load_entity(self, entity_name: str):
        """Load and display properties for *entity_name*."""
        if not self.asr_file or not entity_name:
            self._clear()
            return

        self.entity_name = entity_name
        self._clear()

        entity = self.asr_file.entities.get(entity_name)
        if not entity:
            label = QLabel(f"Entity '{entity_name}' not found")
            label.setStyleSheet(muted_style())
            self.content_layout.addWidget(label)
            return

        # Group float properties by category
        for cat_key, cat_label in self.categories:
            cat_props = [p for p in self.float_props if p[7] == cat_key]
            has_any = any(entity.get(p[1]) and entity.get(p[1]).is_float
                          for p in cat_props)
            if not has_any:
                continue

            group = QGroupBox(cat_label)
            form = QFormLayout(group)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            form.setFieldGrowthPolicy(
                QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
            )

            for label_text, prop_name, vmin, vmax, decimals, step, tooltip, _ in cat_props:
                prop = entity.get(prop_name)
                if prop and prop.is_float:
                    label_text, tooltip = present_prop(
                        prop_name, label_text, tooltip, prop.value, is_int=False
                    )
                    spin = QDoubleSpinBox()
                    spin.setRange(vmin, vmax)
                    spin.setDecimals(decimals)
                    spin.setSingleStep(step)
                    spin.setValue(prop.value)
                    _size_spin(spin)
                    # Prefer curated tooltip; fall back to dictionary help
                    tip = tooltip or tooltip_for_prop(prop_name, prop.hash)
                    editable = getattr(prop, "editable", True)
                    if editable:
                        spin.setToolTip(tip)
                        spin.valueChanged.connect(
                            lambda v, p=prop_name: self._on_value_changed(p, v))
                    else:
                        spin.setReadOnly(True)
                        spin.setEnabled(False)
                        spin.setToolTip(
                            f"{tip}\n\n"
                            "Read-only: value from base common.asr "
                            "(not present in the asrpatch). "
                            "Only patch overrides can be edited."
                        )
                    baseline = _baseline(entity_name, prop_name, prop.value)
                    self._spin_widgets[prop_name] = spin
                    self._original_values[prop_name] = baseline
                    if editable:
                        _apply_warning_style(spin, prop.value, baseline, prop_name)

                    src = getattr(prop, "source", "patch")
                    lbl = _row_label(label_text, prop_name, src)
                    if prop_name in DAMAGE_RELATED_PROPS:
                        tip = spin.toolTip() + "\n\n💥 Likely to affect damage output."
                        spin.setToolTip(tip)
                    lbl.setToolTip(spin.toolTip())
                    form.addRow(lbl, self._value_row(spin, prop_name, prop.value, baseline))

            self.content_layout.addWidget(group)

        # Integer properties
        if self.int_props:
            has_int = any(entity.get(p[1]) and entity.get(p[1]).is_int
                          for p in self.int_props)
            if has_int:
                int_group = QGroupBox("Ammunition")
                int_form = QFormLayout(int_group)
                int_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
                int_form.setFieldGrowthPolicy(
                    QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
                )

                for label_text, prop_name, vmin, vmax, tooltip in self.int_props:
                    ov = INT_PROP_OVERRIDES.get(entity_name, {}).get(prop_name)
                    if ov:
                        label_text, tooltip = ov
                    prop = entity.get(prop_name)
                    if not prop:
                        continue
                    label_text, tooltip = present_prop(
                        prop_name, label_text, tooltip, prop.value,
                        is_int=bool(prop.is_int),
                    )
                    # Mag capacity can be int (round count) or float (attachment mult)
                    if prop.is_int:
                        spin = QSpinBox()
                        spin.setRange(vmin, vmax)
                        spin.setValue(int(prop.value))
                    elif prop.is_float:
                        spin = QDoubleSpinBox()
                        spin.setRange(-1000, 1000)
                        spin.setDecimals(4)
                        spin.setSingleStep(0.01)
                        spin.setValue(float(prop.value))
                    else:
                        continue
                    _size_spin(spin)
                    tip = tooltip or tooltip_for_prop(prop_name, prop.hash)
                    editable = getattr(prop, "editable", True)
                    if editable:
                        spin.setToolTip(tip)
                        spin.valueChanged.connect(
                            lambda v, p=prop_name: self._on_value_changed(p, v))
                    else:
                        spin.setReadOnly(True)
                        spin.setEnabled(False)
                        spin.setToolTip(
                            f"{tip}\n\n"
                            "Read-only: value from base common.asr "
                            "(not present in the asrpatch)."
                        )
                    baseline = _baseline(entity_name, prop_name, prop.value)
                    self._spin_widgets[prop_name] = spin
                    self._original_values[prop_name] = baseline
                    if editable:
                        _apply_warning_style(spin, prop.value, baseline, prop_name)

                    src = getattr(prop, "source", "patch")
                    suffix = " (mult)" if prop.is_float else ""
                    lbl = _row_label(label_text + suffix, prop_name, src)
                    if prop_name in DAMAGE_RELATED_PROPS:
                        spin.setToolTip(
                            spin.toolTip() + "\n\n💥 Likely to affect damage output."
                        )
                    lbl.setToolTip(spin.toolTip())
                    int_form.addRow(
                        lbl, self._value_row(spin, prop_name, prop.value, baseline)
                    )

                self.content_layout.addWidget(int_group)

        # ── All remaining properties not covered by the preset lists ──
        # Attachments often pack 10–30 float modifiers under hashes the
        # preset list never mentioned.  Surface every leftover property
        # so nothing is hidden from the user.
        shown = set(self._spin_widgets.keys())
        extras = [
            p for p in sorted(entity.properties, key=lambda x: x.offset)
            if p.name and p.name not in shown
        ]
        if extras:
            extra_group = QGroupBox(
                f"All Modifiers ({len(extras)})"
            )
            extra_form = QFormLayout(extra_group)
            extra_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            extra_form.setFieldGrowthPolicy(
                QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
            )
            for prop in extras:
                label_text = prop_label(prop.name)
                tooltip = tooltip_for_prop(prop.name, prop.hash)
                label_text, tooltip = present_prop(
                    prop.name, label_text, tooltip, prop.value,
                    is_int=bool(prop.is_int),
                )
                if prop.is_float:
                    spin = QDoubleSpinBox()
                    spin.setRange(-10000, 100000)
                    spin.setDecimals(4)
                    spin.setSingleStep(0.01)
                    spin.setValue(float(prop.value))
                elif prop.is_int:
                    spin = QSpinBox()
                    spin.setRange(0, 100000)
                    spin.setValue(int(prop.value))
                else:
                    continue
                _size_spin(spin)
                editable = getattr(prop, "editable", True)
                if editable:
                    spin.setToolTip(tooltip)
                    spin.valueChanged.connect(
                        lambda v, p=prop.name: self._on_value_changed(p, v))
                else:
                    spin.setReadOnly(True)
                    spin.setEnabled(False)
                    spin.setToolTip(tooltip + "\n\nRead-only (base file).")
                baseline = _baseline(entity_name, prop.name, prop.value)
                self._spin_widgets[prop.name] = spin
                self._original_values[prop.name] = baseline
                if editable:
                    _apply_warning_style(spin, prop.value, baseline, prop.name)
                src = getattr(prop, "source", "patch")
                lbl = _row_label(label_text, prop.name, src)
                if prop.name in DAMAGE_RELATED_PROPS:
                    spin.setToolTip(
                        spin.toolTip() + "\n\n💥 Likely to affect damage output."
                    )
                lbl.setToolTip(spin.toolTip())
                extra_form.addRow(
                    lbl, self._value_row(spin, prop.name, prop.value, baseline)
                )
            self.content_layout.addWidget(extra_group)

        if not self._spin_widgets:
            empty = QLabel(
                "No modifiable properties found for this entity in the "
                "asrpatch.\n\nSome parts (e.g. weapon-specific choke "
                "variants) are unlock stubs — the real stats live on the "
                "generic part of the same name (e.g. Cuts Full Choke)."
            )
            empty.setStyleSheet(muted_style())
            empty.setWordWrap(True)
            self.content_layout.addWidget(empty)

        dmg = entity.get("Damage")
        if (
            self.prop_set == "weapon"
            and dmg is not None
            and dmg.is_float
            and 0 < float(dmg.value) < 2
        ):
            scale = QLabel(
                "This gun’s Listed Damage is on the fraction scale "
                "(SMG / many pistols / Sjögren stock ~0.05–0.5), not "
                "the rifle 100–250 score. Neither scale is infantry HP."
            )
            scale.setWordWrap(True)
            scale.setStyleSheet(muted_style())
            self.content_layout.addWidget(scale)

        # Note when some stats came from the base file
        base_count = sum(
            1 for p in entity.properties
            if getattr(p, "source", "patch") == "base"
        )
        if base_count:
            note = QLabel(
                f"{base_count} value(s) filled from base common.asr "
                f"(shown as read-only)."
            )
            note.setStyleSheet(muted_style())
            note.setWordWrap(True)
            self.content_layout.addWidget(note)

        self.content_layout.addStretch()

    def _clear(self):
        """Remove all widgets from the content layout."""
        self._spin_widgets.clear()
        self._delta_labels.clear()
        self._original_values.clear()
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_value_changed(self, prop_name: str, value):
        if not self.asr_file or not self.entity_name:
            return
        entity = self.asr_file.entities.get(self.entity_name)
        if not entity:
            return
        prop = entity.get(prop_name)
        if not prop or not getattr(prop, "editable", True):
            return

        if prop.is_float:
            self.asr_file.set_float(self.entity_name, prop_name, float(value))
        else:
            self.asr_file.set_int(self.entity_name, prop_name, int(value))

        # Update warning color and ±% vs vanilla
        spin = self._spin_widgets.get(prop_name)
        if spin:
            original = self._original_values.get(prop_name, value)
            _apply_warning_style(spin, value, original, prop_name)
            self._update_delta(prop_name, value)

        self.modified.emit()

    def reset_to_original(self) -> int:
        """Reset editable properties to shipped vanilla (in memory only).

        Does not write the asrpatch to disk. Returns how many properties
        were written. Caller must Save + the game must restart.
        """
        if not self.asr_file or not self.entity_name:
            return 0
        from gui.vanilla_defaults import reset_entity_to_defaults

        n = reset_entity_to_defaults(self.asr_file, self.entity_name)
        entity = self.asr_file.entities.get(self.entity_name)
        if entity is None:
            return n
        for prop_name, spin in list(self._spin_widgets.items()):
            prop = entity.get(prop_name)
            if not prop:
                continue
            # Prefer shipped vanilla for baseline / colour after reset
            baseline = _baseline(self.entity_name, prop_name, prop.value)
            self._original_values[prop_name] = baseline
            spin.blockSignals(True)
            spin.setValue(prop.value)
            spin.blockSignals(False)
            if getattr(prop, "editable", True):
                _apply_warning_style(spin, prop.value, baseline, prop_name)
            self._update_delta(prop_name, prop.value)
        if n:
            self.modified.emit()
        return n

    def has_properties(self) -> bool:
        """Return True if the current entity has any editable properties."""
        return len(self._spin_widgets) > 0
