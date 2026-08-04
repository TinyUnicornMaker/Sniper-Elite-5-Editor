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
import struct
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

# ── Container magic ──────────────────────────────────────────────────────

MAGIC_ZLB = b"AsuraZlb"
MAGIC_ZBB = b"AsuraZbb"

# ── Property type tags ────────────────────────────────────────────────────

TYPE_INT = 0
TYPE_FLOAT = 1
TYPE_VEC2 = 2
TYPE_VEC3 = 3
TYPE_STRING = 4

# ── Known property hashes ────────────────────────────────────────────────
# Discovered by comparing values across weapons with known in-game stats.

HASH_NAMES: Dict[int, str] = {
    # Weapon stats (verified from M1903 known offsets)
    0x19B61B3D: "EffectiveRange",
    0x8C6EF316: "MuzzleVelocity",
    0xFFEBCB07: "Damage",
    0x171B12B6: "DamageSpread",  # secondary damage/spread value
    0xACB8EA97: "WindDrop",
    0x2699E6A9: "RPM",
    0x22983F6D: "FireRate",
    # Recoil
    0x680784A9: "Recoil1_Vertical",
    0xB9CBCCB9: "Recoil2_Horizontal",
    0x6539B743: "RecoilMult",
    0x99CBF4DF: "RecoilRecoveryTime",
    0x19878633: "RecoilResetSpeed",
    # Scope / aim
    0x62CC2933: "ZoomMin",
    0xC0104A2C: "ZoomMax",
    0xC96F3E4D: "ZoomMax2",  # Secondary zoom level (used by A1/A2/M1913 scopes)
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
    # Magazine (int property)
    0x807AAE98: "MagazineCapacity",
}

# Reverse lookup: name -> hash
NAME_TO_HASH: Dict[str, int] = {v: k for k, v in HASH_NAMES.items()}


# ── Property dataclasses ─────────────────────────────────────────────────

@dataclass
class Property:
    """A single typed property in the entity database."""
    type: int
    offset: int  # byte offset in the decompressed body
    hash: int
    name: str = ""
    value: Union[int, float, str, Tuple[float, ...]] = 0

    @property
    def is_float(self) -> bool:
        return self.type == TYPE_FLOAT

    @property
    def is_int(self) -> bool:
        return self.type == TYPE_INT

    @property
    def is_string(self) -> bool:
        return self.type == TYPE_STRING

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
            hash_or_name = NAME_TO_HASH.get(hash_or_name, 0)
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
            hash_or_name = NAME_TO_HASH.get(hash_or_name, 0)
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

# Primary weapons (rifles)
RIFLE_ENTITIES = [
    "M1903", "SREM", "Kar98K", "Mosin_Nagant", "G43",
    "M1Carbine", "RSC1918", "Winchester_1885", "Drilling",
    "Pedersen", "ModelD", "Thompson", "PPSH", "Type100",
    "Sjogren", "Gustaf",
    # Additional rifles
    "Lee_Enfield", "M1_Enfield", "DLC_Mosin", "Type1",
    "GEW_98_Overpressure", "1903_Trench", "G43_Kurz_Silenced",
]

# Secondary weapons (pistols)
PISTOL_ENTITIES = [
    "M1911", "M1911_Plus", "Luger", "Luger_Suppressed",
    "Nambu", "Webley", "Welrod", "Mk1_Welrod", "Mk2_Welrod",
    "Derringer", "Delisle", "M712", "Auto_Burglar",
    "Geret_06_Experimental_P_Plus",
]

# SMGs and automatic weapons
SMG_ENTITIES = [
    "GreaseGun", "StenMkII", "Welgun", "MP.40", "MP.44",
    "MG42", "SuperTommy", "Thompson_Plus",
]

# Special weapons
SPECIAL_WEAPON_ENTITIES = [
    "Pzb39", "Panzerfaust",
]

# Scopes
SCOPE_ENTITIES = [
    "M81_Scope", "M84_Scope", "A1_Optical", "A2_Optical",
    "No32_Mk1_Scope", "No32_Mk2_Scope", "A5_Winchester_Scope",
    "B4_Scope", "ZF41_Scope", "Zf4_scope", "PU_scope",
    "T99_Scope", "T97_Scope", "M1913_Scope",
]

# Suppressors
SUPPRESSOR_ENTITIES = [
    "Maxin_30_Suppressor", "Maxin_1910_Suppressor", "Moore_Suppressor",
    "Bramit_Suppressor", "Hub_23_Suppressor", "OSS_Suppressor",
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
    "Quad_M31_Magazine", "Quad_M31_Magazine_Carl_Gustaf",
    "Quad_M31_Magazine_Sten", "Quad_M31_Magazine_Sten_EMP",
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
    "Improved_Cylinder_Choke", "Improved_Cylinder_Choke_Sjogren",
    "Power_Hyrbid_Choke",
]

# Other attachments (stocks, grips, muzzle brakes, bayonets, etc.)
OTHER_ATTACHMENT_ENTITIES = [
    # Stocks
    "Featherweight_Stock", "GreaseGun_DefaultStock", "Gustaf_DefaultStock",
    "Heavy_Mp44_Stock", "Heavy_Wooden_Stock", "Lightweight_Frame_Stock",
    "Standard_Sten_Stock", "Stock_Removal",
    # Foregrips
    "Austen_Foregrip", "EMP_Foregrip", "Owen_Foregrip",
    "Reinforced Foregrip Bands", "Remove_Foregrip", "US_1911_Foregrip",
    # Grips
    "Sten_Mk5_Grip", "X3_Grip_Tape", "X6_Grip_Tape",
    # Muzzle brakes
    "Axis_mk2_MuzzleBrake", "Mclean_Muzzlebrake",
    "Mk1_Boys_MuzzleBreak", "Mk2_Boys_MuzzleBreak", "USGI_MuzzleBreak",
    # Bayonets
    "Rifle_Bayonet_1",
    # Construction / mechanism
    "Lightened_Elm_Construction", "Lightened_Firing_Mechanism",
    "Lightweight_712s", "SMG_Lightened_Bolt",
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
    RIFLE_ENTITIES + PISTOL_ENTITIES + SMG_ENTITIES
    + SPECIAL_WEAPON_ENTITIES
    + SCOPE_ENTITIES + SUPPRESSOR_ENTITIES
    + BARREL_ENTITIES + MAGAZINE_ENTITIES + IRONSIGHT_ENTITIES
    + CHOKE_ENTITIES + OTHER_ATTACHMENT_ENTITIES
)

# All weapon entity names (for the Weapons tab)
ALL_WEAPON_ENTITIES = (
    RIFLE_ENTITIES + PISTOL_ENTITIES + SMG_ENTITIES + SPECIAL_WEAPON_ENTITIES
)


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
        self._load()

    def _load(self) -> None:
        """Load and decompress the ASR file."""
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
            self._format = "ZBB"
            self.header = raw[:8]
            self._zbb_extra_header = raw[8:24]
            try:
                self.body = bytearray(zlib.decompress(raw[24:], 13))
            except zlib.error as e:
                raise ValueError(
                    f"Failed to decompress ZBB body: {e}"
                ) from e
        else:
            raise ValueError(
                f"Unknown file format: {raw[:8]!r} "
                f"(expected {MAGIC_ZLB!r} or {MAGIC_ZBB!r})"
            )

        self._scan_entities()

    def _scan_entities(self) -> None:
        """Scan the body for all known entity names and their properties.

        This is a two-phase process:
        1. Find all type=4 strings in the body, identifying known entity names.
        2. For each entity, scan a window around its name for properties.

        Phase 1 must complete before phase 2 so that property scanning can
        avoid picking up candidates that are closer to a neighboring entity.
        """
        self.entities.clear()
        self._all_strings.clear()

        # Phase 1: Find all string entities (type=4) using bytes.find for speed.
        # Strings can be at any byte offset (not 4-aligned).
        body_len = len(self.body)
        search_pos = 0
        type_tag = b'\x04\x00\x00\x00'
        entity_name_offsets: List[int] = []  # offsets of all found entity names
        while search_pos < body_len - 8:
            pos = self.body.find(type_tag, search_pos)
            if pos < 0:
                break
            str_len = struct.unpack("<I", self.body[pos + 4:pos + 8])[0]
            if 3 < str_len < 80 and pos + 8 + str_len <= body_len:
                try:
                    s = self.body[pos + 8:pos + 8 + str_len].decode("ascii")
                    # Allow alphanumerics, dots, underscores, hyphens, spaces,
                    # and parentheses (e.g. "MG42(HalfAmmo)").
                    if all(c.isalnum() or c in "._- ()" for c in s):
                        self._all_strings.append((pos, s))
                        if s in ALL_ENTITY_NAMES:
                            entity = Entity(name=s, name_offset=pos)
                            self.entities[s] = entity
                            entity_name_offsets.append(pos)
                except UnicodeDecodeError:
                    pass
            search_pos = pos + 1

        # Phase 2: Scan properties for each entity, now that all entity
        # name positions are known.  This allows us to skip candidates
        # that are closer to a neighboring entity's name.
        entity_name_offsets.sort()
        for entity in self.entities.values():
            self._scan_properties(entity, entity_name_offsets)

    def _scan_properties(self, entity: Entity,
                         all_name_offsets: List[int]) -> None:
        """Scan for float and int properties near an entity name string.

        Properties are 12-byte tuples: [type:4][value:4][hash:4].
        They are NOT necessarily 4-byte aligned, so we scan byte-by-byte.
        We search for known hash bytes, then validate the type and value.

        When multiple properties share the same hash (from neighboring
        child entities like barrels/magazines), we pick the best one
        using value-range heuristics.

        ``all_name_offsets`` is a sorted list of all entity name offsets,
        used to skip candidates that are closer to a neighboring entity.
        """
        # Search in a window around the entity name.
        # The original window (-3500 to +1200) covers the vast majority of
        # properties.  We extend the "after" limit to +5000 to catch
        # properties like PPSH FireRate at +4565 and RSC1918 MuzzleVelocity
        # at +2333.  The "before" limit stays at -3500.
        #
        # For candidates in the extended region (beyond the original window),
        # we apply a closest-entity check to avoid picking up properties that
        # belong to a neighboring entity.  Candidates within the original
        # window are always accepted (they were already validated by the
        # original parser).
        orig_start = max(0, entity.name_offset - 3500)
        orig_end = min(len(self.body), entity.name_offset + 1200)
        start = orig_start
        end = min(len(self.body), entity.name_offset + 5000)

        # Build a set of known hash bytes for fast searching
        hash_bytes_map = {}  # bytes -> hash_int
        for h in HASH_NAMES:
            hb = struct.pack("<I", h)
            hash_bytes_map[hb] = h

        # Collect all candidates: hash -> list of (offset, type, value)
        candidates: Dict[int, list] = {}
        for hb, h_int in hash_bytes_map.items():
            search_pos = start
            while search_pos < end - 12:
                pos = self.body.find(hb, search_pos, end)
                if pos < 0:
                    break
                if pos >= 8:
                    # For candidates in the extended region (outside the
                    # original -3500..+1200 window), skip if the hash
                    # position is closer to another entity's name.
                    if not (orig_start <= pos <= orig_end):
                        if self._is_closer_to_other_entity(
                            pos, entity.name_offset, all_name_offsets
                        ):
                            search_pos = pos + 1
                            continue
                    type_offset = pos - 8
                    value_offset = pos - 4
                    ptype = struct.unpack("<I", self.body[type_offset:type_offset + 4])[0]
                    if ptype == TYPE_FLOAT:
                        fv = struct.unpack("<f", self.body[value_offset:value_offset + 4])[0]
                        if -10000 < fv < 100000 and abs(fv) > 0.0001:
                            candidates.setdefault(h_int, []).append(
                                (value_offset, TYPE_FLOAT, fv)
                            )
                    elif ptype == TYPE_INT:
                        iv = struct.unpack("<I", self.body[value_offset:value_offset + 4])[0]
                        if 0 < iv < 10000:
                            candidates.setdefault(h_int, []).append(
                                (value_offset, TYPE_INT, iv)
                            )
                search_pos = pos + 1

        # Pick the best candidate for each hash using value-range heuristics
        for h_int, props in candidates.items():
            name = HASH_NAMES[h_int]
            best = self._pick_best_property(name, props, entity.name_offset)
            if best:
                offset, ptype, value = best
                entity.properties.append(Property(
                    type=ptype, offset=offset, hash=h_int,
                    name=name, value=value,
                ))

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
            "Damage": (0.01, 500),  # SMGs/shotguns can have Damage < 1
            "DamageSpread": (0.001, 500),  # Sjogren has 0.025
            "WindDrop": (0, 1),
            "RPM": (1, 1000),
            "FireRate": (1, 1000),
            "Recoil1_Vertical": (0, 10),
            "Recoil2_Horizontal": (-2, 10),
            "RecoilMult": (0, 5),
            "RecoilRecoveryTime": (0, 100),  # SMGs can have 50-90
            "RecoilResetSpeed": (0, 100),
            "ZoomMin": (1, 50),
            "ZoomMax": (1, 50),
            "ScopeInSpeed": (0.01, 1.0),
            "SwayAmount": (0, 1),
            "SwayRecovery": (0, 1),
            "SwayDrift": (0, 1),
            "SwayDecay": (0, 1),
            "AimStability": (0, 10),
            "ScopeSteadyTime": (0, 5),
            "HoldBreathDuration": (0, 5),
            "SwayPerShot": (0, 5),
            "SwayWalk": (0, 1),
            "SwayCrouch": (0, 5),
            "SwayProne": (0, 1),
            "DamageDropoff": (0, 500),
            "AudibleRangeBase": (0, 500),
            "MagazineCapacity": (1, 100),  # int only; PPSh drum has 71
        }

        vmin, vmax = RANGES.get(name, (-10000, 100000))

        # Filter by value range
        valid = []
        for offset, ptype, value in candidates:
            if vmin <= value <= vmax:
                valid.append((offset, ptype, value))

        # For MagazineCapacity, only accept int type candidates.
        # Float "MagazineCapacity" values are always false positives from
        # neighboring entities whose binary data happens to contain the
        # hash bytes at the right position.
        if name == "MagazineCapacity":
            int_props = [c for c in valid if c[1] == TYPE_INT]
            if int_props:
                valid = int_props
            else:
                return None  # No valid int MagazineCapacity found

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
        if not prop or not prop.is_float:
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
        if not prop or not prop.is_int:
            return False
        struct.pack_into("<I", self.body, prop.offset, value)
        prop.value = value
        return True

    def save(self, output_path: str) -> None:
        """Recompress and write the modified ASR file.

        Preserves the original container format (AsuraZlb or AsuraZbb).
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
        else:
            # Default to AsuraZlb format
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
