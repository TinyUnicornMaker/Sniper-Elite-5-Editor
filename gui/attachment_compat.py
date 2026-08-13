"""Automated weapon→attachment compatibility from Sniper Elite 5 game files.

Sources (no hand-curated per-weapon lists required):

1. **Loadout localization** (`text/PC/LOADOUT/loadout.asr_en` + `.asrpatch`)
   - ``UNLOCK_REQUIREMENT_ATTACHMENT_AMP_<ID>_<CLASS>_DESC``
   - Classes: RIFLE | SMG | PISTOL | SHOTGUN | SHARED
   - Also ``UNLOCK_REQUIREMENT_ATTACHMENT_<ID>_<CLASS>_DESC`` (e.g. GEW98_OP_MAG)

2. **Weapon-token filter**
   - AMP IDs / entity names that name *another* weapon are excluded
   - Same-family exceptions (e.g. MG13 / Gew98 mags on G43)

3. **Entity fuzzy map**
   - AMP id → asrpatch / common.asr entity name (seed table + normalized match)

4. **Mesh / texture affinity** (from ``common.asr`` block strings)
   - Per-weapon furniture meshes (``Ammo_Pouch_G43``, ``g43_beech_*``) prove support
   - When an attachment family has weapon-suffixed meshes, only weapons with a
     mesh (or a shared generic) receive it

5. **Weapon-prefix entities**
   - ``G43_LongBarrel``, ``Kar98K_DefaultMagazine``, etc. always attach to that weapon

Slot assignment uses entity-name / AMP-id heuristics aligned with in-game UI
slots (Sight, Barrel, Muzzle, Magazine, Stock, Foregrip, Receiver, Construction).
"""

from __future__ import annotations

import re
import struct
import zlib
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Iterable

# ── Class ↔ editor category ──────────────────────────────────────────────

CATEGORY_TO_CLASS = {
    "Primary Rifles": "RIFLE",
    "Shotguns": "SHOTGUN",
    "Pistols": "PISTOL",
    "SMGs": "SMG",
    "Special Weapons": "",  # level-only; no AMP class
}

# ── Weapon identity tokens (for exclude-other-weapon filter) ─────────────
# Longer / more specific tokens first when matching.

WEAPON_MARKERS: dict[str, list[str]] = {
    "G43": ["g43", "kurz"],
    "G43_Kurz_Silenced": ["g43", "kurz"],
    "Kar98K": ["kar98", "k98k", "k98", "98k", "kriegsmodell"],
    "M1903": ["1903", "springfield", "stargauge"],
    "1903_Trench": ["1903", "springfield"],
    "M1Carbine": ["m1carbine", "m1_carbine", "bushmaster"],
    "Mosin_Nagant": ["mosin"],
    "DLC_Mosin": ["mosin"],
    "Lee_Enfield": ["enfield", "leeno4", "lee_enfield"],
    "M1_Enfield": ["enfield", "m1enfield"],
    "Winchester_1885": ["winchester", "1885"],
    "Pedersen": ["pedersen", "pederson"],
    "Type1": ["type1", "tera", "arisaka"],
    "Delisle": ["delisle", "delilse"],
    "SREM": ["srem"],
    "RSC1918": ["rsc"],
    "Sjogren": ["sjogren", "sjorgen"],
    "Drilling": ["drilling", "m30"],
    "M12": ["m12", "winchester_m12", "model_1912"],
    "Auto_Burglar": ["burglar"],
    "Thompson": ["thompson", "tommy"],
    "SuperTommy": ["thompson", "tommy"],
    "Thompson_Plus": ["thompson", "tommy"],
    "PPSH": ["ppsh"],
    "Type100": ["type100", "type_100"],
    "Gustaf": ["gustaf", "gustav"],
    "GreaseGun": ["grease"],
    "StenMkII": ["sten"],
    "Welgun": ["welgun"],
    "MP.40": ["mp40", "mp.40"],
    "MP.44": ["mp44", "mp.44"],
    "EMP": ["emp", "erma"],
    "M1911": ["1911", "colt"],
    "M1911_Plus": ["1911", "colt"],
    "Luger": ["luger", "p08"],
    "Luger_Suppressed": ["luger", "p08"],
    "Webley": ["webley"],
    "Welrod": ["welrod"],
    "Mk1_Welrod": ["welrod"],
    "Mk2_Welrod": ["welrod"],
    "Derringer": ["derringer"],
    "M712": ["m712", "c96", "mauser_m712", "712s"],
    "ModelD": ["modeld", "model_d"],
    "Nambu": ["nambu"],
    "HDM": ["hdm", "hs22"],
    "P38": ["p38"],
    "MG42": ["mg42"],
}

# Attachments that are "named after" a weapon/family but are shared on related guns.
# Maps marker → weapons that may still use it.
FAMILY_EXCEPTIONS: dict[str, set[str]] = {
    "mg13": {"G43", "G43_Kurz_Silenced"},
    "gew98": {"G43", "G43_Kurz_Silenced", "Kar98K", "GEW_98_Overpressure"},
    "gew_98": {"G43", "G43_Kurz_Silenced", "Kar98K"},
    "k98": {"G43", "G43_Kurz_Silenced", "Kar98K"},  # K98 bayonet fits G43
    "98k": {"G43", "G43_Kurz_Silenced", "Kar98K"},
    "k98k": {"G43", "G43_Kurz_Silenced", "Kar98K"},
}

# ── High-confidence AMP id → entity name ─────────────────────────────────

AMP_ENTITY_SEED: dict[str, str] = {
    # Barrels
    "BLUED_BARREL": "Blued_Lightened_Barrel",
    "PARKERIZED_BARREL": "Parkerized_Heavy_Barrel",
    "STARGAUGE_BARREL": "Starguage_Barrel",
    "HEAT_SINK_RIDGED_BARREL": "Heat_Sink_Barrel",
    "PRECISION_RIFLED_BARREL": "Precision_Rifled_Barrel",
    "OSS_MATCHED_BARREL": "OSS_Rifled_Barrel",
    "REINFORCED_PRESSURE_BARREL": "Reinforced_Barrel",
    "BUSHMASTER_BARREL": "M1Carbine_LongBarrel",
    "KREIGSMODELL_BARREL": "kar98K_CarbineBarrel",
    "MOSIN_LONGBARREL": "Mosin_Nagant_LongBarrel",
    "SHORT_CARBINE_BARREL": "M1Carbine_DefaultBarrel",
    "BLUED_LINER_BARREL": "Lightened_Blued_Shotgun_Barrel",
    "SMOOTHBORE_LINER_BARREL": "Smoothbore_Barrel",
    "SLUG_RIFLED_BARREL": "Rifled_Barrel_and_Sight",
    # Muzzle
    "BRAMIT_SUPPRESSOR": "Bramit_Suppressor",
    "HUB23_SUPPRESSOR": "Hub_23_Suppressor",
    "MAXIN1910_SILENCER": "Maxin_1910_Suppressor",
    "MOORE1_SUPPRESSOR": "Moore_Suppressor",
    "FG_MUZZLE": "FG_Compensator",
    "HAL_COMPENSATOR": "Halcon_Compensator",
    "MK2_BOYS_MUZZLE": "Mk2_Boys_MuzzleBreak",
    "MK1_AT_MUZZLE": "Mk1_Boys_MuzzleBreak",
    "USGI_MUZZLE": "USGI_MuzzleBreak",
    "USGI_FLASH_HIDER": "USGI_Flash_Hider",
    "MODIFIED_12G_COMPENSATOR": "Modified_12G_Compensator",
    "12G_COMPENSATOR": "Shotgun_12G_Compensator",
    "MODIFIED_STEN_SPECIAL_SUPPRESSOR": "Sten_Mk2_Special_Silencer",
    "K98K_BAYONET": "Rifle_Bayonet_1",
    "M1905_BAYONET": "Rifle_Bayonet_1",
    "M4_BAYONET": "Rifle_Bayonet_1",
    "FLARED_FLASH_HIDER": "Flared_Flash_Hider",
    "SS_FLASH_HIDER": "SS_Flash_Hider",
    "CLASSIC_CUTTS_COMPENSATOR": "Cuts_Compensator",
    "MCLEAN_MUZZLE": "Mclean_Muzzlebrake",
    "AXIS_MUZZLE_1": "Axis_mk2_MuzzleBrake",
    "ADAPTED_AXIS_MK2_MUZZLE": "Axis_mk2_MuzzleBrake",
    "ADAPTED_CUTTS_COMPENSATOR": "Cuts_Compensator",
    # Chokes
    "CUTTS_FULL_CHOKE": "Cuts_Full_Choke",
    "CUTTS_MODIFIED_CHOKE": "Cuts_Modified_Choke",
    "ADAPTED_HIGGINS_FULL_CHOKE": "Adapted_Higins_Full_Choke",
    "IMPROVED_CYLINDER_CHOKE": "Improved_Cylinder_Choke",
    "POWER_HYBRID_CHOKE": "Power_Hyrbid_Choke",
    # Magazines
    "G43_KURZ_MAG": "Kurz_Conversion",
    "GEW98_OP_MAG": "GEW_98_Overpressure",
    "MG13_TRENCH": "Mg13_trench",
    "PROOF_ROUNDS_MAG": "Reduced_load_magazine",
    "AMMOPOUCH_MAGS": "Magazine_pouch",
    "AMMOPOUCH_ROUNDS": "Magazine_pouch",
    "AMMOPOUCH": "Magazine_pouch",
    "1903_25_TRENCH_MAG": "1903_Trench",
    "98K_TRENCH_MAG": "1903_Trench",
    "M1_CARBINE_10_ROUND": "M1_10rd",
    "M1_CARBINE_30_ROUND": "M1_Carbine_DefaultMagazine",
    "100RD_TOMMY_DRUM_MAG": "100rd_Drum",
    "50RD_TOMMY_DRUM_MAG": "PPSH_50d_Drum",
    "9MM_PPLUS_STICK_MAG": "PPlus_Stick",
    "LARGE_9MM_STICK_MAG": "Large_9mm_Stick",
    "SMALL_9MM_STICK_MAG": "Small_Stick",
    "MEDIUM_THOMPSON_STICK_MAG": "30rd_Thompson_Stick",
    "FIXED_PLUG_25RD_MAG": "25Rd_Marksmen_Mp44_Mag",
    "GUSTAV_71RD_MAG": "Quad_M31_Magazine_Carl_Gustaf",
    "GERAT_EXPERIMENTAL_PPLUS_MAG": "Geret_06_Experimental_P_Plus",
    "32R_SNAIL_MAG": "Snail_Magazine",
    "EXTENDED_SINGLE_STACK_MAG": "Medium_Extended_Single_Stack",
    "LARGE_EXTENDED_SINGLE_STACK_MAG": "Large_Extended_Single_Stack",
    "LARGE_EXTENDED_MAUSER_MAG": "Large_Extended_Single_Stack",
    "DELISLE_11RD_MAGAZINE": "11rd_Delisle",
    "DELISLE_20RD_MAGAZINE": "20rd_delisle",
    # Stock / pads
    "HEAVY_STEEL_BUTTPLATE": "Heavy_Steel_Buttplate",
    "RUBBER_RECOIL_BUTTPLATE": "Rubber_Buttplate",
    "LEATHER_CHEEK_PAD": "Leather_cheek_pad",
    "WOODEN_CHEEK_PAD": "Wooden_Cheek_Pad",
    "HEAVYWEIGHT_WOODEN_STOCK": "Heavy_Wooden_Stock",
    "HEAVY_MP44_STOCK": "Heavy_Mp44_Stock",
    "LIGHTWEIGHT_STOCK": "Lightweight_Frame_Stock",
    "STANDARD_STEN_STOCK": "Standard_Sten_Stock",
    "STOCK_REMOVAL": "Stock_Removal",
    "GUSTAV_FOLDED_STOCK": "Gustaf_DefaultStock",
    "FIXED_FRAME_M1911_STOCK": "Fixed_Frame",
    "LIGHTWEIGHT_712_STOCK": "Lightweight_712s",
    "C96_REMOVABLE_STOCK": "Fixed_Frame",
    # Construction
    "LAMINATED_BEECH_CONSTRUCTION": "Laminated_Beech_Construction",
    "LIGHTENED_ELM_CONSTRUCTION": "Lightened_Elm_Construction",
    "HEAVY_DARK_WALNUT_CONSTRUCTION": "Heavy_Walnut_Construction",
    # Foregrip / grip
    "REINFORCED_BANDS_GRIP": "Reinforced Foregrip Bands",
    # Rifle "heavy reinforcement band" → Overpressure Power barrel (not pistol bands)
    "HEAVY_REINFORCEMENT_BAND": "Reinforced_Barrel",
    # Pistol-only AMP_HEAVY_BARREL_BANDS → Heavy_Barrel_Bands ("Overpressure Power")
    "HEAVY_BARREL_BANDS": "Heavy_Barrel_Bands",
    "GRASPING_CONVEX_GRIP": "Tanned_draw_grip",
    "TANNED_DRAW_GRIP": "Tanned_draw_grip",
    "THICK_GRIP_TAPE": "X6_Grip_Tape",
    "THIN_GRIP_TAPE": "X3_Grip_Tape",
    "GRIPTAPE_X3": "X3_Grip_Tape",
    "GRIPTAPE_X6": "X6_Grip_Tape",
    "HEAVY_LEATHER_LOADER_GRIP": "leather_Loader",
    "LEATHER_SIGHT_HOOD_GRIP": "Leather_Hood",
    "1911_FOREGRIP": "US_1911_Foregrip",
    "ADAPTED_EMP_GRIP": "EMP_Foregrip",
    "EXPERIMENTAL_OWEN_GRIP": "Owen_Foregrip",
    "MODIFIED_AUSTEN_GRIP": "Austen_Foregrip",
    "CLASSIC_TOMMY_GRIP": "Remove_Foregrip",
    "FOREGRIP_REMOVAL": "Remove_Foregrip",
    "MK5_STEN_GRIP": "Sten_Mk5_Grip",
    "STENMK5_GRIP": "Sten_Mk5_Grip",
    # Receiver / assembly
    "HEAVY_STEEL_ASSEMBLY_RECEIVER": "Heavy_Steel_Assembly",
    "LIGHTENED_FIRING_MECHANISM_RECEIVER": "Lightened_Firing_Mechanism",
    "QUICK_LOAD_MOD_RECIEVER": "Quick_Load_Mod",
    "LIGHTENED_BOLT_RECEIVER": "SMG_Lightened_Bolt",
    "LIGHTENED_BOLT_RECEIEVER": "SMG_Lightened_Bolt",
    "HEAVY_BOLT_RECEIVER": "SMG_Heavy_Bolt",
    "HEAVY_BOLT_RECEIEVER": "SMG_Heavy_Bolt",
    "PRECISION_RECEIVER": "Precision_Receiver",
    "REINFORCED_OP_RECEIVER": "Reinforced_Overpressure_Receiver",
    # Scopes (SHARED / AMP short ids)
    "PU": "PU_scope",
    "ZF41": "ZF41_Scope",
    "A1_OC": "A1_Optical",
    "A2_OC": "A2_Optical",
    "B4": "B4_Scope",
    "MODEL_2_NIGHT_VISION_SCOPE": "Model2_Night_Vision_Scope",
    # Pistol suppressors
    "FOXLEY_SUPPRESSOR": "Foxley_Silencer",
    "OSS_SUPPRESSOR": "OSS_Suppressor",
    "MAXIM_30_SILENCER": "Maxin_30_Suppressor",
    "MODEL_27_SUPPRESSOR": "SMG_Model_27_Silencer",
    "SS_EXPERIMENTAL_SILENCER": "OSS_Suppressor",
    # Pistol barrels
    "EXTENDED_ARTILLERY_BARREL": "Extended_Artillery_Barrel",
    "EXTENDED_CARBINE_BARREL": "Extended_Carbine_Barrel",
    "HEAVY_BARREL_BANDS": "Heavy_Barrel_Bands",
}

# AMP ids that are ammo types, not attachment entities (skip for attachment UI)
AMMO_AMP_IDS = frozenset({
    "AP_FMJ_AMMO", "MATCH_FMJ_AMMO", "SOFT_POINT_AMMO", "SUBSONIC_AMMO",
    "24_BUCKSHOT_SHELLS", "36_BUCKSHOT_SHELLS", "36_BUCKSHOT_PISTOL_SHELLS",
    "SLUG_SHELLS", "DERRINGER_OVERPRESSURE",
})

# ── Slot classification ──────────────────────────────────────────────────

SLOT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Order matters — first match wins. Put specific families before generic.
    ("Construction", re.compile(
        r"(construction|walnut|beech|elm|laminated)", re.I)),
    ("Sight", re.compile(
        r"(scope|optical|ironsight|_sight$)", re.I)),
    ("Barrel", re.compile(
        r"(barrel|liner|bushmaster|kriegsmodell|mousqueton|stargauge|"
        r"marksman|longbarrel|shortbarrel|parkerized|reinforced_barrel)", re.I)),
    ("Muzzle", re.compile(
        r"(suppressor|silencer|muzzle|compensator|brake|flash_hider|"
        r"flashhider|bayonet|choke|bramit|hub_?23|moore|maxin|oss_|"
        r"fg_|halcon|boys|usgi|baffle)", re.I)),
    ("Stock", re.compile(
        r"(stock|buttplate|cheek_pad|cheekpad|pouch|shell_loops|"
        r"bullet_loops|featherweight|frame_stock|folded)", re.I)),
    ("Magazine", re.compile(
        r"(mag|magazine|drum|stick|snail|trench|kurz|mg13|gew98|"
        r"overpressure|pplus|quad|reduced_load|10rd|20rd|11rd|25rd|30rd|"
        r"50d|100rd|conversion)", re.I)),
    ("Foregrip", re.compile(
        r"(foregrip|grip_tape|handgrip|draw_grip|hood|loader|"
        r"reinforced.?foregrip|bands_grip|austen|owen|emp_fore|"
        r"x3_grip|x6_grip)", re.I)),
    ("Receiver", re.compile(
        r"(receiver|assembly|firing_mechanism|quick_load|heavy_bolt|"
        r"lightened_bolt|travel_trigger|match_receiver|precision_receiver|"
        r"overpressure_receiver)", re.I)),
]

# ── Scope / sight faction pools ──────────────────────────────────────────
# The game does NOT give every rifle every scope. In-game Gewehr 1943 SIGHT
# list is only: Iron Sights, ZF4, M-2 Night Vision, P.K Berlin, PU.
# Allied scopes (M81, No32, A5, …) must not appear on Axis rifles.
#
# AMP keys only tag a few scopes as SHARED (PU, ZF41). The rest have no
# RIFLE/SMG class suffix. We therefore assign scopes by faction derived
# from weapon identity + historical SE5 loadout pools, validated against
# G43 screenshots.

FACTION_AXIS = "axis"
FACTION_ALLIED = "allied"
FACTION_SOVIET = "soviet"
FACTION_JAPANESE = "japanese"
FACTION_SHARED = "shared"  # usable on any scoped weapon of the right class

WEAPON_FACTION: dict[str, str] = {
    # Axis
    "G43": FACTION_AXIS,
    "G43_Kurz_Silenced": FACTION_AXIS,
    "Kar98K": FACTION_AXIS,
    "GEW_98_Overpressure": FACTION_AXIS,
    "MP.40": FACTION_AXIS,
    "MP.44": FACTION_AXIS,
    "Luger": FACTION_AXIS,
    "Luger_Suppressed": FACTION_AXIS,
    "P38": FACTION_AXIS,
    "M712": FACTION_AXIS,
    "MG42": FACTION_AXIS,
    "Pzb39": FACTION_AXIS,
    # Allied (US / UK / FR / mixed Western)
    "M1903": FACTION_ALLIED,
    "1903_Trench": FACTION_ALLIED,
    "M1Carbine": FACTION_ALLIED,
    "SREM": FACTION_ALLIED,
    "Winchester_1885": FACTION_ALLIED,
    "Pedersen": FACTION_ALLIED,
    "Lee_Enfield": FACTION_ALLIED,
    "M1_Enfield": FACTION_ALLIED,
    "Delisle": FACTION_ALLIED,
    "RSC1918": FACTION_ALLIED,
    "M1911": FACTION_ALLIED,
    "M1911_Plus": FACTION_ALLIED,
    "Thompson": FACTION_ALLIED,
    "SuperTommy": FACTION_ALLIED,
    "Thompson_Plus": FACTION_ALLIED,
    "GreaseGun": FACTION_ALLIED,
    "StenMkII": FACTION_ALLIED,
    "Welgun": FACTION_ALLIED,
    "Welrod": FACTION_ALLIED,
    "Mk1_Welrod": FACTION_ALLIED,
    "Mk2_Welrod": FACTION_ALLIED,
    "Webley": FACTION_ALLIED,
    "Derringer": FACTION_ALLIED,
    "HDM": FACTION_ALLIED,
    "ModelD": FACTION_ALLIED,
    "M12": FACTION_ALLIED,
    "Auto_Burglar": FACTION_ALLIED,
    "Sjogren": FACTION_ALLIED,
    "Drilling": FACTION_AXIS,  # German M30
    "Gustaf": FACTION_ALLIED,
    "EMP": FACTION_AXIS,
    # Soviet
    "Mosin_Nagant": FACTION_SOVIET,
    "DLC_Mosin": FACTION_SOVIET,
    "PPSH": FACTION_SOVIET,
    # Japanese
    "Type1": FACTION_JAPANESE,
    "Type100": FACTION_JAPANESE,
    "Nambu": FACTION_JAPANESE,
}

# Scope entity → faction(s) that may equip it on rifles/SMGs.
# SHARED = any faction. Weapon-specific variants handled separately.
SCOPE_FACTION: dict[str, set[str]] = {
    # Axis optics — G43 in-game SIGHT: Iron, ZF4, M-2 NV, P.K Berlin, PU
    "Zf4_scope": {FACTION_AXIS},
    # ZF39 has a Kar98-specific mesh (Kar98k_ZF39_Scope); not on G43 UI
    "Zf39_Scope": set(),  # only via weapon-prefix / explicit allow below
    "ZF41_Scope": {FACTION_SHARED},  # AMP_ZF41_SHARED
    "PK_Berlin_Scope": {FACTION_AXIS},
    # Cross-faction (confirmed on G43 screenshots)
    "PU_scope": {FACTION_SHARED},
    "Model2_Night_Vision_Scope": {FACTION_SHARED},
    # Allied Western
    "M81_Scope": {FACTION_ALLIED},
    "M84_Scope": {FACTION_ALLIED},
    "No32_Mk1_Scope": {FACTION_ALLIED},
    "No32_Mk2_Scope": {FACTION_ALLIED},
    "A1_Optical": {FACTION_ALLIED},
    "A2_Optical": {FACTION_ALLIED},
    "A5_Winchester_Scope": {FACTION_ALLIED},
    "B4_Scope": {FACTION_ALLIED},
    "M1913_Scope": {FACTION_ALLIED},
    "PPCo_Scope": {FACTION_ALLIED},
    # Soviet-specific
    "PU_scope_Mosin": {FACTION_SOVIET},
    # Japanese
    "T97_Scope": {FACTION_JAPANESE},
    "T99_Scope": {FACTION_JAPANESE},
    "Type99_LMG_Scope": {FACTION_JAPANESE},
}

# AMP ids for scopes that lack a RIFLE/SMG class suffix in loadout keys
SCOPE_AMP_ENTITY: dict[str, str] = {
    "A1_OC": "A1_Optical",
    "A2_OC": "A2_Optical",
    "B4": "B4_Scope",
    "M84": "M84_Scope",
    "NO32_MK2": "No32_Mk2_Scope",
    "ZF39": "Zf39_Scope",
    "PU": "PU_scope",
    "ZF41": "ZF41_Scope",
    "MODEL_2_NIGHT_VISION_SCOPE": "Model2_Night_Vision_Scope",
    "MODEL2_NIGHT_VISION_SCOPE": "Model2_Night_Vision_Scope",
}


def weapon_faction(weapon_name: str) -> str:
    if weapon_name in WEAPON_FACTION:
        return WEAPON_FACTION[weapon_name]
    # heuristic fallbacks
    n = weapon_name.lower()
    if any(x in n for x in ("g43", "kar98", "mp40", "mp44", "luger", "p38", "mg42")):
        return FACTION_AXIS
    if any(x in n for x in ("mosin", "ppsh")):
        return FACTION_SOVIET
    if any(x in n for x in ("type1", "type100", "nambu", "tera", "arisaka")):
        return FACTION_JAPANESE
    return FACTION_ALLIED


def scope_allowed_for_weapon(scope_entity: str, weapon_name: str) -> bool:
    """True if this scope entity is legal on the weapon's faction."""
    wn = _norm(weapon_name)
    sn = _norm(scope_entity)

    # Explicit weapon-specific optics (mesh names in common.asr)
    if sn in ("zf39scope", "kar98kzf39scope") or "zf39" in sn:
        return "kar98" in wn
    if "mosin" in sn:
        return "mosin" in wn
    if wn and wn in sn and "scope" in sn:
        return True

    factions = SCOPE_FACTION.get(scope_entity)
    if not factions:
        # Unknown scope: do NOT auto-include (prevents Allied dump on Axis)
        return False
    if FACTION_SHARED in factions:
        return True
    return weapon_faction(weapon_name) in factions

# In-game slot order for rifles (matches GEWEHR 1943 loadout summary)
RIFLE_SLOT_ORDER = [
    "Sight", "Barrel", "Muzzle", "Magazine", "Stock",
    "Foregrip", "Receiver", "Construction",
]
SHOTGUN_SLOT_ORDER = ["Barrel", "Muzzle", "Stock", "Receiver", "Magazine"]
SMG_SLOT_ORDER = [
    "Sight", "Barrel", "Muzzle", "Magazine", "Stock",
    "Foregrip", "Receiver",
]
PISTOL_SLOT_ORDER = [
    "Sight", "Barrel", "Muzzle", "Magazine", "Stock",
    "Foregrip", "Receiver",
]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _read_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if data[:8] == b"AsuraZlb":
        _flags, csize, _usize = struct.unpack_from("<III", data, 8)
        for wbits in (13, 15, -15, 12):
            try:
                return zlib.decompress(data[20:20 + csize], wbits)
            except Exception:
                continue
        return data
    return data


def _ascii_strings(data: bytes, min_len: int = 6) -> list[str]:
    return [m.decode("ascii") for m in re.findall(
        rb"[\x20-\x7e]{" + str(min_len).encode() + rb",}", data)]


# ── Loadout AMP class pools ──────────────────────────────────────────────

@lru_cache(maxsize=4)
def load_amp_class_pools(loadout_dir: str) -> dict[str, set[str]]:
    """Parse AMP attachment ids grouped by weapon class from loadout loc files."""
    root = Path(loadout_dir)
    by_class: dict[str, set[str]] = defaultdict(set)
    pat_amp = re.compile(
        r"UNLOCK_REQUIREMENT_ATTACHMENT_AMP_(.+?)_"
        r"(RIFLE|SMG|PISTOL|SHOTGUN|SHARED)_DESC$"
    )
    pat_plain = re.compile(
        r"UNLOCK_REQUIREMENT_ATTACHMENT_(.+?)_"
        r"(RIFLE|SMG|PISTOL|SHOTGUN)_DESC$"
    )
    for name in ("loadout.asr_en", "loadout.asr_en.asrpatch"):
        path = root / name
        if not path.is_file():
            continue
        for key in _ascii_strings(_read_bytes(path), 12):
            m = pat_amp.match(key)
            if m:
                by_class[m.group(2)].add(m.group(1))
                continue
            m = pat_plain.match(key)
            if m and not m.group(1).startswith("AMP_"):
                by_class[m.group(2)].add(m.group(1))
    return dict(by_class)


@lru_cache(maxsize=4)
def load_weapon_attachment_ids(loadout_dir: str) -> set[str]:
    root = Path(loadout_dir)
    ids: set[str] = set()
    pat = re.compile(
        r"WEAPON_ATTACHMENT_(.+?)_(LONGNAME|SHORTNAME|DESC|SHORTDESC)$"
    )
    for name in ("loadout.asr_en", "loadout.asr_en.asrpatch"):
        path = root / name
        if not path.is_file():
            continue
        for key in _ascii_strings(_read_bytes(path), 10):
            m = pat.match(key)
            if m:
                ids.add(m.group(1))
    return ids


# ── Mesh / texture affinity ──────────────────────────────────────────────

@lru_cache(maxsize=2)
def scan_mesh_weapon_affinity(common_asr_path: str) -> dict[str, set[str]]:
    """Map normalized weapon tokens → set of attachment-family tags found on meshes.

    Scans decompressed ``common.asr`` ZBB blocks for strings like
    ``Ammo_Pouch_G43``, ``ButtStock_Rubber_G43``, ``g43_beech_``, ``MG13_Magazine``.
    """
    path = Path(common_asr_path)
    if not path.is_file():
        return {}

    data = path.read_bytes()
    if data[:8] != b"AsuraZbb":
        return {}

    _val1, _val2, first_comp, _first_uncomp = struct.unpack_from("<IIII", data, 8)
    affinity: dict[str, set[str]] = defaultdict(set)

    def consider(s: str) -> None:
        sl = s.lower().replace("\\", "/")
        # weapon-suffixed attachment meshes
        m = re.search(
            r"(ammo_?pouch|buttstock|buttplate|cheekpad|magazine|barrel|"
            r"scope|foregrip|stock|band_heavy|kurz|mg13|beech|elm|walnut)"
            r"[_\-]?([a-z0-9]{2,20})",
            sl,
        )
        if m:
            family, token = m.group(1), m.group(2)
            # filter noise tokens
            if token in ("ar", "m", "n", "nm", "lod", "lng", "type", "a", "b",
                         "r", "l", "01", "02", "medium", "small", "large"):
                return
            affinity[token].add(family)
        # path style: weapons/rifles/g43/...
        m2 = re.search(r"weapons/(?:rifles|smg|pistols|shotguns)/([a-z0-9]+)/", sl)
        if m2:
            affinity[m2.group(1)].add("weapon_path")
        # g43_beech / g43_elm material variants
        m3 = re.search(r"\b([a-z0-9]{2,12})_(beech|elm|walnut)\b", sl)
        if m3:
            affinity[m3.group(1)].add(m3.group(2))

    offset = 24
    try:
        u0 = zlib.decompress(data[offset:offset + first_comp], 12)
    except Exception:
        try:
            u0 = zlib.decompress(data[offset:offset + first_comp], -15)
        except Exception:
            return {}
    for s in _ascii_strings(u0, 8):
        consider(s)
    offset += first_comp

    bidx = 1
    while offset + 8 < len(data) and bidx < 420:
        csize, _usize = struct.unpack_from("<II", data, offset)
        offset += 8
        if csize <= 0 or offset + csize > len(data):
            break
        try:
            ub = zlib.decompress(data[offset:offset + csize], 12)
        except Exception:
            try:
                ub = zlib.decompress(data[offset:offset + csize], -15)
            except Exception:
                offset += csize
                bidx += 1
                continue
        # only scan blocks that look string-rich for weapons
        if b"weapons" in ub or b"G43" in ub or b"attachment" in ub.lower():
            for s in _ascii_strings(ub, 8):
                if any(k in s.lower() for k in (
                    "g43", "kar98", "mosin", "m1903", "attachment",
                    "ammo_pouch", "buttstock", "beech", "elm", "magazine",
                )):
                    consider(s)
        offset += csize
        bidx += 1

    return dict(affinity)


def _weapon_mesh_tokens(weapon_name: str) -> set[str]:
    tokens = {_norm(weapon_name)}
    for t in WEAPON_MARKERS.get(weapon_name, []):
        tokens.add(_norm(t))
    # short forms
    n = weapon_name.lower()
    if "g43" in n:
        tokens.update({"g43", "gewehr"})
    if "kar98" in n.lower() or "kar98k" in n.lower():
        tokens.update({"kar98", "k98", "kar98k"})
    return tokens


# ── AMP → entity mapping ─────────────────────────────────────────────────

def map_amp_to_entity(
    amp_id: str,
    entities: set[str],
    weapon_name: str | None = None,
) -> str | None:
    """Map an AMP id to a concrete entity name present in *entities*."""
    if amp_id in AMMO_AMP_IDS:
        return None

    # Extended marksman → prefer this weapon's long barrel entity
    if amp_id == "EXTENDED_MARKSMAN_BARREL" and weapon_name:
        for cand in (
            f"{weapon_name}_LongBarrel",
            f"{weapon_name.replace('.', '')}_LongBarrel",
            "G43_LongBarrel" if "G43" in weapon_name else None,
            "Kar98K_LongBarrel" if "Kar98" in weapon_name else None,
            "Mosin_Nagant_LongBarrel" if "Mosin" in weapon_name else None,
            "SREM_LongBarrel" if weapon_name == "SREM" else None,
            "RSC1918_LongBarrel" if "RSC" in weapon_name else None,
            "M1Carbine_LongBarrel" if "Carbine" in weapon_name else None,
            "Type1_LongBarrel" if "Type1" in weapon_name else None,
            "Pedersen_LongBarrel" if "Peder" in weapon_name else None,
        ):
            if cand and cand in entities:
                return cand
        # fall through to generic if any

    seed = AMP_ENTITY_SEED.get(amp_id)
    if seed and seed in entities:
        return seed
    if seed:
        # seed known but entity not loaded yet — still return for registration
        return seed

    n = _norm(amp_id)
    ent_by_norm = {_norm(e): e for e in entities}
    if n in ent_by_norm:
        return ent_by_norm[n]

    # strip common role suffixes and retry
    for suf in (
        "receiver", "barrel", "magazine", "mag", "stock", "grip", "foregrip",
        "suppressor", "silencer", "muzzle", "scope", "construction", "choke",
        "rifle", "smg", "pistol", "shotgun",
    ):
        if n.endswith(suf) and len(n) > len(suf) + 2:
            base = n[: -len(suf)]
            if base in ent_by_norm:
                return ent_by_norm[base]

    # token overlap score
    tokens = [t for t in re.split(r"[_\d]+", amp_id) if len(t) >= 3]
    if not tokens:
        return None
    best: tuple[int, int, str] | None = None
    for e in entities:
        en = _norm(e)
        score = sum(1 for t in tokens if _norm(t) in en)
        if score >= max(2, (len(tokens) + 1) // 2):
            cand = (score, -len(e), e)
            if best is None or cand > best:
                best = cand
    return best[2] if best else None


# ── Other-weapon exclusion ───────────────────────────────────────────────

def _markers_for_weapon(weapon_name: str) -> set[str]:
    markers = set(WEAPON_MARKERS.get(weapon_name, []))
    markers.add(_norm(weapon_name))
    # variants without punctuation
    markers.add(_norm(weapon_name.replace(".", "")))
    return markers


def is_other_weapon_specific(label: str, weapon_name: str) -> bool:
    """True if *label* (AMP id or entity name) belongs to a different weapon."""
    n = _norm(label)
    my = _markers_for_weapon(weapon_name)

    for other_weapon, markers in WEAPON_MARKERS.items():
        if other_weapon == weapon_name:
            continue
        # same family silenced variants
        if weapon_name.startswith(other_weapon) or other_weapon.startswith(
            weapon_name.split("_")[0]
        ):
            if other_weapon.split("_")[0] == weapon_name.split("_")[0]:
                continue
        for m in markers:
            mn = _norm(m)
            if len(mn) < 3:
                continue
            if mn in n and mn not in my and not any(mn in mine for mine in my):
                # family exceptions (K98 bayonet / MG13 on G43, etc.)
                allowed = FAMILY_EXCEPTIONS.get(m, set()) | FAMILY_EXCEPTIONS.get(
                    mn, set()
                )
                if weapon_name in allowed:
                    continue
                # bayonets are shared across rifles even if named K98/M1905
                if "bayonet" in n:
                    continue
                return True
    return False


# Shotgun furniture / chokes that AMP SHARED + name-matching leak onto
# rifles, SMGs, and pistols. Token filter — not a per-weapon allow-list.
_SHOTGUN_ONLY_PART = re.compile(
    r"(choke|12g|buttplate|cheek_pad|cheekpad|shell_loops|bullet_loops|"
    r"smoothbore|buckshot|higins|sjogren|drilling|cuts_compensator)",
    re.I,
)
_SMG_ONLY_ON_PISTOL = re.compile(
    r"(smg_heavy_bolt|smg_lightened_bolt|austen_foregrip|owen_foregrip)",
    re.I,
)


def _rejected_for_class(entity: str, slot: str | None, wclass: str) -> bool:
    """True when *entity* is a different weapon class's furniture."""
    if wclass != "SHOTGUN" and _SHOTGUN_ONLY_PART.search(entity):
        return True
    if wclass == "PISTOL" and _SMG_ONLY_ON_PISTOL.search(entity):
        return True
    if wclass == "RIFLE" and slot == "Stock":
        if re.search(r"buttplate|cheek_pad|shell_loop|bullet_loop", entity, re.I):
            return True
    return False


# ── Slot detection ───────────────────────────────────────────────────────

def classify_slot(name: str, amp_id: str | None = None) -> str | None:
    # Prefer the entity name alone first — AMP ids can be misleading
    # (e.g. AMMOPOUCH_MAGS is a stock pouch, not a magazine).
    for source in (name, amp_id or ""):
        if not source:
            continue
        if re.search(r"defaultironsight|ironsight", source, re.I):
            return "Sight"
        if re.search(r"defaultmagazine", source, re.I):
            return "Magazine"
        if re.search(r"defaultbarrel", source, re.I):
            return "Barrel"
        if re.search(r"pouch", source, re.I):
            return "Stock"
        if re.search(r"hood", source, re.I):
            return "Foregrip"
        for slot, pat in SLOT_PATTERNS:
            if pat.search(source):
                return slot
    return None


# ── Main API ─────────────────────────────────────────────────────────────

def discover_game_paths(asrpatch_path: str | Path) -> dict[str, Path | None]:
    """Locate loadout dir and common.asr relative to an open asrpatch."""
    p = Path(asrpatch_path).resolve()
    # .../misc/common.asr.asrpatch → game root is parent of misc
    misc = p.parent
    game = misc.parent if misc.name.lower() == "misc" else misc
    loadout = game / "text" / "PC" / "LOADOUT"
    if not loadout.is_dir():
        # search upward
        loadout_found = None
        for parent in [game, *game.parents]:
            cand = parent / "text" / "PC" / "LOADOUT"
            if cand.is_dir():
                loadout_found = cand
                break
        loadout = loadout_found
    common = misc / "common.asr"
    if not common.is_file():
        common = None
    return {
        "game": game if game.is_dir() else None,
        "loadout": loadout if loadout and Path(loadout).is_dir() else None,
        "common_asr": common if common and Path(common).is_file() else None,
    }


def get_compatible_attachments(
    weapon_name: str,
    category_name: str,
    available_entities: set[str],
    *,
    loadout_dir: str | Path | None = None,
    common_asr_path: str | Path | None = None,
    include_weapon_prefix: bool = True,
) -> dict[str, list[str]]:
    """Return ``{slot: [entity_name, ...]}`` for *weapon_name*.

    Uses loadout AMP class pools + weapon-token filter + entity mapping.
    Falls back to weapon-prefix matching when loadout data is unavailable.
    """
    if category_name == "Special Weapons" or not CATEGORY_TO_CLASS.get(category_name):
        return {}
    result: dict[str, list[str]] = defaultdict(list)
    wclass = CATEGORY_TO_CLASS.get(category_name, "RIFLE")

    amp_pools: dict[str, set[str]] = {}
    if loadout_dir:
        try:
            amp_pools = load_amp_class_pools(str(loadout_dir))
        except Exception:
            amp_pools = {}

    # Candidate AMP ids for this class
    amp_ids: set[str] = set()
    if amp_pools:
        amp_ids |= amp_pools.get(wclass, set())
        amp_ids |= amp_pools.get("SHARED", set())
        # WEAPON_ATTACHMENT ids that look like this weapon
        try:
            for wa in load_weapon_attachment_ids(str(loadout_dir)):
                if _norm(weapon_name) in _norm(wa) or any(
                    _norm(m) in _norm(wa)
                    for m in WEAPON_MARKERS.get(weapon_name, [])
                ):
                    amp_ids.add(wa)
        except Exception:
            pass

    # Mesh affinity (optional boost / construction filter)
    affinity: dict[str, set[str]] = {}
    if common_asr_path:
        try:
            affinity = scan_mesh_weapon_affinity(str(common_asr_path))
        except Exception:
            affinity = {}
    my_tokens = _weapon_mesh_tokens(weapon_name)
    my_families: set[str] = set()
    for tok in my_tokens:
        my_families |= affinity.get(tok, set())
        my_families |= affinity.get(tok[:3], set()) if len(tok) >= 3 else set()

    # Never treat weapons themselves as attachments
    try:
        from asr import ALL_WEAPON_ENTITY_SET
        weapon_entities = set(ALL_WEAPON_ENTITY_SET)
    except Exception:
        weapon_entities = set()

    chosen: set[str] = set()

    def add(entity: str, slot: str | None, amp: str | None = None) -> None:
        if entity not in available_entities:
            return
        if entity in chosen:
            return
        if entity in weapon_entities:
            return
        if is_other_weapon_specific(entity, weapon_name):
            return
        s = slot or classify_slot(entity, amp)
        if not s:
            return
        if _rejected_for_class(entity, s, wclass):
            return
        # Hard gate scopes by faction (even if AMP pool or name-match added them)
        if s == "Sight" and "ironsight" not in entity.lower():
            if not scope_allowed_for_weapon(entity, weapon_name):
                return
        # Construction mesh affinity: only exclude when we positively saw
        # wood families for this weapon (beech/elm) and this material is absent.
        if s == "Construction" and my_families:
            woods = my_families & {"beech", "elm", "walnut"}
            if woods:
                el = entity.lower()
                if "beech" in el and "beech" not in woods:
                    return
                if "elm" in el and "elm" not in woods:
                    return
                if "walnut" in el and "walnut" not in woods:
                    return
        chosen.add(entity)
        result[s].append(entity)

    # 1) AMP pool
    for amp in sorted(amp_ids):
        if is_other_weapon_specific(amp, weapon_name):
            continue
        if amp in AMMO_AMP_IDS:
            continue
        ent = map_amp_to_entity(amp, available_entities, weapon_name)
        if ent:
            add(ent, classify_slot(ent, amp), amp)

    # 1b) Family extras not always AMP-class-tagged (MG13 trench on G43, etc.)
    for marker, weapons in FAMILY_EXCEPTIONS.items():
        if weapon_name not in weapons:
            continue
        if marker in ("mg13",):
            add("Mg13_trench", "Magazine", "MG13_TRENCH")

    # 1c) Scopes by faction — NOT "all scopes on all rifles"
    # Unclassed AMP scope ids (A1, ZF39, …) + faction pools.
    if wclass in ("RIFLE", "SMG"):
        # From AMP ids that mention scopes (including unclassed)
        if loadout_dir:
            try:
                for wa in load_weapon_attachment_ids(str(loadout_dir)):
                    ent = SCOPE_AMP_ENTITY.get(wa) or map_amp_to_entity(
                        wa, available_entities, weapon_name
                    )
                    if ent and "scope" in ent.lower() or ent and ent in SCOPE_FACTION:
                        if ent and scope_allowed_for_weapon(ent, weapon_name):
                            add(ent, "Sight", wa)
            except Exception:
                pass
            # Unclassed AMP scope keys (AMP_A1_OC_DESC has no _RIFLE_ suffix)
            try:
                pools = amp_pools or {}
                # also scan raw unclassed ids from seed map
                for amp_id, ent in SCOPE_AMP_ENTITY.items():
                    if scope_allowed_for_weapon(ent, weapon_name):
                        add(ent, "Sight", amp_id)
            except Exception:
                pass
        # Faction pool (covers ZF4 / PK Berlin which lack AMP class tags)
        for sc, factions in SCOPE_FACTION.items():
            if scope_allowed_for_weapon(sc, weapon_name):
                add(sc, "Sight")

    # 2) Weapon-prefix / name-matching entities
    if include_weapon_prefix:
        terms = [_norm(weapon_name)]
        for v in WEAPON_MARKERS.get(weapon_name, []):
            terms.append(_norm(v))
        terms = [t for t in terms if len(t) >= 3]
        for ent in available_entities:
            if ent in weapon_entities:
                continue
            en = _norm(ent)
            if any(t in en for t in terms):
                if en == _norm(weapon_name):
                    continue
                add(ent, classify_slot(ent))

    # ── Dedupe: same in-game loc label / identity → one UI entry ────────
    # Also build alias map so edits can fan out to every entity version.
    prop_counts: dict[str, int] = {}
    try:
        from gui.vanilla_defaults import load_defaults
        prop_counts = {n: len(p) for n, p in load_defaults().items()}
    except Exception:
        prop_counts = {}
    meta: dict = {}
    try:
        from gui.game_loc import load_entity_meta
        from gui.display_names import set_game_loc_names

        # common.asr → sibling common.asr.asrpatch
        asrpatch = None
        if common_asr_path:
            sibling = Path(str(common_asr_path) + ".asrpatch")
            if sibling.is_file():
                asrpatch = str(sibling)
        if asrpatch or common_asr_path:
            meta = load_entity_meta(
                asrpatch or "",
                str(common_asr_path) if common_asr_path else None,
                str(loadout_dir) if loadout_dir else None,
            )
            loc_names = {
                n: m.display_name
                for n, m in meta.items()
                if m.display_name
            }
            if loc_names:
                set_game_loc_names(loc_names)
    except Exception:
        meta = {}

    global _LAST_ALIASES
    _LAST_ALIASES = {}

    order = {
        "RIFLE": RIFLE_SLOT_ORDER,
        "SHOTGUN": SHOTGUN_SLOT_ORDER,
        "SMG": SMG_SLOT_ORDER,
        "PISTOL": PISTOL_SLOT_ORDER,
    }.get(wclass, RIFLE_SLOT_ORDER)

    ordered: dict[str, list[str]] = {}
    for slot in order:
        if slot not in result:
            continue
        items = list(set(result[slot]))
        if meta:
            try:
                from gui.game_loc import dedupe_entities
                reps, aliases = dedupe_entities(items, meta, prop_counts)
                ordered[slot] = reps
                for rep, group in aliases.items():
                    _LAST_ALIASES[rep] = group
            except Exception:
                ordered[slot] = sorted(items)
        else:
            # Fallback: collapse by display-name string
            from gui.display_names import get_display_name
            by_label: dict[str, list[str]] = {}
            for e in items:
                by_label.setdefault(get_display_name(e).lower(), []).append(e)
            reps = []
            for _lab, group in by_label.items():
                # prefer entity with more properties if we know them
                group_sorted = sorted(
                    group,
                    key=lambda n: (
                        0 if not re.search(r"_(Sjogren|Drilling|M12)$", n) else -1,
                        prop_counts.get(n, 0),
                    ),
                    reverse=True,
                )
                rep = group_sorted[0]
                reps.append(rep)
                _LAST_ALIASES[rep] = group_sorted
            ordered[slot] = sorted(reps)

    for slot, items in sorted(result.items()):
        if slot not in ordered:
            ordered[slot] = sorted(set(items))
    return collapse_slots_by_display_name(ordered, prop_counts)


# Populated by the last get_compatible_attachments() call: rep → all aliases
_LAST_ALIASES: dict[str, list[str]] = {}


def collapse_slots_by_display_name(
    slot_map: dict[str, list[str]],
    prop_counts: dict[str, int] | None = None,
) -> dict[str, list[str]]:
    """Merge parts that share an in-game display name within each slot.

    Two entities labelled "Heavy Parkerized" on the same weapon become one
    dropdown entry; writes still fan out to every linked entity via
    ``_LAST_ALIASES``.
    """
    from gui.display_names import get_display_name

    global _LAST_ALIASES
    prop_counts = prop_counts or {}
    out: dict[str, list[str]] = {}
    for slot, names in slot_map.items():
        groups: dict[str, list[str]] = {}
        for n in names:
            label = (get_display_name(n) or n).strip().lower()
            groups.setdefault(label or n.lower(), []).append(n)
        reps: list[str] = []
        for _lab, members in groups.items():
            members_sorted = sorted(
                members,
                key=lambda n: (
                    prop_counts.get(n, 0),
                    0 if not re.search(r"_(Sjogren|Drilling|M12)$", n) else -1,
                    -len(n),
                ),
                reverse=True,
            )
            rep = members_sorted[0]
            merged: list[str] = []
            seen: set[str] = set()
            for m in members_sorted:
                extras = _LAST_ALIASES.get(m) or [m]
                for x in extras:
                    if x not in seen:
                        seen.add(x)
                        merged.append(x)
                if m not in seen:
                    seen.add(m)
                    merged.append(m)
            reps.append(rep)
            _LAST_ALIASES[rep] = merged
        out[slot] = sorted(reps)
    return out


def get_aliases_for(entity: str) -> list[str]:
    """Entities that should receive the same property writes as *entity*."""
    if entity in _LAST_ALIASES:
        return list(_LAST_ALIASES[entity])
    for rep, group in _LAST_ALIASES.items():
        if entity in group:
            return list(group)
    return [entity]


def describe_discovery_sources(
    loadout_dir: str | Path | None,
    common_asr_path: str | Path | None,
) -> str:
    """Human-readable summary of what was found in game files."""
    lines = []
    if loadout_dir and Path(loadout_dir).is_dir():
        pools = load_amp_class_pools(str(loadout_dir))
        lines.append(
            "Loadout AMP pools: "
            + ", ".join(f"{c}={len(v)}" for c, v in sorted(pools.items()))
        )
        lines.append(
            f"WEAPON_ATTACHMENT ids: {len(load_weapon_attachment_ids(str(loadout_dir)))}"
        )
    else:
        lines.append("Loadout dir: not found (using entity name-matching only)")
    if common_asr_path and Path(common_asr_path).is_file():
        aff = scan_mesh_weapon_affinity(str(common_asr_path))
        lines.append(f"Mesh affinity tokens: {len(aff)}")
    else:
        lines.append("common.asr: not scanned for mesh affinity")
    return "\n".join(lines)
