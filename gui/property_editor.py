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

from gui.theme import (
    TEXT_MUTED, TEXT_DIM, SUCCESS, WARNING, ERROR, muted_style,
    TEST_FIELD, TEST_FIELD_BG,
)
from gui.display_names import format_entity_label
from gui.vanilla_defaults import get_default
from asr import (
    AsrFile, prop_label,
    RIFLE_ENTITIES, SHOTGUN_ENTITIES, PISTOL_ENTITIES, SMG_ENTITIES,
)

# ── Per-weapon damage field status (from playtesting) ──────────────────────
# Each damage field has a per-weapon status determined by in-game testing:
#   "working" — verified to scale damage (💥 emoji, standard warning colors)
#   "dead"    — verified NOT to scale damage (hidden from editor entirely)
#   "test"    — unverified (🧪 emoji, orange highlight)
# Weapons not listed for a field default to "hidden" (not shown).
#
# Test results recorded in weapons.ods (2026-08-15):
#   Rifles:  CombatDamageScore works for M1903/SREM/Kar98K/G43/RSC1918/
#            Mosin_Nagant/DLC_Mosin; dead for Pedersen/Type1;
#            untested for Lee_Enfield/Winchester_1885/Delisle.
#   Shotguns: DamageMod works for Sjogren; untested for M12/Auto_Burglar.
#   Pistols:  SidearmDamageScore works for M1911/Luger/Nambu/M712/ModelD;
#             dead for HDM (HS.22); P38 untested.
#             AltDamageScore removed — ODT showed it was inferior to
#             SidearmDamageScore for every pistol that had both.
#             DamageMod dead for Webley/Derringer.
#   SMGs:     SMGDamageScore works for MP.44/Type100/Gustaf/Thompson;
#             dead for GreaseGun/Welgun/MP.40;
#             untested for PPSH/EMP.
_DAMAGE_FIELD_STATUS: dict[str, dict[str, str]] = {
    "CombatDamageScore": {
        "M1903": "working", "SREM": "working", "Kar98K": "working",
        "G43": "working", "RSC1918": "working",
        "Mosin_Nagant": "working", "DLC_Mosin": "working",
        "Pedersen": "dead", "Type1": "dead",
        "Lee_Enfield": "test", "Winchester_1885": "test", "Delisle": "test",
    },
    "SidearmDamageScore": {
        "M1911": "working", "Luger": "working", "Nambu": "working",
        "M712": "working", "ModelD": "working",
        "HDM": "dead",
        "P38": "test",
    },
    "SMGDamageScore": {
        "MP.44": "working", "Type100": "working", "Gustaf": "working",
        "Thompson": "working",
        "GreaseGun": "dead", "Welgun": "dead", "MP.40": "dead",
        "PPSH": "test", "EMP": "test",
    },
    "DamageMod": {
        "Sjogren": "working",
        "Webley": "dead", "Derringer": "dead",
        "M12": "test", "Auto_Burglar": "test",
    },
}

# Damage fields that show in the "damage" category when "working" but in
# "test_damage" when "test". This lets verified damage appear as a normal
# "Damage" field instead of a playtest candidate.
_DUAL_CATEGORY_DAMAGE_PROPS: frozenset[str] = frozenset({
    "SidearmDamageScore",
    "DamageMod",
    "SMGDamageScore",
})

# Weapons hidden from the sidebar per playtest results (weapons.ods):
#   Variant stubs with no stats: M1911_Plus, Luger_Suppressed, Mk1_Welrod,
#       Mk2_Welrod — edit the parent weapon instead.
#   DLC_Mosin — not used by the player in game; the non-DLC Mosin_Nagant
#       is the correct record to edit.
#   Thompson_Plus (M1A1 Gov. Extended) — variant stub, cannot be edited.
#   G43_Kurz_Silenced (Gewehr 1943 Kurz Silenced) — variant stub, cannot be
#       edited. Edit G43 (Gewehr 43) instead.
#   SuperTommy (Super Thompson) — variant stub with no useful stats (only
#       dead/hidden fields and 0 values). Edit Thompson (M1A1 Gov.) instead.
#   Thompson is NOT hidden — it has full stats and Thompson_Plus depends on
#   it. SMGDamageScore is working (shown as "Damage").
_HIDDEN_WEAPONS: frozenset[str] = frozenset({
    "M1911_Plus", "Luger_Suppressed", "Mk1_Welrod", "Mk2_Welrod",
    "DLC_Mosin", "Thompson_Plus", "G43_Kurz_Silenced", "SuperTommy",
})

# Build the old-style class lookup from the per-weapon status for backward
# compatibility with any code that still references _CLASS_FOR_DAMAGE_PROP.
def _all_weapons_for_prop(prop_name: str) -> tuple[str, ...]:
    status = _DAMAGE_FIELD_STATUS.get(prop_name, {})
    return tuple(sorted(status.keys()))

_CLASS_FOR_DAMAGE_PROP: dict[str, tuple[tuple[str, ...], ...]] = {
    prop: (_all_weapons_for_prop(prop),)
    for prop in _DAMAGE_FIELD_STATUS
}

# Quick lookup: is a given (prop_name, entity_name) damage field working?
def _damage_status(prop_name: str, entity_name: str) -> str:
    """Return 'working', 'dead', 'test', or '' (not shown)."""
    return _DAMAGE_FIELD_STATUS.get(prop_name, {}).get(entity_name, "")


# ── Hidden fields & weapons registry ────────────────────────────────────────
# Documentation of fields and weapons removed from the GUI after playtesting,
# what we originally thought they did, and why they were removed.
#
# Source: weapons.ods playtest results (2026-08-15).
#
# HIDDEN DAMAGE FIELDS (per-weapon, status="dead" in _DAMAGE_FIELD_STATUS):
#
#   CombatDamageScore (0x65A440D8) — "Weapon Damage"
#     Thought: scales damage for all weapon classes.
#     Reality: only works for rifles. Dead for Pedersen and Type1.
#     Hidden on: Pedersen, Type1 (and all non-rifles, as before).
#
#   SidearmDamageScore (0xA02EE0D8) — "Damage" (for working pistols)
#     Thought: scales pistol damage.
#     Reality: ✅ works for M1911/Luger/Nambu/M712/ModelD.
#     Dead for HDM (HS.22). Shown as "Damage" in the Damage section for
#     working pistols. P38 untested → "Sidearm Score" in playtest section.
#
#   AltDamageScore (0x85E90E24) — in DEAD_GUI_PROPS (removed entirely)
#     Thought: alternate pistol damage, also SMG decoy.
#     Reality: ODT showed it was inferior to SidearmDamageScore for every
#     pistol that had both. Removed from the editor completely.
#
#   SMGDamageScore (0x14F34760) — "Damage" (for working SMGs)
#     Thought: scales SMG damage for all SMGs.
#     Reality: ✅ works for MP.44/Type100/Gustaf/Thompson.
#     Dead for GreaseGun/Welgun/MP.40. Untested: PPSH/EMP.
#     Shown as "Damage" in the Damage section for working SMGs.
#
#   DamageMod (0xD02587AE) — "Shotgun / Pistol Damage"
#     Thought: shotgun damage score and pistol damage for Webley/Derringer.
#     Reality: ✅ works for Sjogren. Dead for Webley and Derringer.
#     Untested: M12/Auto_Burglar.
#
#   ShotgunDamageScore (0xD1880B7B) — in DEAD_GUI_PROPS
#     Thought: shotgun damage score (Sjogren/M12 120, Auto_Burglar 100).
#     Reality: 9999/0 test → no effect. Dead on all shotguns.
#     Use DamageMod instead.
#
#   Damage (0xFFEBCB07) — in DEAD_GUI_PROPS
#     Thought: listed damage score.
#     Reality: does not change kills. Values 0.044–1.7 for SMGs, 0.2–0.45
#     for pistols — not damage scores. Hidden from all weapon editors.
#
#   DamageSpread (0x171B12B6) — in DEAD_GUI_PROPS
#     Thought: second listed damage / cone.
#     Reality: does not change kills. Hidden from all weapon editors.
#
#   DamageDropoff — in DEAD_GUI_PROPS
#     Thought: damage dropoff with range.
#     Reality: does not change kills. Hidden from all weapon editors.
#
# HIDDEN WEAPONS (in _HIDDEN_WEAPONS, removed from sidebar):
#
#   M1911_Plus (M1911 Extended) — variant stub, no stat block.
#     Thought: extended magazine variant of M1911.
#     Reality: no stats in asrpatch or common.asr blocks 0–1.
#     Edit M1911 instead.
#
#   Luger_Suppressed (Pistole 08 Suppressed) — variant stub, no stat block.
#     Thought: suppressed variant of Luger.
#     Reality: no stats. Edit Luger instead.
#
#   Mk1_Welrod (Mk1 Welrod Conversion) — variant stub, no stat block.
#     Thought: Mk1 variant of Welrod.
#     Reality: no stats. Edit Welrod instead.
#
#   Mk2_Welrod (Mk2 Welrod) — variant stub, no stat block.
#     Thought: Mk2 variant of Welrod.
#     Reality: no stats. Edit Welrod instead.
#
#   DLC_Mosin (Mosin-Nagant M91/30 DLC) — not used by the player in game.
#     Thought: the DLC variant of the Mosin-Nagant rifle.
#     Reality: the non-DLC Mosin_Nagant is the record the player actually
#     uses. DLC_Mosin is hidden to avoid confusion; edit Mosin_Nagant.
#
#   Thompson_Plus (M1A1 Gov. Extended) — variant stub, cannot be edited.
#     Thought: extended-magazine variant of the Thompson SMG.
#     Reality: no editable stat block. Edit Thompson instead.
#
#   G43_Kurz_Silenced (Gewehr 1943 Kurz Silenced) — variant stub, cannot be
#     edited.
#     Thought: suppressed Kurz (short) variant of the G43 rifle.
#     Reality: no editable stat block. Edit G43 (Gewehr 43) instead.
#
#   SuperTommy (Super Thompson) — variant stub with no useful stats.
#     Thought: special Thompson variant with unique stats.
#     Reality: only 5 properties — Damage/ShotgunDamageScore (dead/hidden),
#     AimStability/SwayCrouch (both 0.0), MagazineCapacity=3. No useful
#     editable stats. Edit Thompson (M1A1 Gov.) instead.
#
#   Thompson (M1A1 Gov.) — NOT hidden. SMGDamageScore field is working.
#     Shown as "Damage" in the Damage section.
#     Weapon stays visible (has other useful stats). Thompson_Plus
#     (Extended variant) is a stub that redirects here.

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
        "Unused for kills — hidden from the weapon Stats UI. "
        "Use 💥 Weapon Damage (D840A465) instead."
    ),
    "CombatDamageScore": (
        "Weapon damage score (hash 0x65A440D8 / hex dump D840A465).\n"
        "✅ Verified working for rifles: M1903/SREM/Kar98K/G43/RSC1918/\n"
        "Mosin_Nagant/DLC_Mosin. Dead for Pedersen/Type1.\n"
        "Untested: Lee_Enfield/Winchester_1885/Delisle.\n"
        "Hidden on pistols/SMGs/shotguns — does nothing for them."
    ),
    "SidearmDamageScore": (
        "Pistol damage score (0xA02EE0D8).\n"
        "✅ Verified: M1911/Luger/Nambu/M712/ModelD.\n"
        "Dead for HDM (HS.22). P38 untested.\n"
        "Does NOT affect shotguns or SMGs."
    ),
    "SMGDamageScore": (
        "SMG damage score (0x14F34760).\n"
        "✅ Verified: MP.44/Type100/Gustaf/Thompson.\n"
        "Dead: GreaseGun/Welgun/MP.40.\n"
        "Untested: PPSH/EMP."
    ),
    "ShotgunDamageScore": (
        "Shotgun damage score (0xD1880B7B) — DEAD.\n"
        "9999/0 test showed no effect. Hidden from editor.\n"
        "Use DamageMod for shotgun damage instead."
    ),
    "AmmoSpreadCand": (
        "🧪 PLAYTEST — ammo spread/pattern (0xD0E44A77).\n"
        "Normal 0.12–0.35 · Match 1.2 · 36Buck 1.6 · Slug 0.1. "
        "Looks like pattern, not lethality."
    ),
    "AmmoFactorCand": (
        "🧪 PLAYTEST — ammo factor (0xAF82BE35, exe-backed).\n"
        "SoftPoint 1.4 · Match ~1.25 · Slug 4. "
        "Not the Power/Pen hashes that already failed SoftPoint."
    ),
    "AmmoMassCand": (
        "🧪 PLAYTEST — ammo mass (0x920314BF, exe-backed).\n"
        "Normal 2–3.6 · Slug 1.2. Weight-shaped."
    ),
    "AmmoSoftPointCand": (
        "🧪 PLAYTEST — Soft Point vs Match split (0x80553FD9).\n"
        "SoftPoint 1.5 · Match 1.0. Matches in-game Soft Point "
        "being more lethal than Match. Best unused SoftPoint cand."
    ),
    "AmmoSoftBoostCand": (
        "🧪 PLAYTEST — Soft Point boost (0xE70AB2DE).\n"
        "SoftPoint 2.0 · Match 1.0. Same direction as Soft Point."
    ),
    "AmmoLethalityCand": (
        "🧪 PLAYTEST — load lethality (0xAE7A4305).\n"
        "Match 1.4 · SubSonic 0.7 · NonLethal 0.75. "
        "SoftPoint often omits this hash."
    ),
    "DamageSpread": (
        "Unused listed score (dead for kills). Hidden from the main UI."
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
        "Unused listed score (dead for kills). Hidden from the main UI."
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
    ("Weapon Damage", "CombatDamageScore", 0, 100000, 3, 0.001,
     "Rifle damage score (0x65A440D8 / D840A465). "
     "✅ Verified working for M1903/SREM/Kar98K/G43/RSC1918/"
     "Mosin_Nagant/DLC_Mosin. Dead for Pedersen/Type1. "
     "Untested for Lee_Enfield/Winchester_1885/Delisle.",
     "damage"),
    ("Damage", "SidearmDamageScore", -1000, 100000, 3, 0.001,
     "Pistol damage score (0xA02EE0D8). "
     "✅ Verified for M1911/Luger/Nambu/M712/ModelD. "
     "Dead for HDM (HS.22). P38 untested.",
     "damage"),
    ("Sidearm Score", "SidearmDamageScore", -1000, 100000, 3, 0.001,
     "Pistol damage score (0xA02EE0D8). "
     "✅ Verified for M1911/Luger/Nambu/M712/ModelD. "
     "Dead for HDM (HS.22). P38 untested.",
     "test_damage"),
    ("Damage", "SMGDamageScore", 0, 100000, 3, 0.001,
     "SMG damage score (0x14F34760). "
     "✅ Verified for MP.44/Type100/Gustaf/Thompson.",
     "damage"),
    ("SMG Damage", "SMGDamageScore", 0, 100000, 3, 0.001,
     "SMG damage score (0x14F34760). "
     "✅ Verified for MP.44/Type100/Gustaf/Thompson. "
     "Dead for GreaseGun/Welgun/MP.40. "
     "PPSH/EMP untested.",
     "test_damage"),
    ("Damage", "DamageMod", 0, 100000, 3, 0.001,
     "Damage score for shotguns (0xD02587AE). "
     "✅ Verified for Sjogren.",
     "damage"),
    ("Shotgun / Pistol Damage", "DamageMod", 0, 100000, 3, 0.001,
     "Damage score for shotguns and some pistols (0xD02587AE). "
     "✅ Verified for Sjogren. Dead for Webley/Derringer. "
     "M12/Auto_Burglar untested.",
     "test_damage"),
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

# Weapon-level MagazineCapacity is reserve/carry junk — not shown.
WEAPON_INT_PROPS: list = []

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
    # Magazines: real power × + mag size (int props below). No dead listed scores.
    ("Power ×", "DamageMod", 0, 100000, 6, 0.001,
     "Power multiplier on this magazine / conversion. Overpressure "
     "stores 1.2–1.4; Reduced-Load stores 0.85.", "power"),
    ("Power × B", "DamageModB", 0, 100000, 6, 0.001,
     "Second power multiplier (often pairs with Power ×).", "power"),
    ("Penetration ×", "PenetrationMod", 0, 100000, 6, 0.001,
     "Penetration multiplier. AP / overpressure store ~1.2.", "power"),
    ("Power score (mod)", "PowerMod", -1000, 100000, 6, 0.001,
     "Gunsmith power-bar contribution (often 10–12 on overpressure).",
     "power"),
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
     "How far this load is heard.", "stealth"),
    ("Wind Drop", "WindDrop", 0, 100, 6, 0.001,
     "How much wind affects the bullet trajectory.", "stealth"),
]

# Shared ammo *types* (Soft Point, Match, AP…) — not magazines.
AMMO_TYPE_FLOAT_PROPS = [
    ("Power ×", "DamageMod", 0, 100000, 6, 0.001,
     "Known power multiplier when present (Match 1.0, 24Buck 0.8). "
     "SoftPoint often has no DamageMod — try the orange candidates.",
     "power"),
    ("Power × B", "DamageModB", 0, 100000, 6, 0.001,
     "Second power multiplier (Match often 1.4).", "power"),
    ("Penetration ×", "PenetrationMod", 0, 100000, 6, 0.001,
     "Penetration multiplier when present.", "power"),
    ("🧪 Soft-Point ×", "AmmoSoftPointCand", 0, 100000, 6, 0.001,
     "PLAYTEST (0x80553FD9): SoftPoint 1.5, Match 1.0. "
     "Best unused SoftPoint lethality candidate.",
     "test_damage"),
    ("🧪 Soft Boost ×", "AmmoSoftBoostCand", 0, 100000, 6, 0.001,
     "PLAYTEST (0xE70AB2DE): SoftPoint 2.0, Match 1.0.",
     "test_damage"),
    ("🧪 Lethality ×", "AmmoLethalityCand", 0, 100000, 6, 0.001,
     "PLAYTEST (0xAE7A4305): Match 1.4, SubSonic 0.7, NonLethal 0.75.",
     "test_damage"),
    ("🧪 Ammo Factor ×", "AmmoFactorCand", 0, 100000, 6, 0.001,
     "PLAYTEST (0xAF82BE35, exe-backed): SoftPoint 1.4, Match ~1.25.",
     "test_damage"),
    ("🧪 Ammo Spread ×", "AmmoSpreadCand", 0, 100000, 6, 0.001,
     "PLAYTEST (0xD0E44A77): Normal 0.12–0.35, Match 1.2, 36Buck 1.6.",
     "test_damage"),
    ("🧪 Ammo Mass ×", "AmmoMassCand", 0, 100000, 6, 0.001,
     "PLAYTEST (0x920314BF, exe-backed): Normal 2–3.6.",
     "test_damage"),
]



# Category labels for each property set
WEAPON_CATEGORIES = [
    ("damage", "Weapon damage"),
    ("test_damage", "🧪 Non-rifle damage playtest"),
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
    ("stats", "Ballistics & loudness"),
    ("recoil", "Recoil"),
    ("aim", "Aiming & Zoom"),
    ("sway", "Sway"),
]

AMMO_CATEGORIES = [
    ("power", "Power (this scales output)"),
    ("ballistics", "Ballistics"),
    ("stealth", "Stealth & Detection"),
]

AMMO_TYPE_CATEGORIES = [
    ("power", "Known power multipliers"),
    ("test_damage", "🧪 Unused SoftPoint candidates"),
]

# Magazine / ammo entities carry capacity as an int property
AMMO_INT_PROPS = [
    ("Magazine Capacity", "MagazineCapacity", 1, 200,
     "Real magazine / tube size (integer). Not weapon reserve/carry. "
     "WARNING: large changes may break reload animations."),
]

# Properties exempt from color warning
NO_COLOR_PROPS = {"MagazineCapacity", "ZoomMin", "ZoomMax", "ZoomDefault"}

# Fields that actually scale stopping power / penetration. Listed Damage
# is deliberately excluded — playtests show it does not change kills.
# Per-weapon damage scores (CombatDamageScore, SidearmDamageScore, etc.) are
# now handled by _damage_status() — they are added to this set dynamically
# when their status is "working" for the current weapon.
DAMAGE_RELATED_PROPS = {
    "DamageModB", "PenetrationMod", "PressureMod",
}

# Ammo playtest candidates (orange, unverified). These are not per-weapon.
TEST_DAMAGE_PROPS = {
    "AmmoSpreadCand",
    "AmmoFactorCand",
    "AmmoMassCand",
    "AmmoSoftPointCand",
    "AmmoSoftBoostCand",
    "AmmoLethalityCand",
}

# Proven-dead hashes — never shown in the GUI (parser still reads them).
DEAD_GUI_PROPS = {
    "Damage", "DamageSpread", "DamageDropoff",
    "AmmoDamageScale", "AmmoPowerCand", "AmmoPenCand",
    "ShotgunDamageScore",  # 9999/0 test → no effect
    "AltDamageScore",      # inferior to SidearmDamageScore (ODT) — removed
}

DAMAGE_EMOJI = "💥"
TEST_EMOJI = "🧪"

# Property set presets for different entity types
PROPERTY_SETS = {
    "weapon":     (WEAPON_FLOAT_PROPS, WEAPON_INT_PROPS, WEAPON_CATEGORIES),
    "scope":      (SCOPE_FLOAT_PROPS, [], SCOPE_CATEGORIES),
    "attachment": (ATTACHMENT_FLOAT_PROPS, ATTACHMENT_INT_PROPS, ATTACHMENT_CATEGORIES),
    "ammo":       (AMMO_FLOAT_PROPS, AMMO_INT_PROPS, AMMO_CATEGORIES),  # magazines
    "ammo_type":  (AMMO_TYPE_FLOAT_PROPS, [], AMMO_TYPE_CATEGORIES),
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


def _apply_warning_style(spin, current: float, original: float, prop_name: str,
                         entity_name: str = ""):
    """Apply green/yellow/red border color to a spinbox.

    Per-weapon damage status:
      "working" → standard green/yellow/red warning (💥 verified)
      "test"    → permanent orange highlight (🧪 unverified)
      "dead"    → field is hidden, never reaches here
    """
    if prop_name in NO_COLOR_PROPS:
        return
    status = _damage_status(prop_name, entity_name) if entity_name else ""
    if status == "test" or (not status and prop_name in TEST_DAMAGE_PROPS):
        level = _warning_color(current, original)
        width = 3 if level != "green" else 2
        spin.setStyleSheet(
            f"QDoubleSpinBox, QSpinBox {{"
            f"  border: {width}px solid {TEST_FIELD};"
            f"  border-radius: 5px;"
            f"  background: {TEST_FIELD_BG};"
            f"  font-weight: 600;"
            f"}}"
            f"QDoubleSpinBox:focus, QSpinBox:focus {{"
            f"  border: {width}px solid {TEST_FIELD};"
            f"  background: {TEST_FIELD_BG};"
            f"}}"
        )
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


def _row_label(display: str, prop_name: str, src: str = "patch",
               entity_name: str = "") -> QLabel:
    status = _damage_status(prop_name, entity_name) if entity_name else ""
    if status == "working":
        prefix = f"{DAMAGE_EMOJI} "
    elif status == "test":
        prefix = f"{TEST_EMOJI} "
    elif prop_name in TEST_DAMAGE_PROPS:
        prefix = f"{TEST_EMOJI} "
    elif prop_name in DAMAGE_RELATED_PROPS:
        prefix = f"{DAMAGE_EMOJI} "
    else:
        prefix = ""
    # Avoid double emoji if the display string already starts with 🧪 or 💥
    if display.startswith(TEST_EMOJI) or display.startswith(DAMAGE_EMOJI):
        prefix = ""
    suffix = " (base)" if src == "base" else ""
    lbl = QLabel(prefix + display + suffix)
    if status == "test" or (not status and prop_name in TEST_DAMAGE_PROPS):
        lbl.setStyleSheet(
            f"color: {TEST_FIELD}; font-weight: 700; font-size: 13px;"
        )
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
            "Marks proven damage scalers: Weapon Damage (rifles), "
            "Damage (pistols), SMG/Shotgun Damage, "
            "and Power × / Penetration × on magazines and parts."
        )
        legend.addWidget(dmg)
        test = QLabel(f"{TEST_EMOJI} playtest")
        test.setStyleSheet(
            f"color: {TEST_FIELD}; font-size: 11px; font-weight: 700;"
        )
        test.setToolTip(
            "Orange fields are unverified playtest candidates. "
            "Change one value, Save, full game restart."
        )
        legend.addWidget(test)
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
                "💥 = verified damage field (playtested). "
                "🧪 = unverified playtest candidate. "
                "Damage fields are per-weapon: <b>Weapon Damage</b> for rifles, "
                "<b>Damage</b> for pistols, <b>SMG Damage</b> for SMGs, "
                "<b>DamageMod</b> for shotguns. Dead fields are hidden. "
                "Magazine size is on the <b>Magazine</b> sub-tab."
            )
        elif self.prop_set == "ammo":
            self.model_note.setText(
                "This is a <b>magazine</b> (clip/belt/tube), not an ammo type. "
                "Overpressure / Small Overpressure / Reduced-Load belong here. "
                "<b>Power ×</b> scales those magazines. "
                "Soft Point / Match / AP are under the Ammo Types browser."
            )
        elif self.prop_set == "ammo_type":
            self.model_note.setText(
                "Shared gunsmith ammo types (Soft Point, Match, AP…). "
                "One edit applies to every weapon that can use that type. "
                "Power / Pen / Scale A already failed SoftPoint playtest "
                "and are hidden. "
                f"<span style='color:{TEST_FIELD}; font-weight:700;'>"
                f"{TEST_EMOJI} Orange fields</span> are unused SoftPoint "
                "candidates (Soft-Point × first)."
            )
        elif self.prop_set == "attachment":
            self.model_note.setText(
                "Gunsmith “Boosts Damage” / Overpressure lines write "
                "<b>Power ×</b> (DamageMod). Weapon damage itself is "
                "💥 Weapon Damage on the Stats tab."
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

            def _visible(prop_name, _cat_key=cat_key):
                if prop_name in DEAD_GUI_PROPS:
                    return False
                # Per-weapon damage field visibility
                if self.prop_set == "weapon":
                    status = _damage_status(prop_name, entity_name)
                    if status == "dead":
                        return False
                    if status == "":
                        # Not in the status table for this weapon —
                        # check if it's a known damage prop (hide it)
                        if prop_name in _DAMAGE_FIELD_STATUS:
                            return False
                    # Dual-category damage fields: "working" shows in the
                    # "damage" category, "test" shows in "test_damage".
                    if prop_name in _DUAL_CATEGORY_DAMAGE_PROPS:
                        if status == "working" and _cat_key != "damage":
                            return False
                        if status == "test" and _cat_key != "test_damage":
                            return False
                prop = entity.get(prop_name)
                return bool(prop and (prop.is_float or prop.is_int))

            if not any(_visible(p[1]) for p in cat_props):
                continue

            # Check if any visible props in this category are still unverified
            # test candidates (orange). If all are verified working, use normal
            # group styling instead of the orange test border.
            _has_test = any(
                _damage_status(p[1], entity_name) == "test"
                or (not _damage_status(p[1], entity_name) and p[1] in TEST_DAMAGE_PROPS)
                for p in cat_props if _visible(p[1])
            ) if self.prop_set == "weapon" else (
                any(p[1] in TEST_DAMAGE_PROPS for p in cat_props if _visible(p[1]))
            )

            group = QGroupBox(cat_label)
            if cat_key == "test_damage" and _has_test:
                group.setStyleSheet(
                    f"QGroupBox {{"
                    f"  border: 2px solid {TEST_FIELD};"
                    f"  border-radius: 6px;"
                    f"  margin-top: 10px;"
                    f"  background: {TEST_FIELD_BG};"
                    f"  font-weight: 700;"
                    f"  color: {TEST_FIELD};"
                    f"}}"
                    f"QGroupBox::title {{"
                    f"  subcontrol-origin: margin;"
                    f"  left: 10px;"
                    f"  padding: 0 4px;"
                    f"  color: {TEST_FIELD};"
                    f"}}"
                )
            form = QFormLayout(group)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            form.setFieldGrowthPolicy(
                QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
            )

            for label_text, prop_name, vmin, vmax, decimals, step, tooltip, _ in cat_props:
                if not _visible(prop_name):
                    continue
                prop = entity.get(prop_name)
                is_int_prop = bool(prop and prop.is_int)
                if prop and (prop.is_float or is_int_prop):
                    label_text, tooltip = present_prop(
                        prop_name, label_text, tooltip, prop.value,
                        is_int=is_int_prop,
                    )
                    if is_int_prop:
                        # e.g. DamageMod on shotguns is stored as an int score.
                        spin = QSpinBox()
                        spin.setRange(int(vmin), int(vmax))
                        spin.setSingleStep(max(1, int(step)))
                        spin.setValue(int(prop.value))
                    else:
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
                        _apply_warning_style(spin, prop.value, baseline, prop_name,
                                             entity_name)

                    src = getattr(prop, "source", "patch")
                    lbl = _row_label(label_text, prop_name, src, entity_name)
                    status = _damage_status(prop_name, entity_name)
                    if status == "test" or (not status and prop_name in TEST_DAMAGE_PROPS):
                        tip = (
                            spin.toolTip()
                            + "\n\n🧪 PLAYTEST CANDIDATE — orange highlight. "
                            "Unverified; try zero / 3×, Save + full restart."
                        )
                        spin.setToolTip(tip)
                    elif status == "working" or prop_name in DAMAGE_RELATED_PROPS:
                        tip = spin.toolTip() + "\n\n💥 Verified to affect damage output."
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
                        _apply_warning_style(spin, prop.value, baseline, prop_name,
                                             entity_name)

                    src = getattr(prop, "source", "patch")
                    suffix = " (mult)" if prop.is_float else ""
                    lbl = _row_label(label_text + suffix, prop_name, src, entity_name)
                    status = _damage_status(prop_name, entity_name)
                    if status == "working" or prop_name in DAMAGE_RELATED_PROPS:
                        spin.setToolTip(
                            spin.toolTip() + "\n\n💥 Verified to affect damage output."
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
        # Proven-dead hashes + weapon reserve — never surface these
        _hide_extras = set(DEAD_GUI_PROPS)
        if self.prop_set == "weapon":
            _hide_extras.add("MagazineCapacity")
            # Per-weapon damage scores: hide dead ones and ones not listed
            # for this weapon (they would be irrelevant or misleading).
            for prop_name in _DAMAGE_FIELD_STATUS:
                status = _damage_status(prop_name, entity_name)
                if status in ("dead", ""):
                    _hide_extras.add(prop_name)
        extras = [
            p for p in sorted(entity.properties, key=lambda x: x.offset)
            if p.name and p.name not in shown and p.name not in _hide_extras
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
                    _apply_warning_style(spin, prop.value, baseline, prop.name,
                                         entity_name)
                src = getattr(prop, "source", "patch")
                lbl = _row_label(label_text, prop.name, src, entity_name)
                status = _damage_status(prop.name, entity_name)
                if status == "test" or (not status and prop.name in TEST_DAMAGE_PROPS):
                    spin.setToolTip(
                        spin.toolTip()
                        + "\n\n🧪 PLAYTEST CANDIDATE — orange highlight. "
                        "Unverified; try zero / 3×, Save + full restart."
                    )
                elif status == "working" or prop.name in DAMAGE_RELATED_PROPS:
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
            _apply_warning_style(spin, value, original, prop_name,
                                 self.entity_name)
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
                _apply_warning_style(spin, prop.value, baseline, prop_name,
                                     self.entity_name)
            self._update_delta(prop_name, prop.value)
        if n:
            self.modified.emit()
        return n

    def has_properties(self) -> bool:
        """Return True if the current entity has any editable properties."""
        return len(self._spin_widgets) > 0
