"""Load in-game display names and attachment identity from SE5 data files.

Key discovery (decoded from entity type-3 tags + loadout HTXT):

* After each attachment entity name the game stores::

      (att_id, 0x90BC6B2B)   # attachment identity
      (loc_id, 0x66AD0BDC)   # localization string hash

* ``loc_id`` indexes a UTF-16 string in ``text/PC/LOADOUT/loadout.asr_en``
  (HTXT). That string is the **exact in-game short name** shown in the
  customization UI (e.g. ``Heavy Parkerized``, ``Overpressure Power``,
  ``ZF4 S``).

* Entities that share the same ``att_id`` are mesh/weapon variants of one
  logical upgrade (e.g. all ``*_LongBarrel`` → ``Extended Marksmen``).

* Entities that share the same *display text* but different ``loc_id`` are
  distinct upgrades (still present separately if both apply).

This module exposes those tables so the editor can:

1. Show correct UI labels (not hand-maintained guesses)
2. Deduplicate false doubles (two "Heavy Parkerized" from wrong labels)
3. Apply edits to every entity alias of the same logical attachment
"""

from __future__ import annotations

import re
import struct
import zlib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

ENTITY_MARKER = b"\x03\x00\x00\x00\x99\x9b\xf8\x55\x00\x00\x00\x00"
ATT_ID_TAG = 0x90BC6B2B
LOC_ID_TAG = 0x66AD0BDC
WPN_ID_TAG = 0xF61039E0


@dataclass
class EntityMeta:
    name: str
    att_id: int | None = None
    loc_id: int | None = None
    wpn_id: int | None = None
    display_name: str | None = None


def _load_zlb(path: Path) -> bytes:
    data = path.read_bytes()
    if data[:8] == b"AsuraZlb":
        _f, csize, _u = struct.unpack_from("<III", data, 8)
        for wbits in (13, 15, -15, 12):
            try:
                return zlib.decompress(data[20 : 20 + csize], wbits)
            except Exception:
                continue
    return data


def parse_htxt_strings(data: bytes) -> dict[int, str]:
    """Parse Asura HTXT body: repeated ``(hash:u32, char_count:u32, utf16le)``."""
    entries: dict[int, str] = {}
    i = 0
    n = len(data)
    while i + 8 <= n:
        h, ln = struct.unpack_from("<II", data, i)
        if not (1 <= ln <= 400) or i + 8 + ln * 2 > n:
            i += 4
            continue
        try:
            s = data[i + 8 : i + 8 + ln * 2].decode("utf-16-le")
        except Exception:
            i += 4
            continue
        if all((c.isprintable() or c in "\n\r\t\x00") for c in s) and re.search(
            r"[A-Za-z]", s
        ):
            s = s.replace("\x00", "").strip()
            if s:
                entries[h] = s
            i = i + 8 + ln * 2
        else:
            i += 4
    return entries


@lru_cache(maxsize=4)
def load_loadout_strings(loadout_dir: str) -> dict[int, str]:
    """hash → display string from loadout.asr_en (+ patch overrides if present)."""
    root = Path(loadout_dir)
    out: dict[int, str] = {}
    base = root / "loadout.asr_en"
    if base.is_file():
        out.update(parse_htxt_strings(base.read_bytes()))
    # asrpatch is PNFO/ASCII — ignore for values; keys are separate
    return out


def _parse_entity_tags(buf: bytes) -> dict[str, EntityMeta]:
    ents: dict[str, EntityMeta] = {}
    pos = 0
    while True:
        p = buf.find(ENTITY_MARKER, pos)
        if p < 0:
            break
        np = p + 12
        if np + 8 > len(buf) or buf[np : np + 4] != b"\x04\x00\x00\x00":
            pos = p + 1
            continue
        slen = struct.unpack_from("<I", buf, np + 4)[0]
        if not (2 <= slen <= 80) or np + 8 + slen + 4 > len(buf):
            pos = p + 1
            continue
        try:
            name = buf[np + 8 : np + 8 + slen].decode("ascii")
        except Exception:
            pos = p + 1
            continue
        if not re.match(r"^[A-Za-z]", name):
            pos = p + 1
            continue
        meta = EntityMeta(name=name)
        i = np + 8 + slen + 4
        while i + 12 <= len(buf) and i < np + 8 + slen + 250:
            t = struct.unpack_from("<I", buf, i)[0]
            if t != 3:
                break
            a, b = struct.unpack_from("<II", buf, i + 4)
            if b == ATT_ID_TAG:
                meta.att_id = a
            elif b == LOC_ID_TAG:
                meta.loc_id = a
            elif b == WPN_ID_TAG:
                meta.wpn_id = a
            i += 12
            if buf[i : i + 12] == ENTITY_MARKER:
                break
        ents[name] = meta
        pos = p + 12
    return ents


@lru_cache(maxsize=2)
def load_entity_meta(
    asrpatch_path: str,
    common_asr_path: str | None = None,
    loadout_dir: str | None = None,
) -> dict[str, EntityMeta]:
    """Entity name → meta (att_id, loc_id, display_name)."""
    ents: dict[str, EntityMeta] = {}
    if common_asr_path and Path(common_asr_path).is_file():
        data = Path(common_asr_path).read_bytes()
        if data[:8] == b"AsuraZbb":
            fc = struct.unpack_from("<I", data, 16)[0]
            try:
                b0 = zlib.decompress(data[24 : 24 + fc], 12)
            except Exception:
                b0 = zlib.decompress(data[24 : 24 + fc], -15)
            ents.update(_parse_entity_tags(b0))
            # block 1 often holds more entity defs
            off = 24 + fc
            if off + 8 < len(data):
                cs, _us = struct.unpack_from("<II", data, off)
                off += 8
                if 0 < cs and off + cs <= len(data):
                    try:
                        b1 = zlib.decompress(data[off : off + cs], 12)
                        ents.update(_parse_entity_tags(b1))
                    except Exception:
                        pass

    if asrpatch_path and Path(asrpatch_path).is_file():
        ents.update(_parse_entity_tags(_load_zlb(Path(asrpatch_path))))

    loc: dict[int, str] = {}
    if loadout_dir:
        try:
            loc = load_loadout_strings(loadout_dir)
        except Exception:
            loc = {}

    for meta in ents.values():
        if meta.loc_id is not None and meta.loc_id in loc:
            meta.display_name = loc[meta.loc_id]

    return ents


def display_name_for(entity: str, meta: dict[str, EntityMeta] | None = None) -> str | None:
    if meta and entity in meta and meta[entity].display_name:
        return meta[entity].display_name
    return None


def group_aliases_by_att_id(
    entities: list[str], meta: dict[str, EntityMeta]
) -> dict[int, list[str]]:
    """att_id → [entity names] for known identities."""
    groups: dict[int, list[str]] = {}
    for e in entities:
        m = meta.get(e)
        if m and m.att_id is not None:
            groups.setdefault(m.att_id, []).append(e)
    return groups


def dedupe_entities(
    entities: list[str],
    meta: dict[str, EntityMeta],
    prop_counts: dict[str, int] | None = None,
) -> tuple[list[str], dict[str, list[str]]]:
    """Collapse entities that are the same in-game attachment.

    Priority:
    1. Same ``loc_id`` (same localization string → same UI label identity)
    2. Same ``att_id`` when choosing a representative for weapon-prefix variants
       is handled by the caller (pass only candidates for one weapon)

    Returns ``(representatives, aliases_map)`` where aliases_map[rep] lists
    every entity that should receive the same property writes as *rep*.
    """
    prop_counts = prop_counts or {}

    # Group by loc_id when available; else by unique name
    groups: dict[str | int, list[str]] = {}
    for e in entities:
        m = meta.get(e)
        key: str | int
        if m and m.loc_id is not None:
            key = ("loc", m.loc_id)  # type: ignore[assignment]
        elif m and m.display_name:
            key = ("name", m.display_name.lower())  # type: ignore[assignment]
        else:
            key = ("ent", e)  # type: ignore[assignment]
        # fix key typing — use string keys
    groups2: dict[tuple, list[str]] = {}
    for e in entities:
        m = meta.get(e)
        if m and m.loc_id is not None:
            key: tuple = ("loc", m.loc_id)
        elif m and m.display_name:
            key = ("dn", m.display_name.lower())
        else:
            key = ("ent", e)
        groups2.setdefault(key, []).append(e)

    representatives: list[str] = []
    aliases: dict[str, list[str]] = {}
    for _key, members in groups2.items():
        # Prefer entity with most properties (real stats over empty stubs)
        members_sorted = sorted(
            members,
            key=lambda n: (
                prop_counts.get(n, 0),
                # prefer non-suffixed generic over _Sjogren/_Drilling stubs
                0 if not re.search(r"_(Sjogren|Drilling|M12)$", n) else -1,
                -len(n),
            ),
            reverse=True,
        )
        rep = members_sorted[0]
        representatives.append(rep)
        aliases[rep] = members_sorted

    return sorted(representatives), aliases
