"""Asura engine ASR/ASRpatch file reader and writer.

Handles the AsuraZlb container format used by Sniper Elite 5:
  - 8-byte magic ("AsuraZlb")
  - 4-byte flags (0)
  - 4-byte compressed size
  - 4-byte uncompressed size
  - zlib-compressed body (wbits=13)

The body is a binary entity database. Properties are stored as 12-byte
tuples: [type:4][value:4][hash:4]. Properties are NOT necessarily aligned
to 4-byte boundaries, so scanning must be byte-by-byte.

Property types:
  - type 0: int32  [0:4=type=0][4:8=int_value][8:12=hash]
  - type 1: float32 [0:4=type=1][4:8=float_value][8:12=hash]
  - type 4: string  [0:4=type=4][4:8=length][8:8+length=ascii_data]
  - type 2: vec2    [0:4=type=2][4:12=2xfloat][12:16=hash]
  - type 3: vec3    [0:4=type=3][4:16=3xfloat][16:20=hash]

Property hashes are 32-bit identifiers. Known hashes are mapped to
human-readable names in the HASH_NAMES dictionary.
"""
from __future__ import annotations

import bisect
import os
import struct
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

# ── Container magic ──────────────────────────────────────────────────────

MAGIC_ZLB = b"AsuraZlb"
MAGIC_ZBB = b"AsuraZbb"
# Uncompressed Asura archive (the *inner* payload of a ZLB file).
# Some tools / installs leave common.asr.asrpatch in this form (~17 MB).
MAGIC_RAW = b"Asura   "

# ── Property type tags ────────────────────────────────────────────────────

TYPE_INT = 0
TYPE_FLOAT = 1
TYPE_VEC2 = 2
TYPE_VEC3 = 3
TYPE_STRING = 4

# ── Known property hashes ────────────────────────────────────────────────
# Working names from value comparison + loc tags. Several are confirmed
# NOT to mean what the name suggests in combat (see WEAPONS.md):
#   Damage / DamageSpread / DamageDropoff = listed scores, two encodings
#   DamageMod = real gunsmith “power / damage” multiplier on parts/ammo

# Core weapon / scope stats — safe to search in any entity window.
CORE_HASH_NAMES: Dict[int, str] = {
    0x19B61B3D: "EffectiveRange",
    0x8C6EF316: "MuzzleVelocity",
    0xFFEBCB07: "Damage",
    0x171B12B6: "DamageSpread",
    0xACB8EA97: "WindDrop",
    0x2699E6A9: "RPM",
    0x22983F6D: "FireRate",
    0x680784A9: "Recoil1_Vertical",
    0xB9CBCCB9: "Recoil2_Horizontal",
    0x6539B743: "RecoilMult",
    0x99CBF4DF: "RecoilRecoveryTime",
    0x19878633: "RecoilResetSpeed",
    0x62CC2933: "ZoomMin",
    0xC0104A2C: "ZoomMax",
    0xC96F3E4D: "ZoomMax2",
    0xF71A01A6: "ScopeInSpeed",
    0x4EA793D6: "SwayAmount",
    0xD1F1115E: "SwayRecovery",
    0xCE5406BF: "SwayDrift",
    0x3D7EB22E: "SwayDecay",
    0xDA8BB27B: "AimStability",
    0x57C43583: "ScopeSteadyTime",
    0x9C221933: "HoldBreathDuration",
    0xA3476A93: "SwayPerShot",
    0x2E359A4B: "SwayWalk",
    0x8A4BDCE4: "SwayCrouch",
    0x2C504024: "SwayProne",
    0x83BC523F: "DamageDropoff",
    0x78EFCCCF: "AudibleRangeBase",
    # int on weapons/mags; float multiplier on many attachments
    0x807AAE98: "MagazineCapacity",
}

# Attachment-only modifier hashes.  Searching these in a *weapon* window
# produces false positives (same 4-byte patterns appear in unrelated data).
# They are resolved via consecutive-walk on attachment entities only.
ATTACHMENT_MOD_HASH_NAMES: Dict[int, str] = {
    0xB9CBCCBA: "RecoilHorizontalMod",
    0x325ECD81: "LoudnessMod",
    0xD02587AE: "DamageMod",
    0xD02587AF: "DamageModB",
    0xC1B46824: "MobilityMod",
    0x368B80FC: "HandlingMod",
    0x43760D85: "StabilityMod",
    0x0647B364: "ControlMod",
    0x8C39BE2C: "DropMod",
    0xDCE39C2D: "VelocityMod",
    0x880BFFF2: "RangeMod",
    0x629C73C3: "SwayMod",
    0xEC89DDC2: "RecoilRecoveryMod",
    0x3894DC05: "AimSpeedMod",
    0xC3E52455: "HipfireMod",
    0x9D89AD85: "SpreadMod",
    0xEFE0D7FC: "ZoomStabilityMod",
    0xE31BAAA1: "FireRateMod",
    0x582896DA: "CycleTimeMod",
    0xCBE77E9C: "BulletDropMod",
    0xD874D19C: "PenetrationMod",
    0x13CD1D62: "AimStabilityMod",
    0xEF81B876: "ScopeInMod",
    0x1126C10F: "FollowUpMod",
    0x0D60FBAC: "AdsMoveMod",
    0x7D9993E4: "StrafeMod",
    0x00A32AA1: "PowerMod",
    0xCA7DA0A2: "KickMod",
    0x082B4B64: "GripMod",
    0x48B358A3: "BurstMod",
    0x3B6C121A: "ClimbMod",
    0xA7DE39B3: "FlinchMod",
    0xC176A208: "CompensatorMod",
    0x0AA487A0: "MuzzleMod",
    0x4F751A01: "BrakeMod",
    0x83734569: "MassMod",
    0xD10AACCC: "BarrelHarmonicsMod",
    0xDD7DA326: "HeatMod",
    0xE2611FF6: "PressureMod",
    0xD96B7BF1: "BoltMod",
    0xD5E95021: "GasMod",
    0x73F37068: "LighteningMod",
    0x6E14C492: "BalanceMod",
    0x55F9257E: "ChokeModA",
    0xCB385E6F: "ChokeModB",
    0x84043BEC: "ChokeModC",
    0x6F7E9717: "ChokeModD",
    0x8C9D7CA7: "ChokeModE",
    0x1A4FCB0F: "ReceiverMod",
    0x7BE3A4FD: "PatternMod",
    0xEA085D03: "FlashMod",
    0x8633AD48: "BaffleMod",
}

# Combined lookup (editing / display)
HASH_NAMES: Dict[int, str] = {**CORE_HASH_NAMES, **ATTACHMENT_MOD_HASH_NAMES}

# Reverse lookup: name -> hash
NAME_TO_HASH: Dict[str, int] = {v: k for k, v in HASH_NAMES.items()}

# Human-readable labels for the UI (falls back to the hash name).
PROP_LABELS: Dict[str, str] = {
    "EffectiveRange": "Effective Range",
    "MuzzleVelocity": "Muzzle Velocity",
    "Damage": "Listed Damage",
    "DamageSpread": "2nd Score / Spread",
    "WindDrop": "Wind Drop",
    "RPM": "RPM",
    "FireRate": "Fire Rate",
    "Recoil1_Vertical": "Recoil (Vertical)",
    "Recoil2_Horizontal": "Recoil (Horizontal)",
    "RecoilMult": "Recoil Multiplier",
    "RecoilRecoveryTime": "Recoil Recovery Time",
    "RecoilResetSpeed": "Recoil Reset Speed",
    "ZoomMin": "Zoom Min",
    "ZoomMax": "Zoom Max",
    "ZoomMax2": "Zoom Max 2",
    "ScopeInSpeed": "Scope-In Speed",
    "SwayAmount": "Sway Amount",
    "SwayRecovery": "Sway Recovery",
    "SwayDrift": "Sway Drift",
    "SwayDecay": "Sway Decay",
    "AimStability": "Aim Stability",
    "ScopeSteadyTime": "Scope Steady Time",
    "HoldBreathDuration": "Hold Breath Duration",
    "SwayPerShot": "Sway Per Shot",
    "SwayWalk": "Sway (Walking)",
    "SwayCrouch": "Sway (Crouching)",
    "SwayProne": "Sway (Prone)",
    "DamageDropoff": "Drop-off / Alt. Score",
    "AudibleRangeBase": "Audible Range",
    "MagazineCapacity": "Magazine Capacity",
    "RecoilHorizontalMod": "Recoil Horizontal (mod)",
    "LoudnessMod": "Loudness (mod)",
    "DamageMod": "Power ×",
    "DamageModB": "Power × B",
    "MobilityMod": "Mobility (mod)",
    "HandlingMod": "Handling (mod)",
    "StabilityMod": "Stability (mod)",
    "ControlMod": "Control (mod)",
    "DropMod": "Drop (mod)",
    "VelocityMod": "Velocity (mod)",
    "RangeMod": "Range (mod)",
    "SwayMod": "Sway (mod)",
    "RecoilRecoveryMod": "Recoil Recovery (mod)",
    "AimSpeedMod": "Aim Speed (mod)",
    "HipfireMod": "Hipfire (mod)",
    "SpreadMod": "Spread (mod)",
    "FireRateMod": "Fire Rate (mod)",
    "CycleTimeMod": "Cycle Time (mod)",
    "BulletDropMod": "Bullet Drop (mod)",
    "PenetrationMod": "Penetration ×",
    "AimStabilityMod": "Aim Stability (mod)",
    "ScopeInMod": "Scope-In (mod)",
    "PowerMod": "Power (mod)",
    "KickMod": "Kick (mod)",
    "CompensatorMod": "Compensator (mod)",
    "MuzzleMod": "Muzzle (mod)",
    "BrakeMod": "Brake (mod)",
    "LighteningMod": "Lightening (mod)",
    "ChokeModA": "Choke Mod A",
    "ChokeModB": "Choke Mod B",
    "ChokeModC": "Choke Mod C",
    "ChokeModD": "Choke Mod D",
    "ChokeModE": "Choke Mod E",
    "PatternMod": "Pattern (mod)",
    "BalanceMod": "Balance (mod)",
    "HeatMod": "Heat (mod)",
    "PressureMod": "Pressure (mod)",
    "BarrelHarmonicsMod": "Barrel Harmonics (mod)",
    "FollowUpMod": "Follow-Up (mod)",
    "AdsMoveMod": "ADS Move (mod)",
    "StrafeMod": "Strafe (mod)",
    "GripMod": "Grip (mod)",
    "BurstMod": "Burst (mod)",
    "ClimbMod": "Climb (mod)",
    "FlinchMod": "Flinch (mod)",
    "BoltMod": "Bolt (mod)",
    "GasMod": "Gas (mod)",
    "ReceiverMod": "Receiver (mod)",
    "FlashMod": "Flash (mod)",
    "BaffleMod": "Baffle (mod)",
    "ZoomStabilityMod": "Zoom Stability (mod)",
}


def prop_label(name: str) -> str:
    """UI label for a property name."""
    return PROP_LABELS.get(name, name)


# ── Property dataclasses ─────────────────────────────────────────────────

@dataclass
class Property:
    """A single typed property in the entity database."""
    type: int
    offset: int  # byte offset in the decompressed body (-1 if base-only)
    hash: int
    name: str = ""
    value: Union[int, float, str, Tuple[float, ...]] = 0
    # "patch" = lives in the loaded asrpatch body (editable)
    # "base"  = filled from sibling common.asr (read-only unless also in patch)
    source: str = "patch"

    @property
    def is_float(self) -> bool:
        return self.type == TYPE_FLOAT

    @property
    def is_int(self) -> bool:
        return self.type == TYPE_INT

    @property
    def is_string(self) -> bool:
        return self.type == TYPE_STRING

    @property
    def editable(self) -> bool:
        """True when this property can be written back into the loaded file."""
        return self.source == "patch" and self.offset >= 0

    def display_value(self) -> str:
        if self.is_string:
            return str(self.value)
        if self.is_float:
            return f"{self.value:.4f}"
        return str(self.value)


@dataclass
class Entity:
    """A named entity found in the ASR body (e.g. a weapon or scope)."""
    name: str
    name_offset: int  # offset of the string in the body
    properties: List[Property] = field(default_factory=list)

    def get(self, hash_or_name: Union[int, str]) -> Optional[Property]:
        """Find the first property matching the given hash or name.

        If multiple properties share the same hash (e.g. duplicate
        MagazineCapacity entries from child entities), only the first
        match is returned.  Use ``get_all`` to retrieve every match.
        """
        if isinstance(hash_or_name, str):
            # Match by property .name first (covers Mod_0x… unknowns)
            for p in self.properties:
                if p.name == hash_or_name:
                    return p
            hash_or_name = NAME_TO_HASH.get(hash_or_name, 0)
            if hash_or_name == 0:
                return None
        for p in self.properties:
            if p.hash == hash_or_name:
                return p
        return None

    def get_all(self, hash_or_name: Union[int, str]) -> List[Property]:
        """Find all properties matching the given hash or name.

        Some entities may have multiple properties with the same hash
        (e.g. multiple MagazineCapacity entries from child entities).
        This method returns every match, sorted by byte offset.
        """
        if isinstance(hash_or_name, str):
            by_name = [p for p in self.properties if p.name == hash_or_name]
            if by_name:
                return sorted(by_name, key=lambda p: p.offset)
            hash_or_name = NAME_TO_HASH.get(hash_or_name, 0)
            if hash_or_name == 0:
                return []
        return sorted(
            [p for p in self.properties if p.hash == hash_or_name],
            key=lambda p: p.offset,
        )

    def get_float(self, hash_or_name: Union[int, str]) -> Optional[float]:
        p = self.get(hash_or_name)
        if p and p.is_float:
            return p.value
        return None

    def get_int(self, hash_or_name: Union[int, str]) -> Optional[int]:
        p = self.get(hash_or_name)
        if p and p.is_int:
            return p.value
        return None


# ── Known entity names ───────────────────────────────────────────────────
#
# Categories mirror the in-game loadout slots (Primary / Secondary / Pistol).
# Some DLC / special weapons sit in the slot that best matches their role.

# Primary weapons (sniper rifles and carbines)
RIFLE_ENTITIES = [
    # Base-game primaries
    "M1903", "SREM", "Kar98K", "G43", "M1Carbine", "RSC1918",
    # DLC / expansion primaries
    "Mosin_Nagant", "DLC_Mosin", "Lee_Enfield", "M1_Enfield",
    "Winchester_1885", "Pedersen", "Type1", "Delisle",
    # Silenced / special configurations
    "G43_Kurz_Silenced",
]

# Shotguns (primary or secondary smoothbores)
SHOTGUN_ENTITIES = [
    "Sjogren",       # Sjögren Inertia (primary shotgun)
    "Drilling",      # M30 Drilling (primary)
    "M12",           # Model 1912 (secondary shotgun)
    "Auto_Burglar",  # Auto Burglar (shotgun-pistol secondary)
]

# Pistols (sidearms)
PISTOL_ENTITIES = [
    "M1911", "M1911_Plus", "Luger", "Luger_Suppressed",
    "Nambu", "Webley", "Welrod", "Mk1_Welrod", "Mk2_Welrod",
    "Derringer", "M712", "ModelD",
    # Short names previously missed by the str_len > 3 filter
    "HDM",   # High Standard .22 (HS.22)
    "P38",   # Walther P38
]

# SMGs and automatic secondaries
SMG_ENTITIES = [
    "GreaseGun", "StenMkII", "Welgun", "MP.40", "MP.44",
    "SuperTommy", "Thompson_Plus",
    # Base-game / DLC secondaries previously mis-filed as rifles
    "Thompson", "PPSH", "Type100", "Gustaf",
    # Short name previously missed by the str_len > 3 filter
    "EMP",   # ERMA.36 (suppressed SMG)
]

# Special / level-only weapons (not in the pre-mission gunsmith).
# Panzerfaust and Pzb39 are mission pickups. MG42 is WEAPON_SPECIAL_MG42
# (found heavy MG) — it is not an SMG workbench gun.
SPECIAL_WEAPON_ENTITIES = [
    "Pzb39", "Panzerfaust", "MG42",
]

# Scopes
SCOPE_ENTITIES = [
    "M81_Scope", "M84_Scope", "A1_Optical", "A2_Optical",
    "No32_Mk1_Scope", "No32_Mk2_Scope", "A5_Winchester_Scope",
    "B4_Scope", "ZF41_Scope", "Zf4_scope", "PU_scope",
    "T99_Scope", "T97_Scope", "M1913_Scope",
    # Additional scopes present in asrpatch but previously unlisted
    "Model2_Night_Vision_Scope", "PK_Berlin_Scope", "PPCo_Scope",
    "Zf39_Scope", "Type99_LMG_Scope", "PU_scope_Mosin",
]

# Suppressors
SUPPRESSOR_ENTITIES = [
    "Maxin_30_Suppressor", "Maxin_1910_Suppressor", "Moore_Suppressor",
    "Bramit_Suppressor", "Hub_23_Suppressor", "OSS_Suppressor",
    "Sten_Mk2_Special_Silencer",
]

# Barrels
BARREL_ENTITIES = [
    "Delisle_DefaultBarrel", "Delisle_LongBarrel", "Delisle_ShortBarrel",
    "EMP_Default_Barrel", "EMP_LongBarrel", "EMP_UnSuppressedBarrel",
    "G43_DefaultBarrel", "G43_LongBarrel",
    "GreaseGun_FlashHiderBarrel", "GreaseGun_LongBarrel",
    "Gustaf_DefaultBarrel", "Gustaf_SuppressedBarrel", "Gustaf_UnshroudedBarrel",
    "Kar98K_DefaultBarrel", "Kar98K_LongBarrel", "kar98K_CarbineBarrel",
    "M1903_DefaultBarrel", "M1903_ShortBarrel",
    "M1Carbine_DefaultBarrel", "M1Carbine_LongBarrel",
    "Mosin_Nagant_DefaultBarrel", "Mosin_Nagant_LongBarrel",
    "Pedersen_LongBarrel", "Pedersen_ShortBarrel", "Pederson_DefaultBarrel",
    "RSC1918_DefaultBarrel", "RSC1918_LongBarrel", "RSC1918_ShortBarrel",
    "SREM_DefaultBarrel", "SREM_LongBarrel", "SREM_ShortBarrel",
    "Type1_LongBarrel", "Type1_ShortBarrel",
    "Winchester_1885_DefaultBarrel",
    # Generic barrel upgrades
    "Blued_Lightened_Barrel", "Default_Barrel", "Extended_Artillery_Barrel",
    "Extended_Carbine_Barrel", "Heat_Sink_Barrel", "Heavy_Barrel_Bands",
    "Lightened_Barrel", "Lightened_Blued_Shotgun_Barrel",
    "Parkerized_Heavy_Barrel", "Reinforced_Barrel", "Smoothbore_Barrel",
    "Starguage_Barrel", "Precision_Rifled_Barrel", "OSS_Rifled_Barrel",
    "Rifled_Barrel_and_Sight",
]

# Magazines
MAGAZINE_ENTITIES = [
    "Auto_Burglar_DefaultMagazine", "Colt_M1911_DefaultMagazine",
    "Colt_Stealth_DefaultMagazine", "Delisle_DefaultMagazine",
    "Drilling_DefaultMagazine", "G43_DefaultMagazine",
    "GreaseGun_DefaultMagazine", "Gustaf_DefaultMagazine",
    "Kar98k_DefaultMagazine", "Luger_DefaultMagazine",
    "M1_Carbine_DefaultMagazine", "MG42_DefaultMagazine",
    "MP40_DefaultMagazine", "MP44_DefaultMagazine",
    "Mauser_M712_DefaultMagazine", "ModelD_DefaultMagazine",
    "Mosin_DefaultMagazine", "Mosin_Nagant_DefaultMagazine",
    "Nambu_DefaultMagazine", "PPSh_DefaultMagazine",
    "Pederson_DefaultMagazine", "RSC1918_DefaultMagazine",
    "SREM_DefaultMagazine", "Sjogren_DefaultMagazine",
    "Snail_Magazine", "Springfield_DefaultMagazine",
    "StenMkII_DefaultMagazine", "StenMkV_DefaultMagazine",
    "Thompson_DefaultMagazine", "Type100_DefaultMagazine",
    "Webley_DefaultMagazine", "Welgun_DefaultMagazine",
    "Welrod_DefaultMagazine", "Welrod_Variant_DefaultMagazine",
    "Winchester_1885_DefaultMagazine", "m12_DefaultMagazine",
    # Level-only AT rifle ammo pool (not a gunsmith magazine)
    "Pzb39Ammo",
    # Found-MG pickup with a halved belt
    "MG42(HalfAmmo)",
    "Quad_M31_Magazine", "Quad_M31_Magazine_Carl_Gustaf",
    "Quad_M31_Magazine_Sten", "Quad_M31_Magazine_Sten_EMP",
    # Extended / conversion magazines previously unlisted
    "Reduced_load_magazine", "Large_9mm_Stick", "Large_Extended_Single_Stack",
    "Medium_Extended_Single_Stack", "Small_Stick", "PPlus_Stick",
    "30rd_Thompson_Stick", "25Rd_Marksmen_Mp44_Mag", "PPSH_50d_Drum",
    "100rd_Drum", "11rd_Delisle", "20rd_delisle", "M1_10rd",
    # Named magazine conversions (were previously mis-listed as weapons)
    "1903_Trench", "GEW_98_Overpressure", "Geret_06_Experimental_P_Plus",
    # Discovered in common.asr entity table (G43 / shared rifle mags)
    "Kurz_Conversion", "Mg13_trench", "Magazine_pouch",
]

# Ironsights
IRONSIGHT_ENTITIES = [
    "Auto_Burglar_DefaultIronsight", "Colt_M1911_DefaultIronsight",
    "Delisle_DefaultIronsight", "Derringer_DefaultIronsight",
    "Drilling_DefaultIronsight", "EMP_DefaultIronsight",
    "G43_DefaultIronsight", "GreaseGun_DefaultIronsight",
    "Gustav_DefaultIronsight", "HDM_DefaultIronsight",
    "Kar98k_DefaultIronsight", "Luger_DefaultIronsight",
    "M12_DefaultIronsight", "M1Carbine_DefaultIronsight",
    "MP40_DefaultIronsight", "MP44_DefaultIronsight",
    "Mauser_M712_DefaultIronsight", "ModelD_DefaultIronsight",
    "Nambu_DefaultIronsight", "PPSH_DefaultIronsight",
    "RSC1918_DefaultIronsight", "SREM_DefaultIronsight",
    "Sjogren_DefaultIronsight", "StenMKII_DefaultIronsight",
    "StenMkV_DefaultIronsight", "Thompson_DefaultIronsight",
    "Type100_DefaultIronsight", "Type1_DefaultIronsight",
    "Webley_DefaultIronsight", "Welrod_DefaultIronsight",
    "Winchester_1885_Ironsight", "welgun_DefaultIronsight",
]

# Chokes (shotgun-specific)
CHOKE_ENTITIES = [
    "Adapted_Higins_Full_Choke", "Adapted_Higins_Full_Choke_Drilling",
    "Adapted_Higins_Full_Choke_Sjogren",
    "Cuts_Full_Choke", "Cuts_Full_Choke_Drilling", "Cuts_Full_Choke_Sjogren",
    "Cuts_Modified_Choke", "Cuts_Modified_Choke_Drilling",
    "Cuts_Modified_Choke_Sjogren",
    "Improved_Cylinder_Choke", "Improved_Cylinder_Choke_Sjogren",
    "Power_Hyrbid_Choke",
]

# Other attachments (stocks, grips, muzzle brakes, bayonets, etc.)
# Shotgun stock / furniture — in-game STOCK slot (buttplates, pads, loops)
SHOTGUN_STOCK_ENTITIES = [
    "Heavy_Steel_Buttplate",   # Heavy Buttplate
    "Rubber_Buttplate",        # Rubber Buttplate
    "Leather_cheek_pad",       # Leather Pad
    "Wooden_Cheek_Pad",        # Wooden Pad
    "Shotgun_Shell_Loops",     # Shell Loops
    "Bullet_Loops",
    "leather_Loader",
]

# Receiver / assembly slot (in-game RECEIVER)
RECEIVER_ENTITIES = [
    "Heavy_Steel_Assembly",        # Heavy Steel Assembly
    "Lightened_Firing_Mechanism",  # Lightened Assembly
    "Lightened_Elm_Construction",
    "Quick_Load_Mod",              # Quick Load Mod (has stats)
    "Quick_Load_Mod_Sjogren",      # unlock stub (often empty)
    "Quick_Load_Mod_M12",
    "SMG_Lightened_Bolt",
    "SMG_Heavy_Bolt",
    "Precision_Receiver",
    "Reinforced_Overpressure_Receiver",
]

OTHER_ATTACHMENT_ENTITIES = [
    # Rifle / SMG stocks
    "Featherweight_Stock", "GreaseGun_DefaultStock", "Gustaf_DefaultStock",
    "Heavy_Mp44_Stock", "Heavy_Wooden_Stock", "Lightweight_Frame_Stock",
    "Standard_Sten_Stock", "Stock_Removal",
    "Lightweight_712s",
    "Heavy_Walnut_Construction", "Heavy_Oak",
    "Laminated_Beech_Construction", "Fixed_Frame",
    # Shotgun furniture + receivers
    *SHOTGUN_STOCK_ENTITIES,
    *RECEIVER_ENTITIES,
    # Foregrips
    "Austen_Foregrip", "EMP_Foregrip", "Owen_Foregrip",
    "Reinforced Foregrip Bands", "Remove_Foregrip", "US_1911_Foregrip",
    # Grips
    "Sten_Mk5_Grip", "X3_Grip_Tape", "X6_Grip_Tape",
    "Ridged_Pistol_Handgrip", "Ridged_SMG_Handgrip",
    "Tactical_Pistol_Handgrip", "Tactical_SMG_Handgrip",
    "Tanned_draw_grip",
    # Muzzle brakes / compensators
    "Axis_mk2_MuzzleBrake", "Mclean_Muzzlebrake",
    "Mk1_Boys_MuzzleBreak", "Mk2_Boys_MuzzleBreak", "USGI_MuzzleBreak",
    "FG_Compensator", "Halcon_Compensator",
    "Shotgun_12G_Compensator", "Shotgun_12G_Compensator_Sjogren",
    "Modified_12G_Compensator", "SS_Flash_Hider",
    # Bayonets
    "Rifle_Bayonet_1",
    # Extra furniture / muzzle pieces found in common.asr entity table
    "Magazine_pouch",
    "Leather_Hood",
    "Foxley_Silencer",
    "USGI_Flash_Hider",
    "Flared_Flash_Hider",
    "Cuts_Compensator",
    "Remove_Baffles",
    "Solid_Baffles",
    "Sstandard_Baffles",
    "SMG_Model_27_Silencer",
]

# Suffixes for pattern matching (kept for reference)
BARREL_SUFFIXES = [
    "_DefaultBarrel", "_ShortBarrel", "_LongBarrel", "_CarbineBarrel",
    "_UnshroudedBarrel",
]

MAGAZINE_SUFFIXES = [
    "_DefaultMagazine", "_ExtendedMagazine",
]

IRONSIGHT_SUFFIXES = [
    "_DefaultIronsight",
]

ALL_ENTITY_NAMES = set(
    RIFLE_ENTITIES + SHOTGUN_ENTITIES + PISTOL_ENTITIES + SMG_ENTITIES
    + SPECIAL_WEAPON_ENTITIES
    + SCOPE_ENTITIES + SUPPRESSOR_ENTITIES
    + BARREL_ENTITIES + MAGAZINE_ENTITIES + IRONSIGHT_ENTITIES
    + CHOKE_ENTITIES + OTHER_ATTACHMENT_ENTITIES
)

# All weapon entity names (for the Weapons tab)
ALL_WEAPON_ENTITIES = (
    RIFLE_ENTITIES + SHOTGUN_ENTITIES + PISTOL_ENTITIES
    + SMG_ENTITIES + SPECIAL_WEAPON_ENTITIES
)
ALL_WEAPON_ENTITY_SET = set(ALL_WEAPON_ENTITIES)


# ── ASR file class ───────────────────────────────────────────────────────

class AsrFile:
    """Read, parse, modify, and write AsuraZlb ASR/ASRpatch files."""

    def __init__(self, path: str):
        self.path = path
        self.header: bytes = b""
        self.flags: int = 0
        self.comp_size: int = 0
        self.uncomp_size: int = 0
        self.body: bytearray = bytearray()
        self.entities: Dict[str, Entity] = {}
        self._all_strings: List[Tuple[int, str]] = []
        self._format: str = ""  # "ZLB" or "ZBB"
        self._zbb_extra_header: bytes = b""  # extra 16 bytes for ZBB
        self._marker_entities: List[Tuple[str, int, int]] = []
        # Base-file merge state (populated by merge_base_stats)
        self.base_path: str = ""
        self.base_entities: Dict[str, Entity] = {}
        self._load()

    @staticmethod
    def _format_error_message(path: str, magic: bytes, size: int) -> str:
        """Build a user-friendly error when the file is not a supported Asura container."""
        import os

        name = os.path.basename(path)
        magic_display = magic.decode("latin-1", errors="replace")
        lines = [
            f"Unknown file format in:\n  {path}\n",
            f"File size: {size:,} bytes",
            f"Header bytes: {magic!r}  ({magic_display!r})",
            f"Expected: {MAGIC_ZLB.decode()!r}, {MAGIC_ZBB.decode()!r}, "
            f"or uncompressed {MAGIC_RAW.decode()!r}",
            "",
            "Open this file (under the game install):",
            "  Sniper Elite 5/misc/common.asr.asrpatch",
            "",
            "Do NOT open:",
            "  • common.asr          (huge ~489 MB base file)",
            "  • common.asr_en       (localization)",
            "  • *.pc.sounds / *.ts  (audio/text containers)",
            "  • any navmesh .asrpatch",
        ]
        lower = name.lower()
        if lower == "common.asr" or (
            lower.endswith(".asr") and not lower.endswith(".asrpatch")
        ):
            lines.append(
                "\nTip: use common.asr.asrpatch (the patch in misc/), "
                "not common.asr."
            )
        elif not lower.endswith(".asrpatch"):
            lines.append(
                "\nTip: the file name should be exactly common.asr.asrpatch."
            )
        return "\n".join(lines)

    def _load(self) -> None:
        """Load and decompress the ASR file.

        Supported outer containers:
          - AsuraZlb — zlib-compressed (normal Steam common.asr.asrpatch)
          - AsuraZbb — block-compressed base archives
          - Asura\\x20\\x20\\x20 — uncompressed archive body (same bytes that
            live *inside* a ZLB file). Some Windows installs / third-party
            tools leave the patch in this form (~17 MB, magic 'Asura   ').
            That is the real Windows "file looks correct but won't open" case.
        """
        with open(self.path, "rb") as f:
            raw = f.read()

        if len(raw) == 0:
            raise ValueError(
                f"File is empty: {self.path}"
            )

        if raw[:8] == MAGIC_ZLB:
            self._format = "ZLB"
            self.header = raw[:8]
            self.flags = struct.unpack("<I", raw[8:12])[0]
            self.comp_size = struct.unpack("<I", raw[12:16])[0]
            self.uncomp_size = struct.unpack("<I", raw[16:20])[0]
            try:
                self.body = bytearray(
                    zlib.decompress(raw[20:20 + self.comp_size], 13)
                )
            except zlib.error as e:
                raise ValueError(
                    f"Failed to decompress ZLB body: {e}"
                ) from e
        elif raw[:8] == MAGIC_ZBB:
            # AsuraZbb format - block-based compression.
            # Header is 24 bytes: 8-byte magic + 16 bytes of metadata.
            # Note: only the first zlib stream is expanded here; multi-block
            # ZBB base files (e.g. common.asr) will load incompletely.
            self._format = "ZBB"
            self.header = raw[:8]
            self._zbb_extra_header = raw[8:24]
            try:
                self.body = bytearray(zlib.decompress(raw[24:], 13))
            except zlib.error as e:
                raise ValueError(
                    f"Failed to decompress ZBB body: {e}"
                ) from e
        elif raw[:8] == MAGIC_RAW:
            # Uncompressed Asura archive — identical to the decompressed ZLB
            # body. Accept it so Windows users whose patch was left
            # decompressed can still edit weapon data (~17 MB).
            #
            # Reject huge Asura-space files (localization / sounds) early so
            # we don't scan hundreds of MB looking for weapon entities.
            # A normal decompressed common.asr.asrpatch is ~15–20 MB.
            if len(raw) > 40 * 1024 * 1024:
                raise ValueError(
                    self._format_error_message(self.path, raw[:8], len(raw))
                    + "\n\nThis uncompressed Asura file is too large to be "
                    "common.asr.asrpatch (expected ~17 MB, got "
                    f"{len(raw) / (1024 * 1024):.0f} MB). "
                    "You may have selected a localization or audio file."
                )
            self._format = "RAW"
            self.header = raw[:8]
            self.flags = 0
            self.comp_size = 0
            self.uncomp_size = len(raw)
            self.body = bytearray(raw)
        else:
            raise ValueError(
                self._format_error_message(self.path, raw[:8], len(raw))
            )

        self._scan_entities()

    # Entity boundary marker placed immediately before each entity name:
    # type=3, hash=0x55F89B99, value=0  →  03 00 00 00 99 9b f8 55 00 00 00 00
    _ENTITY_MARKER = b"\x03\x00\x00\x00\x99\x9b\xf8\x55\x00\x00\x00\x00"

    def _scan_entities(self) -> None:
        """Scan the body for all known entity names and their properties.

        Two-phase process:

        1. Find all type=4 strings and, separately, every entity-boundary
           marker (``03 00 00 00 99 9b f8 55 00 00 00 00``) that is
           immediately followed by a type=4 name.  Known entity names are
           registered using the **first** marker-linked occurrence so that
           shared attachment instances (e.g. ``Blued_Lightened_Barrel``
           appears 8 times) do not overwrite a clean first record with a
           later polluted one.

        2. For each registered entity, scan only the property window that
           belongs to that entity: from the end of the previous
           marker-linked name to this entity's boundary marker.

        Critical details discovered during reverse-engineering:

        - Entity names may be as short as 3 characters (``G43``, ``EMP``,
          ``HDM``, ``M12``, ``P38``).  The old ``str_len > 3`` filter
          dropped them entirely.
        - Properties for an entity sit **before** its boundary marker, not
          after the name.  Scanning past the name into the next entity's
          block is what caused scopes/ironsights to inherit weapon stats.
        - The asrpatch only contains property *overrides*; base stats live
          in ``common.asr``.  Sparse property lists are expected.
        """
        self.entities.clear()
        self._all_strings.clear()
        # Ordered list of every marker-linked (name, name_offset, marker_offset).
        # Used both for entity registration and for tight property windows.
        self._marker_entities: List[Tuple[str, int, int]] = []

        body_len = len(self.body)
        type_tag = b"\x04\x00\x00\x00"

        # Phase 1a: collect ALL type=4 strings (for display / debugging and
        # as a secondary boundary signal).  Allow len >= 3 so "G43" is kept.
        search_pos = 0
        while search_pos < body_len - 8:
            pos = self.body.find(type_tag, search_pos)
            if pos < 0:
                break
            str_len = struct.unpack("<I", self.body[pos + 4:pos + 8])[0]
            # Min length 3 catches G43/EMP/HDM/M12/P38; max 80 rejects junk.
            if 3 <= str_len < 80 and pos + 8 + str_len <= body_len:
                try:
                    s = self.body[pos + 8:pos + 8 + str_len].decode("ascii")
                    # Allow alphanumerics, dots, underscores, hyphens, spaces,
                    # and parentheses (e.g. "MG42(HalfAmmo)").
                    if all(c.isalnum() or c in "._- ()" for c in s):
                        self._all_strings.append((pos, s))
                except UnicodeDecodeError:
                    pass
            search_pos = pos + 1

        # Phase 1b: walk entity-boundary markers and the type=4 name that
        # immediately follows each one.  This is the authoritative entity list.
        search_pos = 0
        while search_pos < body_len - 20:
            pos = self.body.find(self._ENTITY_MARKER, search_pos)
            if pos < 0:
                break
            name_off = pos + 12
            if (name_off + 8 <= body_len
                    and self.body[name_off:name_off + 4] == type_tag):
                str_len = struct.unpack(
                    "<I", self.body[name_off + 4:name_off + 8]
                )[0]
                if 3 <= str_len < 80 and name_off + 8 + str_len <= body_len:
                    try:
                        s = self.body[
                            name_off + 8:name_off + 8 + str_len
                        ].decode("ascii")
                        if all(c.isalnum() or c in "._- ()" for c in s):
                            self._marker_entities.append((s, name_off, pos))
                            # First occurrence wins — shared attachments
                            # repeat many times with identical overrides.
                            if s in ALL_ENTITY_NAMES and s not in self.entities:
                                self.entities[s] = Entity(
                                    name=s, name_offset=name_off
                                )
                    except UnicodeDecodeError:
                        pass
            search_pos = pos + 1

        # Phase 1c: fallback for known entities that appear as type=4 strings
        # but were not linked to a marker (should be rare).  Still register
        # them so the UI can list them; property scan will use string bounds.
        for pos, s in self._all_strings:
            if s in ALL_ENTITY_NAMES and s not in self.entities:
                self.entities[s] = Entity(name=s, name_offset=pos)

        # Phase 2: scan properties with marker-bounded windows.
        # Build a name_offset → index map into _marker_entities for O(1) lookup.
        marker_index: Dict[int, int] = {
            name_off: i
            for i, (_n, name_off, _m) in enumerate(self._marker_entities)
        }
        for entity in self.entities.values():
            self._scan_properties(entity, marker_index)

    def _scan_properties(self, entity: Entity,
                         marker_index: Dict[int, int]) -> None:
        """Scan for float and int properties belonging to an entity.

        Properties are 12-byte tuples: [type:4][value:4][hash:4].
        They are NOT necessarily 4-byte aligned, so we scan byte-by-byte.
        We search for known hash bytes, then validate the type and value.

        ASR entity structure (verified against common.asr.asrpatch)::

            [properties for this entity ...]
            [type=3 marker  03 00 00 00 99 9b f8 55 00 00 00 00]
            [type=4 name][name_hash 4B]
            [properties for next entity ...]
            [type=3 marker][type=4 next_name]...

        Properties sit **before** the entity's boundary marker.  Scanning
        past the name into the following block is what previously made
        scopes and ironsights inherit neighbouring weapon stats.

        When the entity was registered via a marker, the search window is
        strictly ``(end of previous marker-entity) … (this marker)``.
        Otherwise we fall back to neighbouring type=4 string bounds.
        """
        body_len = len(self.body)
        search_start: int
        search_end: int

        idx = marker_index.get(entity.name_offset)
        if idx is not None:
            # Tight marker-bounded window (preferred path).
            _name, _name_off, marker_off = self._marker_entities[idx]
            search_end = marker_off
            if idx > 0:
                prev_name, prev_off, _prev_marker = self._marker_entities[idx - 1]
                # End of previous entity = after its name string + name_hash.
                search_start = prev_off + 8 + len(prev_name) + 4
            else:
                search_start = max(0, marker_off - 8000)
        else:
            # Fallback: bound by neighbouring type=4 strings.
            all_str_offsets = [s[0] for s in self._all_strings]
            sidx = bisect.bisect_left(all_str_offsets, entity.name_offset)
            if sidx > 0:
                prev_off, prev_str = self._all_strings[sidx - 1]
                search_start = prev_off + 8 + len(prev_str) + 4
            else:
                search_start = max(0, entity.name_offset - 5000)
            # Properties end at the marker 12 bytes before the name when
            # present; otherwise stop at the name itself.
            if (entity.name_offset >= 12
                    and self.body[entity.name_offset - 12:entity.name_offset]
                    == self._ENTITY_MARKER):
                search_end = entity.name_offset - 12
            else:
                search_end = entity.name_offset

        search_start = max(0, search_start)
        search_end = max(search_end, search_start + 12)
        search_end = min(search_end, body_len)

        # Core hashes in the wide window. Attachment-mod hashes collide
        # with junk inside full weapon defs, but magazine / ammo entities
        # (Pzb39Ammo etc.) store their real stats as those mods — include
        # them for non-weapons.
        hash_bytes_map = {
            struct.pack("<I", h): h for h in CORE_HASH_NAMES
        }
        if entity.name not in ALL_WEAPON_ENTITY_SET:
            hash_bytes_map.update(
                {struct.pack("<I", h): h for h in ATTACHMENT_MOD_HASH_NAMES}
            )

        # Collect all candidates: hash -> list of (offset, type, value)
        candidates: Dict[int, list] = {}
        for hb, h_int in hash_bytes_map.items():
            search_pos = search_start
            while search_pos < search_end - 4:
                pos = self.body.find(hb, search_pos, search_end)
                if pos < 0:
                    break
                if pos >= 8:
                    type_offset = pos - 8
                    value_offset = pos - 4
                    ptype = struct.unpack(
                        "<I", self.body[type_offset:type_offset + 4]
                    )[0]
                    if ptype == TYPE_FLOAT:
                        fv = struct.unpack(
                            "<f", self.body[value_offset:value_offset + 4]
                        )[0]
                        if -10000 < fv < 100000:
                            candidates.setdefault(h_int, []).append(
                                (value_offset, TYPE_FLOAT, fv)
                            )
                    elif ptype == TYPE_INT:
                        iv = struct.unpack(
                            "<I", self.body[value_offset:value_offset + 4]
                        )[0]
                        if 0 < iv < 10000:
                            candidates.setdefault(h_int, []).append(
                                (value_offset, TYPE_INT, iv)
                            )
                search_pos = pos + 1

        # Anchor for "closest property" selection is the marker (end of the
        # property block), falling back to the name offset.
        anchor = search_end if idx is not None else entity.name_offset

        # Pick the best candidate for each hash using value-range heuristics
        for h_int, props in candidates.items():
            name = HASH_NAMES.get(h_int) or CORE_HASH_NAMES.get(h_int)
            if not name:
                continue
            best = self._pick_best_property(name, props, anchor)
            if best:
                offset, ptype, value = best
                entity.properties.append(Property(
                    type=ptype, offset=offset, hash=h_int,
                    name=name, value=value,
                ))

        # Attachments store most of their effects as consecutive float
        # multipliers packed just before the entity marker.  Only run this
        # on non-weapon entities — on full weapon defs the walk can spill
        # into structural bytes and invent junk stats.
        # Attachments always walk leftover modifiers. Special/level-only
        # weapons (Panzerfaust, Pzb39, MG42) store extra payload / reserve
        # floats that core hashes miss — walk those too. Regular loadout
        # guns stay on the core-hash scan (consecutive walk invents junk).
        if idx is not None and (
            entity.name not in ALL_WEAPON_ENTITY_SET
            or entity.name in SPECIAL_WEAPON_ENTITIES
        ):
            self._scan_consecutive_modifiers(entity, search_start, search_end)

    def _scan_consecutive_modifiers(
        self, entity: Entity, search_start: int, search_end: int
    ) -> None:
        """Walk 12-byte property tuples backward from the entity marker.

        Captures attachment multiplier packs that the known-hash search
        misses.  Skips structural junk; keeps named hashes and plausible
        float modifiers.
        """
        existing = {p.hash for p in entity.properties}
        # search_end is the marker offset (property block ends here)
        offset = search_end - 12
        found: List[Property] = []
        steps = 0
        while offset >= search_start and steps < 80:
            steps += 1
            if offset + 12 > len(self.body):
                break
            ptype = struct.unpack("<I", self.body[offset:offset + 4])[0]
            value_offset = offset + 4
            if ptype == TYPE_FLOAT:
                value = struct.unpack("<f", self.body[value_offset:value_offset + 4])[0]
                h_int = struct.unpack("<I", self.body[offset + 8:offset + 12])[0]
                rec_start = offset
                offset -= 12
                if h_int == 0 or h_int in existing:
                    continue
                if not (-500.0 < value < 5000.0):
                    continue
                # Prefer attachment-mod names, then core, then raw hex
                name = (
                    ATTACHMENT_MOD_HASH_NAMES.get(h_int)
                    or CORE_HASH_NAMES.get(h_int)
                )
                # Named hashes may legitimately be 0 (e.g. Power × forced off).
                # Unmapped near-zero floats are almost always padding.
                if name is None and abs(value) < 1e-6:
                    continue
                if name is None:
                    if not (0.005 <= abs(value) <= 200.0):
                        continue
                    if abs(value - round(value)) < 1e-6 and int(round(value)) in (
                        256, 512, 768, 1024, 2048, 4096
                    ):
                        continue
                    name = f"Mod_0x{h_int:08X}"
                found.append(Property(
                    type=TYPE_FLOAT, offset=value_offset,
                    hash=h_int, name=name, value=value,
                ))
                existing.add(h_int)
            elif ptype == TYPE_INT:
                value = struct.unpack("<I", self.body[value_offset:value_offset + 4])[0]
                h_int = struct.unpack("<I", self.body[offset + 8:offset + 12])[0]
                offset -= 12
                if h_int == 0 or h_int in existing:
                    continue
                name = CORE_HASH_NAMES.get(h_int) or ATTACHMENT_MOD_HASH_NAMES.get(h_int)
                if name is None:
                    continue  # unmapped ints are usually structural
                if not (0 < value < 10000):
                    continue
                found.append(Property(
                    type=TYPE_INT, offset=value_offset,
                    hash=h_int, name=name, value=value,
                ))
                existing.add(h_int)
            elif ptype == TYPE_VEC3:
                # Interleaved type=3 structural nodes — skip and keep walking
                offset -= 12
            else:
                break

        entity.properties.extend(found)

    @staticmethod
    def _is_closer_to_other_entity(hash_offset: int, this_offset: int,
                                   all_name_offsets: List[int]) -> bool:
        """Check if a hash occurrence is closer to another entity's name.

        Uses binary search on the sorted list of entity name offsets.
        Returns True if there exists another entity name that is closer
        to ``hash_offset`` than ``this_offset`` is.
        """
        idx = bisect.bisect_left(all_name_offsets, hash_offset)
        # Check the two nearest entity names (one before, one after)
        nearest = []
        if idx > 0:
            nearest.append(all_name_offsets[idx - 1])
        if idx < len(all_name_offsets):
            nearest.append(all_name_offsets[idx])
        this_dist = abs(hash_offset - this_offset)
        for other_offset in nearest:
            if other_offset != this_offset:
                if abs(hash_offset - other_offset) < this_dist:
                    return True
        return False

    @staticmethod
    def _is_closer_to_other_string(value_offset: int, this_offset: int,
                                   all_str_offsets: List[int]) -> bool:
        """Check if a property value is closer to another string than to
        this entity's name.

        Uses binary search on the sorted list of ALL type=4 string offsets.
        Returns True if there exists a string that is closer to
        ``value_offset`` than ``this_offset`` is.

        This prevents picking up properties that belong to neighboring
        entities/objects when a property sits near the boundary between
        two entities.
        """
        idx = bisect.bisect_left(all_str_offsets, value_offset)
        nearest = []
        if idx > 0:
            nearest.append(all_str_offsets[idx - 1])
        if idx < len(all_str_offsets):
            nearest.append(all_str_offsets[idx])
        this_dist = abs(value_offset - this_offset)
        for other_offset in nearest:
            if other_offset != this_offset:
                if abs(value_offset - other_offset) < this_dist:
                    return True
        return False

    def _pick_best_property(self, name: str, candidates: list,
                            name_offset: int) -> Optional[tuple]:
        """Pick the best property value from multiple candidates.

        Uses reasonable value ranges to filter out values from
        neighboring child entities (barrels, magazines, etc.).
        Prefers values closest to the entity name.
        """
        # Define reasonable ranges for each property.
        # These ranges are deliberately wide to avoid filtering out real
        # values from weapons with unusual stats (e.g. shotgun Damage of
        # 0.2, SMG DamageSpread of 0.025, high-capacity magazines > 50).
        RANGES = {
            "EffectiveRange": (10, 3000),
            "MuzzleVelocity": (100, 3000),
            "Damage": (0, 500),  # 0 is a real override (no listed score)
            "DamageSpread": (0, 500),  # 0 is a real override; Sjögren stock 0.025
            "WindDrop": (0, 1),
            # RPM is absolute fire-rate on some weapons, but attachment
            # overrides often store multipliers in the ~0.3–1.5 range.
            "RPM": (0.1, 2000),
            "FireRate": (0.01, 2000),  # some entities store sub-1.0 rates
            "Recoil1_Vertical": (0, 20),
            # Suppressors / muzzle brakes can push horizontal recoil negative
            "Recoil2_Horizontal": (-20, 20),
            "RecoilMult": (0, 5),
            "RecoilRecoveryTime": (-10, 100),  # Sten stores -0.6
            "RecoilResetSpeed": (0, 100),
            "ZoomMin": (1, 50),
            "ZoomMax": (1, 50),
            "ZoomMax2": (1, 50),
            "ScopeInSpeed": (0.01, 1.0),
            "SwayAmount": (0, 1),
            "SwayRecovery": (0, 1),
            "SwayDrift": (0, 2),  # Type1 has SwayDrift ~1.6
            "SwayDecay": (0, 1),
            "AimStability": (0, 20),
            "ScopeSteadyTime": (0, 5),
            "HoldBreathDuration": (0, 5),
            "SwayPerShot": (0, 5),
            "SwayWalk": (0, 2),
            "SwayCrouch": (0, 5),
            "SwayProne": (0, 2),
            "DamageDropoff": (0, 500),
            "AudibleRangeBase": (-10, 500),  # Derringer stores -0.5
            # int mag sizes 1–200; float attachment mults ~0.05–5
            "MagazineCapacity": (0.05, 200),
        }

        vmin, vmax = RANGES.get(name, (-10000, 100000))

        # Filter by value range
        valid = []
        for offset, ptype, value in candidates:
            if vmin <= value <= vmax:
                valid.append((offset, ptype, value))

        # MagazineCapacity is int on weapons/magazines (round count) but a
        # float *multiplier* on many barrels/suppressors/chokes.  Prefer int
        # when present; otherwise accept a float in the multiplier range.
        if name == "MagazineCapacity":
            int_props = [c for c in valid if c[1] == TYPE_INT]
            if int_props:
                valid = int_props
            else:
                float_props = [
                    c for c in valid
                    if c[1] == TYPE_FLOAT and 0.05 <= abs(c[2]) <= 5.0
                ]
                if float_props:
                    valid = float_props
                else:
                    return None

        if not valid:
            # Fall back to all candidates if none in range.
            # This handles cases where a real property has an unexpected
            # value outside our defined range.
            valid = candidates

        # Pick the one closest to the entity name
        best = min(valid, key=lambda c: abs(c[0] - name_offset))
        return best

    def set_float(self, entity_name: str, prop_name: str, value: float) -> bool:
        """Set a float property on an entity. Returns True if successful."""
        entity = self.entities.get(entity_name)
        if not entity:
            return False
        prop = entity.get(prop_name)
        if not prop or not prop.is_float or not prop.editable:
            return False
        struct.pack_into("<f", self.body, prop.offset, value)
        prop.value = value
        return True

    def set_int(self, entity_name: str, prop_name: str, value: int) -> bool:
        """Set an int property on an entity. Returns True if successful."""
        entity = self.entities.get(entity_name)
        if not entity:
            return False
        prop = entity.get(prop_name)
        if not prop or not prop.is_int or not prop.editable:
            return False
        struct.pack_into("<I", self.body, prop.offset, value)
        prop.value = value
        return True

    def merge_base_stats(
        self,
        base_path: str,
        max_blocks: int = 2,
        progress_callback=None,
    ) -> dict:
        """Merge weapon/attachment stats from the base ``common.asr`` file.

        The asrpatch only contains *overrides*.  Early ZBB blocks of
        ``common.asr`` hold the same entity property tables the game starts
        from.  For every known property that is **missing** from the patch
        entity but present in the base file, a read-only ``source="base"``
        property is attached so the editor can display the full picture.

        Properties already present in the patch are left untouched (patch
        wins — those are the values the game actually uses after load).

        Args:
            base_path: Path to ``common.asr`` (AsuraZbb).
            max_blocks: How many leading ZBB blocks to scan (weapons live
                in blocks 0–1; default 2 is enough and stays fast).
            progress_callback: Optional ``callable(fraction_0_to_1, message)``.

        Returns:
            Summary dict: ``{merged_props, base_entities, blocks_scanned}``.
        """
        base_entities = extract_entities_from_zbb(
            base_path, max_blocks=max_blocks, progress_callback=progress_callback
        )
        self.base_path = base_path
        self.base_entities = base_entities

        merged = 0
        for name, base_ent in base_entities.items():
            patch_ent = self.entities.get(name)
            if patch_ent is None:
                # Entity exists only in base — register a read-only copy so
                # the browser can still list it (e.g. rare DLC variants).
                clone = Entity(name=name, name_offset=-1)
                for bp in base_ent.properties:
                    clone.properties.append(Property(
                        type=bp.type, offset=-1, hash=bp.hash,
                        name=bp.name, value=bp.value, source="base",
                    ))
                self.entities[name] = clone
                merged += len(clone.properties)
                continue

            existing_hashes = {p.hash for p in patch_ent.properties}
            for bp in base_ent.properties:
                if bp.hash in existing_hashes:
                    continue
                patch_ent.properties.append(Property(
                    type=bp.type, offset=-1, hash=bp.hash,
                    name=bp.name, value=bp.value, source="base",
                ))
                merged += 1
                existing_hashes.add(bp.hash)

        return {
            "merged_props": merged,
            "base_entities": len(base_entities),
            "blocks_scanned": max_blocks,
        }

    def replace_property_hash(self, entity_name: str,
                              old_prop_name: str, new_prop_name: str,
                              new_value: Optional[float] = None) -> bool:
        """Replace a property's hash in-place, effectively renaming it.

        This is used to give entities a property they don't have by
        "hijacking" an existing property.  For example, some sniper rifles
        (Kar98K, Winchester_1885, DLC_Mosin) have ``DamageDropoff`` but no
        ``Damage`` property in the asrpatch.  By changing the hash of the
        ``DamageDropoff`` property to the ``Damage`` hash, the entity gains
        a ``Damage`` property and loses its ``DamageDropoff`` property.

        The property's type and byte offset in the body are preserved —
        only the 4-byte hash field is overwritten.  If ``new_value`` is
        provided, the value bytes are also updated.

        Returns True if the replacement was successful.
        """
        entity = self.entities.get(entity_name)
        if not entity:
            return False
        old_hash = NAME_TO_HASH.get(old_prop_name)
        new_hash = NAME_TO_HASH.get(new_prop_name)
        if old_hash is None or new_hash is None:
            return False
        # Find the property in the entity's property list
        prop = None
        for p in entity.properties:
            if p.hash == old_hash:
                prop = p
                break
        if not prop:
            return False
        # The hash field is at prop.offset + 4 (after the 4-byte value field)
        hash_offset = prop.offset + 4
        struct.pack_into("<I", self.body, hash_offset, new_hash)
        # Update the value if requested
        if new_value is not None and prop.is_float:
            struct.pack_into("<f", self.body, prop.offset, new_value)
            prop.value = new_value
        # Update the cached Property object
        prop.hash = new_hash
        prop.name = new_prop_name
        return True

    def save(self, output_path: str) -> None:
        """Recompress and write the modified ASR file.

        Preserves AsuraZbb when the source was ZBB. ZLB and RAW sources are
        written as AsuraZlb (the format the game expects for
        common.asr.asrpatch). RAW inputs are therefore "repaired" on save.
        Uses zlib with wbits=13 to match the engine's expectations.
        """
        co = zlib.compressobj(6, zlib.DEFLATED, 13)
        compressed = co.compress(bytes(self.body))
        compressed += co.flush()

        # Verify round-trip (use a real check, not assert, so it
        # survives even when Python is run with -O).
        if zlib.decompress(compressed, 13) != bytes(self.body):
            raise RuntimeError(
                "Compression round-trip verification failed"
            )

        out = bytearray()
        if self._format == "ZBB":
            # Preserve AsuraZbb format: 8-byte magic + 16-byte metadata
            out.extend(MAGIC_ZBB)
            out.extend(self._zbb_extra_header)
            out.extend(compressed)
        else:
            # ZLB and RAW → AsuraZlb (game-readable weapon patch format)
            out.extend(MAGIC_ZLB)
            out.extend(struct.pack("<I", self.flags))
            out.extend(struct.pack("<I", len(compressed)))
            out.extend(struct.pack("<I", len(self.body)))
            out.extend(compressed)

        with open(output_path, "wb") as f:
            f.write(out)

    def get_all_strings(self) -> List[Tuple[int, str]]:
        """Return all string entities found in the body."""
        return self._all_strings.copy()

    def find_entities(self, pattern: str) -> List[str]:
        """Find entity names matching a pattern (case-insensitive substring)."""
        pattern_lower = pattern.lower()
        return [name for name in self.entities if pattern_lower in name.lower()]


# ── Base common.asr (AsuraZbb) entity extraction ──────────────────────────

_ENTITY_MARKER = b"\x03\x00\x00\x00\x99\x9b\xf8\x55\x00\x00\x00\x00"


def _decompress_zbb_blocks(
    raw: bytes, max_blocks: int = 2, progress_callback=None
) -> List[bytes]:
    """Decompress the first *max_blocks* ZBB blocks (wbits=12)."""
    if raw[:8] != MAGIC_ZBB:
        raise ValueError(
            f"Not an AsuraZbb file (magic={raw[:8]!r}). "
            "Expected the base common.asr."
        )
    _, _, first_comp, _ = struct.unpack("<4I", raw[8:24])
    blocks: List[bytes] = []
    pos = 24
    comp = first_comp
    for i in range(max_blocks):
        if progress_callback:
            progress_callback(i / max(max_blocks, 1), f"Decompressing block {i}…")
        if pos + comp > len(raw):
            break
        blocks.append(zlib.decompress(raw[pos:pos + comp], 12))
        pos += comp
        if i + 1 >= max_blocks:
            break
        if pos + 8 > len(raw):
            break
        comp, _uncomp = struct.unpack("<II", raw[pos:pos + 8])
        pos += 8
    return blocks


def _scan_entities_in_buffer(buf: bytes) -> Dict[str, Entity]:
    """Scan a decompressed buffer for known entities using marker windows.

    Same algorithm as AsrFile._scan_entities / _scan_properties, but
    produces entities with ``source="base"`` properties (offset is local
    to *buf*, not used for writing).
    """
    type_tag = b"\x04\x00\x00\x00"
    marker_entities: List[Tuple[str, int, int]] = []  # name, name_off, marker_off

    pos = 0
    body_len = len(buf)
    while pos < body_len - 20:
        p = buf.find(_ENTITY_MARKER, pos)
        if p < 0:
            break
        name_off = p + 12
        if name_off + 8 <= body_len and buf[name_off:name_off + 4] == type_tag:
            str_len = struct.unpack("<I", buf[name_off + 4:name_off + 8])[0]
            if 3 <= str_len < 80 and name_off + 8 + str_len <= body_len:
                try:
                    s = buf[name_off + 8:name_off + 8 + str_len].decode("ascii")
                    if all(c.isalnum() or c in "._- ()" for c in s):
                        marker_entities.append((s, name_off, p))
                except UnicodeDecodeError:
                    pass
        pos = p + 1

    # First occurrence of each known entity
    entities: Dict[str, Entity] = {}
    name_to_idx: Dict[str, int] = {}
    for i, (name, name_off, marker_off) in enumerate(marker_entities):
        if name not in ALL_ENTITY_NAMES:
            continue
        if name in entities:
            continue
        entities[name] = Entity(name=name, name_offset=name_off)
        name_to_idx[name] = i

    hash_bytes_map = {struct.pack("<I", h): h for h in HASH_NAMES}

    # Ranges (mirrors AsrFile._pick_best_property)
    ranges = {
        "EffectiveRange": (10, 3000),
        "MuzzleVelocity": (100, 3000),
        "Damage": (0, 500),
        "DamageSpread": (0, 500),
        "WindDrop": (0, 1),
        "RPM": (0.1, 2000),
        "FireRate": (0.01, 2000),
        "Recoil1_Vertical": (0, 20),
        "Recoil2_Horizontal": (-20, 20),
        "RecoilMult": (0, 5),
        "RecoilRecoveryTime": (-10, 100),
        "RecoilResetSpeed": (0, 100),
        "ZoomMin": (1, 50),
        "ZoomMax": (1, 50),
        "ZoomMax2": (1, 50),
        "ScopeInSpeed": (0.01, 1.0),
        "SwayAmount": (0, 1),
        "SwayRecovery": (0, 1),
        "SwayDrift": (0, 2),
        "SwayDecay": (0, 1),
        "AimStability": (0, 20),
        "ScopeSteadyTime": (0, 5),
        "HoldBreathDuration": (0, 5),
        "SwayPerShot": (0, 5),
        "SwayWalk": (0, 2),
        "SwayCrouch": (0, 5),
        "SwayProne": (0, 2),
        "DamageDropoff": (0, 500),
        "AudibleRangeBase": (-10, 500),
        "MagazineCapacity": (1, 200),
    }

    for name, entity in entities.items():
        idx = name_to_idx[name]
        _n, _name_off, marker_off = marker_entities[idx]
        search_end = marker_off
        if idx > 0:
            prev_name, prev_off, _pm = marker_entities[idx - 1]
            search_start = prev_off + 8 + len(prev_name) + 4
        else:
            search_start = max(0, marker_off - 8000)
        search_start = max(0, search_start)
        search_end = min(len(buf), max(search_end, search_start + 12))

        candidates: Dict[int, list] = {}
        for hb, h_int in hash_bytes_map.items():
            sp = search_start
            while sp < search_end - 4:
                found = buf.find(hb, sp, search_end)
                if found < 0:
                    break
                if found >= 8:
                    to = found - 8
                    vo = found - 4
                    ptype = struct.unpack("<I", buf[to:to + 4])[0]
                    if ptype == TYPE_FLOAT:
                        fv = struct.unpack("<f", buf[vo:vo + 4])[0]
                        if -10000 < fv < 100000:
                            candidates.setdefault(h_int, []).append(
                                (vo, TYPE_FLOAT, fv)
                            )
                    elif ptype == TYPE_INT:
                        iv = struct.unpack("<I", buf[vo:vo + 4])[0]
                        if 0 < iv < 10000:
                            candidates.setdefault(h_int, []).append(
                                (vo, TYPE_INT, iv)
                            )
                sp = found + 1

        for h_int, props in candidates.items():
            pname = HASH_NAMES[h_int]
            vmin, vmax = ranges.get(pname, (-10000, 100000))
            valid = [c for c in props if vmin <= c[2] <= vmax]
            if pname == "MagazineCapacity":
                ints = [c for c in valid if c[1] == TYPE_INT]
                if ints:
                    valid = ints
                else:
                    continue
            if not valid:
                valid = props
            best = min(valid, key=lambda c: abs(c[0] - marker_off))
            entity.properties.append(Property(
                type=best[1], offset=best[0], hash=h_int,
                name=pname, value=best[2], source="base",
            ))

    return entities


def extract_entities_from_zbb(
    path: str,
    max_blocks: int = 2,
    progress_callback=None,
) -> Dict[str, Entity]:
    """Load known weapon/attachment entities from a base ``common.asr``.

    Weapon stat tables live in the first two ZBB blocks (~4 MB decompressed).
    Scanning only those keeps startup fast (~0.5 s) while covering every
    player weapon entity.
    """
    with open(path, "rb") as f:
        raw = f.read()
    blocks = _decompress_zbb_blocks(raw, max_blocks, progress_callback)
    if progress_callback:
        progress_callback(0.9, "Scanning base entities…")
    # Concatenate so property windows never clip at a block boundary
    combined = b"".join(blocks)
    entities = _scan_entities_in_buffer(combined)
    if progress_callback:
        progress_callback(1.0, f"Base: {len(entities)} entities")
    return entities


def find_sibling_base_asr(asrpatch_path: str) -> Optional[str]:
    """Return path to ``common.asr`` next to an asrpatch, if it exists."""
    if not asrpatch_path:
        return None
    directory = os.path.dirname(asrpatch_path)
    # Prefer exact common.asr
    candidate = os.path.join(directory, "common.asr")
    if os.path.isfile(candidate):
        return candidate
    return None
