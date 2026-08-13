"""Weapon-to-attachment mapping for the Sniper Elite 5 Editor.

Primary path: auto-discover compatibility from game files via
``gui.attachment_compat`` (loadout AMP class pools + weapon-token filter +
mesh affinity). Curated shotgun allowlists remain as a fallback / override
when they match the in-game Sjögren layout better than the generic pool.

Call ``set_game_data_paths(loadout_dir, common_asr)`` after opening a game
folder so discovery can read loadout.asr_en and common.asr.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from asr import (
    RIFLE_ENTITIES, SHOTGUN_ENTITIES, PISTOL_ENTITIES, SMG_ENTITIES,
    SPECIAL_WEAPON_ENTITIES,
    SCOPE_ENTITIES, BARREL_ENTITIES, MAGAZINE_ENTITIES,
    SUPPRESSOR_ENTITIES, IRONSIGHT_ENTITIES, CHOKE_ENTITIES,
    SHOTGUN_STOCK_ENTITIES, RECEIVER_ENTITIES,
)

# Optional game-file paths for automated compatibility (set by main window)
_LOADOUT_DIR: Optional[str] = None
_COMMON_ASR: Optional[str] = None


def set_game_data_paths(
    loadout_dir: str | Path | None = None,
    common_asr: str | Path | None = None,
) -> None:
    """Point discovery at the installed game's loadout + common.asr files."""
    global _LOADOUT_DIR, _COMMON_ASR
    _LOADOUT_DIR = str(loadout_dir) if loadout_dir else None
    _COMMON_ASR = str(common_asr) if common_asr else None
    # Clear cached parsers when paths change
    try:
        from gui.attachment_compat import (
            load_amp_class_pools,
            load_weapon_attachment_ids,
            scan_mesh_weapon_affinity,
        )
        load_amp_class_pools.cache_clear()
        load_weapon_attachment_ids.cache_clear()
        scan_mesh_weapon_affinity.cache_clear()
    except Exception:
        pass

# ── Weapon categories ──────────────────────────────────────────────────────

WEAPON_CATEGORIES = [
    ("Primary Rifles", RIFLE_ENTITIES),
    ("Shotguns", SHOTGUN_ENTITIES),
    ("Pistols", PISTOL_ENTITIES),
    ("SMGs", SMG_ENTITIES),
    ("Special Weapons", SPECIAL_WEAPON_ENTITIES),
]

# Pre-mission loadout / gunsmith weapons. These have AMP attachment slots
# (or at least appear as Primary / Secondary / Sidearm). DLC guns that use
# the same workbench are included even when their loc key is named oddly.
#
# Loc keys used to build this (text/PC/LOADOUT/loadout.asr_en):
#   WEAPON_RIFLE_*  WEAPON_SECONDARY_*  WEAPON_SIDEARM_*  WEAPON_SMG_*
#   WEAPON_PISTOL_*  WEAPON_HDM_PISTOL_*
LOADOUT_WEAPONS = frozenset(
    RIFLE_ENTITIES + SHOTGUN_ENTITIES + PISTOL_ENTITIES + SMG_ENTITIES
)

# Mission pickups. They have HUD names in loadout loc (WEAPON_LAUNCHER_*,
# WEAPON_RIFLE_PZB39, WEAPON_SPECIAL_MG42) but no AMP class, no attachment
# slots, and cannot be taken into the workbench. Do not invent attachments.
LEVEL_ONLY_WEAPONS = frozenset(SPECIAL_WEAPON_ENTITIES)

# Extra entities that hold stats for a level-only weapon (not attachments).
# Shown as linked stat sources on the weapon page.
# (entity_name, prop_set, heading)
LEVEL_ONLY_STAT_SOURCES: dict[str, list[tuple[str, str, str]]] = {
    "Pzb39": [
        (
            "Pzb39Ammo",
            "ammo",
            "AT round pool (Pzb39Ammo) — spare rounds and ballistic mods, not a clip",
        ),
    ],
    "Panzerfaust": [],
    "MG42": [
        (
            "MG42_DefaultMagazine",
            "ammo",
            "Belt / magazine entity (MG42_DefaultMagazine)",
        ),
        (
            "MG42(HalfAmmo)",
            "ammo",
            "Half-ammo pickup variant (MG42(HalfAmmo))",
        ),
    ],
}


def is_loadout_weapon(weapon_name: str) -> bool:
    """True if this gun is part of the player's loadout / gunsmith."""
    return weapon_name in LOADOUT_WEAPONS


def is_level_only_weapon(weapon_name: str) -> bool:
    """True if this gun is only found in levels (no attachment workbench)."""
    return weapon_name in LEVEL_ONLY_WEAPONS

SHOTGUN_WEAPONS = frozenset(SHOTGUN_ENTITIES)

NO_SUPPRESSOR_WEAPONS = frozenset({
    "Webley", "Derringer", "Welrod", "Mk1_Welrod", "Mk2_Welrod",
    "Auto_Burglar", "Sjogren", "Drilling", "M12",
    "Panzerfaust", "Pzb39", "MG42",
    "Delisle", "G43_Kurz_Silenced", "Luger_Suppressed",
    "HDM", "EMP",
})

NO_MUZZLE_WEAPONS = frozenset({
    "Webley", "Derringer", "Welrod", "Mk1_Welrod", "Mk2_Welrod",
    "Delisle", "HDM", "G43_Kurz_Silenced", "Luger_Suppressed",
    "Panzerfaust", "Pzb39", "MG42",
})

NO_SCOPE_WEAPONS = frozenset(
    set(PISTOL_ENTITIES) | SHOTGUN_WEAPONS | set(SPECIAL_WEAPON_ENTITIES)
)

# ── Name-variant overrides ─────────────────────────────────────────────────

WEAPON_NAME_VARIANTS: dict[str, list[str]] = {
    "M1903":              ["Springfield", "1903_Trench"],
    "M1911":              ["Colt_M1911", "Colt_Stealth", "US_1911"],
    "M1911_Plus":         ["Colt_M1911", "Colt_Stealth", "US_1911", "M1911"],
    "Kar98K":             ["Kar98k", "GEW_98", "GEW98"],
    "G43_Kurz_Silenced":  ["G43"],
    "Mosin_Nagant":       ["Mosin"],
    "DLC_Mosin":          ["Mosin", "Mosin_Nagant"],
    "Pedersen":           ["Pederson"],
    "Gustaf":             ["Gustav", "Carl_Gustaf"],
    "Type1":              ["Type1", "TERA"],
    "Type100":            ["Type100"],
    "Thompson":           ["Thompson"],
    "SuperTommy":         ["Thompson", "SuperTommy"],
    "Thompson_Plus":      ["Thompson"],
    "Mk1_Welrod":         ["Welrod"],
    "Mk2_Welrod":         ["Welrod"],
    "Luger_Suppressed":   ["Luger"],
    "Drilling":           ["Drilling"],
    "Sjogren":            ["Sjogren"],
    "M12":                ["M12", "m12"],
    "EMP":                ["EMP"],
    "HDM":                ["HDM"],
    "P38":                ["P38"],
    "Delisle":            ["Delisle"],
    "StenMkII":           ["StenMkII", "StenMKII", "StenMkV", "Sten"],
    "M712":               ["M712", "Mauser_M712"],
    "MP.40":              ["MP40", "MP.40"],
    "MP.44":              ["MP44", "MP.44"],
    "Auto_Burglar":       ["Auto_Burglar", "Burglar"],
    "Winchester_1885":    ["Winchester_1885", "Winchester"],
    "Lee_Enfield":        ["Lee_Enfield", "Enfield"],
    "M1_Enfield":         ["M1_Enfield", "Enfield"],
    "M1Carbine":          ["M1Carbine", "M1_Carbine"],
    "GreaseGun":          ["GreaseGun"],
    "PPSH":               ["PPSH", "PPSh"],
    "Webley":             ["Webley"],
    "Welgun":             ["Welgun", "welgun"],
    "ModelD":             ["ModelD"],
    "Nambu":              ["Nambu"],
    "Luger":              ["Luger"],
    "Welrod":             ["Welrod"],
    "Derringer":          ["Derringer"],
    "RSC1918":            ["RSC1918"],
    "SREM":               ["SREM"],
    "G43":                ["G43"],
    "MG42":               ["MG42"],
}

# ── Slot entity pools ──────────────────────────────────────────────────────

STOCK_ENTITIES = [
    "Featherweight_Stock", "GreaseGun_DefaultStock", "Gustaf_DefaultStock",
    "Heavy_Mp44_Stock", "Heavy_Wooden_Stock", "Lightweight_Frame_Stock",
    "Standard_Sten_Stock", "Stock_Removal",
    "Lightweight_712s",
    "Heavy_Walnut_Construction", "Heavy_Oak", "Heavy_Steel_Assembly",
    "Laminated_Beech_Construction", "Fixed_Frame",
    "Lightened_Elm_Construction",
]

GRIP_ENTITIES = [
    "Austen_Foregrip", "EMP_Foregrip", "Owen_Foregrip",
    "Reinforced Foregrip Bands", "Remove_Foregrip", "US_1911_Foregrip",
    "Sten_Mk5_Grip", "X3_Grip_Tape", "X6_Grip_Tape",
    "Ridged_Pistol_Handgrip", "Ridged_SMG_Handgrip",
    "Tactical_Pistol_Handgrip", "Tactical_SMG_Handgrip",
    "Tanned_draw_grip",
]

MUZZLE_BRAKE_ENTITIES = [
    "Axis_mk2_MuzzleBrake", "Mclean_Muzzlebrake",
    "Mk1_Boys_MuzzleBreak", "Mk2_Boys_MuzzleBreak", "USGI_MuzzleBreak",
    "FG_Compensator", "Halcon_Compensator",
    "Shotgun_12G_Compensator", "Shotgun_12G_Compensator_Sjogren",
    "Modified_12G_Compensator", "SS_Flash_Hider",
]

MECHANISM_ENTITIES = list(RECEIVER_ENTITIES)

# ── In-game Sjögren / shotgun muzzle list ──────────────────────────────────
# Matches ALPHA / CUSTOMIZATION / SJÖGREN INERTIA / MUZZLE:
#   12G Compensator, Cuts Choke, Cuts Full Choke, Higins Range, Improved Cylinder
# Prefer generic entities that hold the real stat packs (weapon-suffixed
# stubs like Cuts_Full_Choke_Sjogren often have zero properties).

SHOTGUN_MUZZLE_ENTITIES = [
    # Exact order from in-game SJÖGREN / MUZZLE page
    "Shotgun_12G_Compensator",       # 12G COMPENSATOR
    "Cuts_Modified_Choke",           # CUTS CHOKE
    "Cuts_Full_Choke",               # CUTS FULL CHOKE
    "Adapted_Higins_Full_Choke",     # HIGINS RANGE CHOKE
    "Improved_Cylinder_Choke",       # IMPROVED CYLINDER
]

# In-game STOCK for Sjögren:
#   Heavy Buttplate, Rubber Buttplate, Leather Pad, Shell Loops, Wooden Pad
SHOTGUN_STOCK_ALLOWLIST = [
    "Heavy_Steel_Buttplate",
    "Rubber_Buttplate",
    "Leather_cheek_pad",
    "Shotgun_Shell_Loops",
    "Wooden_Cheek_Pad",
]

# In-game RECEIVER for Sjögren:
#   Standard (implicit), Heavy Steel Assembly, Lightened Assembly, Quick Load Mod
SHOTGUN_RECEIVER_ALLOWLIST = [
    "Heavy_Steel_Assembly",
    "Lightened_Firing_Mechanism",  # Lightened Assembly
    "Quick_Load_Mod",              # real stats (not empty Sjogren stub)
]

SHOTGUN_BARREL_ALLOWLIST = [
    "Lightened_Blued_Shotgun_Barrel",
    "Smoothbore_Barrel",
    "Rifled_Barrel_and_Sight",
]

# ── Shared pools (rifles / SMGs / pistols) ─────────────────────────────────

SHARED_SCOPES_RIFLE = list(SCOPE_ENTITIES)
SHARED_SCOPES_SMG = list(SCOPE_ENTITIES)

SHARED_SUPPRESSORS = [
    "Maxin_30_Suppressor", "Maxin_1910_Suppressor", "Moore_Suppressor",
    "Bramit_Suppressor", "Hub_23_Suppressor", "OSS_Suppressor",
]

SHARED_BARRELS_RIFLE = [
    "Blued_Lightened_Barrel", "Lightened_Barrel",
    "Parkerized_Heavy_Barrel", "Heavy_Barrel_Bands",
    "Starguage_Barrel", "Precision_Rifled_Barrel",
    "Extended_Artillery_Barrel", "Extended_Carbine_Barrel",
    "Reinforced_Barrel", "OSS_Rifled_Barrel",
    "Default_Barrel",
]

SHARED_BARRELS_SMG = [
    "Blued_Lightened_Barrel", "Lightened_Barrel",
    "Heat_Sink_Barrel", "Parkerized_Heavy_Barrel",
    "Default_Barrel",
]

SHARED_STOCKS_RIFLE = [
    "Featherweight_Stock", "Heavy_Wooden_Stock",
    "Lightweight_Frame_Stock", "Stock_Removal",
    "Heavy_Walnut_Construction", "Lightened_Elm_Construction",
    "Laminated_Beech_Construction", "Fixed_Frame",
    "Heavy_Oak",
]

SHARED_STOCKS_SMG = [
    "Featherweight_Stock", "Lightweight_Frame_Stock",
    "Stock_Removal", "Standard_Sten_Stock",
    "Heavy_Mp44_Stock",
]

SHARED_GRIPS_PISTOL = [
    "Ridged_Pistol_Handgrip", "Tactical_Pistol_Handgrip",
    "X3_Grip_Tape", "X6_Grip_Tape", "Tanned_draw_grip",
]

SHARED_GRIPS_SMG = [
    "Ridged_SMG_Handgrip", "Tactical_SMG_Handgrip",
    "Austen_Foregrip", "Owen_Foregrip",
    "Sten_Mk5_Grip", "Remove_Foregrip",
    "Reinforced Foregrip Bands",
    "X3_Grip_Tape", "X6_Grip_Tape",
]

SHARED_GRIPS_RIFLE = [
    "X3_Grip_Tape", "X6_Grip_Tape",
    "Reinforced Foregrip Bands", "Remove_Foregrip",
]

SHARED_MUZZLE_RIFLE = [
    "Mk1_Boys_MuzzleBreak", "Mk2_Boys_MuzzleBreak",
    "USGI_MuzzleBreak", "Mclean_Muzzlebrake",
    "Axis_mk2_MuzzleBrake", "FG_Compensator",
]

SHARED_MUZZLE_SMG = [
    "USGI_MuzzleBreak", "Mclean_Muzzlebrake",
    "Axis_mk2_MuzzleBrake", "SS_Flash_Hider",
    "Halcon_Compensator",
]

SHARED_MUZZLE_PISTOL = [
    "Axis_mk2_MuzzleBrake", "Mclean_Muzzlebrake",
]

SHARED_MECHANISM_RIFLE = [
    "Lightened_Firing_Mechanism", "Rifle_Bayonet_1",
]

SHARED_MECHANISM_SMG = [
    "SMG_Lightened_Bolt", "Lightened_Firing_Mechanism",
]


# ── Attachment type configuration ──────────────────────────────────────────
#
# (slot_label, entity_pool, valid_categories, shared_key)
# For shotguns, get_attachments_for_weapon overrides with curated allowlists.

ATTACHMENT_TYPES = [
    ("Scope",      SCOPE_ENTITIES,        ["Primary Rifles", "SMGs"],                        "scope"),
    ("Barrel",     BARREL_ENTITIES,       ["Primary Rifles", "Shotguns", "Pistols", "SMGs"], "barrel"),
    ("Magazine",   MAGAZINE_ENTITIES,     ["Primary Rifles", "Shotguns", "Pistols", "SMGs"], None),
    ("Suppressor", SUPPRESSOR_ENTITIES,   ["Primary Rifles", "Pistols", "SMGs"],             "suppressor"),
    ("Ironsight",  IRONSIGHT_ENTITIES,    ["Primary Rifles", "Shotguns", "Pistols", "SMGs"], None),
    # Shotgun muzzle = compensator + chokes (same as in-game MUZZLE page)
    ("Muzzle",     MUZZLE_BRAKE_ENTITIES + CHOKE_ENTITIES,
                                          ["Primary Rifles", "Shotguns", "Pistols", "SMGs"], "muzzle"),
    # Shotgun stock = buttplates / pads (not rifle frame stocks)
    ("Stock",      STOCK_ENTITIES + SHOTGUN_STOCK_ENTITIES,
                                          ["Primary Rifles", "Shotguns", "SMGs"],            "stock"),
    ("Grip",       GRIP_ENTITIES,         ["Primary Rifles", "Pistols", "SMGs"],             "grip"),
    # Receiver = in-game RECEIVER slot (assemblies / quick-load)
    ("Receiver",   RECEIVER_ENTITIES,     ["Primary Rifles", "Shotguns", "SMGs"],            "receiver"),
    ("Mechanism",  MECHANISM_ENTITIES,    ["Primary Rifles", "SMGs"],                        "mechanism"),
]


def _shared_for(weapon_name: str, category_name: str, key: str | None) -> list[str]:
    if key is None:
        return []

    is_shotgun = category_name == "Shotguns" or weapon_name in SHOTGUN_WEAPONS

    # Shotguns use dedicated allowlists in get_attachments_for_weapon
    if is_shotgun:
        return []

    if key == "scope":
        if weapon_name in NO_SCOPE_WEAPONS:
            return []
        if category_name == "Primary Rifles":
            return list(SHARED_SCOPES_RIFLE)
        if category_name == "SMGs":
            return list(SHARED_SCOPES_SMG)
        return []

    if key == "suppressor":
        if weapon_name in NO_SUPPRESSOR_WEAPONS:
            return []
        return list(SHARED_SUPPRESSORS)

    if key == "barrel":
        if category_name == "Primary Rifles":
            return list(SHARED_BARRELS_RIFLE)
        if category_name == "SMGs":
            return list(SHARED_BARRELS_SMG)
        return []

    if key == "stock":
        if category_name == "Primary Rifles":
            return list(SHARED_STOCKS_RIFLE)
        if category_name == "SMGs":
            return list(SHARED_STOCKS_SMG)
        return []

    if key == "grip":
        if category_name == "Pistols":
            return list(SHARED_GRIPS_PISTOL)
        if category_name == "SMGs":
            return list(SHARED_GRIPS_SMG)
        if category_name == "Primary Rifles":
            return list(SHARED_GRIPS_RIFLE)
        return []

    if key == "muzzle":
        if weapon_name in NO_MUZZLE_WEAPONS:
            return []
        if category_name == "Primary Rifles":
            return list(SHARED_MUZZLE_RIFLE)
        if category_name == "SMGs":
            return list(SHARED_MUZZLE_SMG)
        if category_name == "Pistols":
            return list(SHARED_MUZZLE_PISTOL)
        return []

    if key == "receiver":
        return []

    if key == "mechanism":
        if category_name == "Primary Rifles":
            return list(SHARED_MECHANISM_RIFLE)
        if category_name == "SMGs":
            return list(SHARED_MECHANISM_SMG)
        return []

    return []


def _normalize(name: str) -> str:
    return name.lower().replace(".", "").replace("-", "").replace("_", "")


def get_weapon_search_terms(weapon_name: str) -> list[str]:
    terms = [_normalize(weapon_name)]
    for variant in WEAPON_NAME_VARIANTS.get(weapon_name, []):
        n = _normalize(variant)
        if n not in terms:
            terms.append(n)
    return terms


def find_attachments_for_weapon(
    weapon_name: str,
    attachment_pool: list[str],
    available_entities: set[str] | None = None,
) -> list[str]:
    search_terms = [t for t in get_weapon_search_terms(weapon_name) if len(t) >= 3]
    matches = []
    for attachment in attachment_pool:
        if available_entities is not None and attachment not in available_entities:
            continue
        att_norm = _normalize(attachment)
        if any(term in att_norm for term in search_terms):
            matches.append(attachment)
    return sorted(matches)


def _filter_available(names: list[str], available: set[str]) -> list[str]:
    return sorted(n for n in names if n in available)


def _collapse_same_names(slot_map: dict[str, list[str]]) -> dict[str, list[str]]:
    """Merge duplicate in-game labels within each attachment slot."""
    if not slot_map:
        return slot_map
    try:
        from gui.attachment_compat import collapse_slots_by_display_name
        return collapse_slots_by_display_name(slot_map)
    except Exception:
        return slot_map


def get_attachments_for_weapon(
    weapon_name: str,
    category_name: str,
    available_entities: set[str],
) -> dict[str, list[str]]:
    """Get attachments for a weapon, organized by slot.

    Prefers automated discovery from loadout AMP class pools (see
    ``gui.attachment_compat``). Shotguns still merge curated allowlists so
    the Sjögren UI layout stays accurate when discovery under-fills a slot.

    Level-only pickups (Panzerfaust, PzB 39, MG42) have no gunsmith
    attachments — always return an empty map.
    """
    if weapon_name in LEVEL_ONLY_WEAPONS or category_name == "Special Weapons":
        return {}

    is_shotgun = category_name == "Shotguns" or weapon_name in SHOTGUN_WEAPONS

    # ── Automated path (loadout AMP + weapon filter + mesh affinity) ──
    discovered: dict[str, list[str]] = {}
    if _LOADOUT_DIR or _COMMON_ASR:
        try:
            from gui.attachment_compat import get_compatible_attachments
            discovered = get_compatible_attachments(
                weapon_name,
                category_name,
                available_entities,
                loadout_dir=_LOADOUT_DIR,
                common_asr_path=_COMMON_ASR,
            )
        except Exception:
            discovered = {}

    # ── Shotgun path: curated allowlists (authoritative for known slots)
    if is_shotgun:
        result: dict[str, list[str]] = {}

        barrels = find_attachments_for_weapon(
            weapon_name, BARREL_ENTITIES, available_entities)
        barrels = sorted(set(barrels + _filter_available(
            SHOTGUN_BARREL_ALLOWLIST, available_entities)
            + discovered.get("Barrel", [])))
        if barrels:
            result["Barrel"] = barrels

        mags = find_attachments_for_weapon(
            weapon_name, MAGAZINE_ENTITIES, available_entities)
        mags = sorted(set(mags + discovered.get("Magazine", [])))
        if mags:
            result["Magazine"] = mags

        irons = find_attachments_for_weapon(
            weapon_name, IRONSIGHT_ENTITIES, available_entities)
        if irons:
            result["Ironsight"] = irons

        muzzle = _filter_available(SHOTGUN_MUZZLE_ENTITIES, available_entities)
        muzzle = sorted(set(muzzle + discovered.get("Muzzle", [])))
        if muzzle:
            result["Muzzle"] = muzzle

        stock = _filter_available(SHOTGUN_STOCK_ALLOWLIST, available_entities)
        stock = sorted(set(stock + discovered.get("Stock", [])))
        if stock:
            result["Stock"] = stock

        receiver = _filter_available(
            SHOTGUN_RECEIVER_ALLOWLIST, available_entities)
        receiver = sorted(set(receiver + discovered.get("Receiver", [])))
        if receiver:
            result["Receiver"] = receiver

        return _collapse_same_names(result)

    # ── If discovery produced results, use them (with slot renames) ────
    if discovered:
        # Map discovery slots → browser tab names
        tab_map = {
            "Sight": "Scope",
            "Barrel": "Barrel",
            "Muzzle": "Muzzle",
            "Magazine": "Magazine",
            "Stock": "Stock",
            "Foregrip": "Grip",
            "Receiver": "Receiver",
            "Construction": "Construction",
        }
        result: dict[str, list[str]] = {}
        irons: list[str] = []
        scopes: list[str] = []
        suppressors: list[str] = []

        for slot, ents in discovered.items():
            if slot == "Sight":
                for e in ents:
                    if re_ironsight(e):
                        irons.append(e)
                    else:
                        scopes.append(e)
            elif slot == "Muzzle":
                for e in ents:
                    el = e.lower()
                    if "suppress" in el or "silencer" in el:
                        suppressors.append(e)
                    else:
                        result.setdefault("Muzzle", []).append(e)
            else:
                tab = tab_map.get(slot, slot)
                result.setdefault(tab, []).extend(ents)

        if scopes and weapon_name not in NO_SCOPE_WEAPONS:
            result["Scope"] = sorted(set(scopes))
        if irons:
            result["Ironsight"] = sorted(set(irons))
        if suppressors and weapon_name not in NO_SUPPRESSOR_WEAPONS:
            result["Suppressor"] = sorted(set(suppressors))

        if weapon_name in NO_MUZZLE_WEAPONS:
            result.pop("Muzzle", None)
            result.pop("Suppressor", None)
        if weapon_name in NO_SCOPE_WEAPONS:
            result.pop("Scope", None)

        return _collapse_same_names(
            {k: sorted(set(v)) for k, v in result.items() if v}
        )

    # ── Legacy fallback: name-matching + curated shared pools ──────────
    result = {}
    for att_type_name, att_pool, valid_categories, shared_key in ATTACHMENT_TYPES:
        if category_name not in valid_categories:
            continue
        if category_name == "Shotguns":
            continue

        if att_type_name == "Scope" and weapon_name in NO_SCOPE_WEAPONS:
            continue
        if att_type_name == "Suppressor" and weapon_name in NO_SUPPRESSOR_WEAPONS:
            continue
        if att_type_name == "Muzzle" and weapon_name in NO_MUZZLE_WEAPONS:
            continue
        if att_type_name == "Receiver":
            continue

        weapon_specific = find_attachments_for_weapon(
            weapon_name, att_pool, available_entities)

        shared = [
            a for a in _shared_for(weapon_name, category_name, shared_key)
            if a in available_entities and a in att_pool
        ]

        combined = sorted(set(weapon_specific + shared))
        if combined:
            result[att_type_name] = combined

    return _collapse_same_names(result)


def re_ironsight(name: str) -> bool:
    n = name.lower()
    return "ironsight" in n or n.endswith("_sight") and "scope" not in n


def get_all_weapons_in_category(
    category_name: str, available_entities: set[str]
) -> list[str]:
    for cat_name, weapon_list in WEAPON_CATEGORIES:
        if cat_name == category_name:
            return sorted([w for w in weapon_list if w in available_entities])
    return []
