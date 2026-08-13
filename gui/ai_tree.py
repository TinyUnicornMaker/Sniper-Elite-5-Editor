"""Read/write named floats in the AI behaviour tree (common.asr block 405).

These are the knobs that actually change how enemies fight. Character
class entities in the asrpatch have no combat floats — they pick a
behaviour role, and the role's nodes live here.

Each parameter is found by a nearby ASCII marker plus a default byte
pattern (same technique as the SE3 Acquiring Timer).

IMPORTANT — block 405 writes crash launch
----------------------------------------
Every attempt to write this block (full recompress, same-size pad,
in-place Huffman patch of the acquiring timer) crashed Sniper Elite 5
on load. ``apply_params`` / ``write_acquiring_timer`` refuse all writes.

``acquiring_timer`` is kept only for research / read helpers. The
Sniper Tweaks UI no longer exposes it: lock-on speed is covered
in-game by Enemy Responsiveness / Enemy Sniper Skill (Custom
Difficulty). See ENEMY_STATS.md and the module header of
gui/sniper_tweaks.py.
"""
from __future__ import annotations

import os
import struct
from collections import Counter
from dataclasses import dataclass

from gui.asr_backup import ensure_backup
from gui.deflate_patch import patch_wrapped_floats
from gui.zbb_util import navigate_to_block, read_block, rewrite_block, validate_zbb

AI_BLOCK = 405

# Exact original acquiring-timer bytes (0.362003) — keep for round-trip.
ACQUIRE_DEFAULT_BYTES = bytes.fromhex("6d58b93e")
ACQUIRE_DEFAULT = 0.362003


@dataclass(frozen=True)
class AiParam:
    key: str
    label: str
    tooltip: str
    marker: bytes
    default: float
    default_bytes: bytes
    vmin: float
    vmax: float
    step: float
    decimals: int
    # Historical "lethal" target; never applied (writes crash launch).
    lethal: float | None
    window: int = 220
    # If set, only replace floats in this inclusive range (avoids -1 sentinels)
    match_min: float | None = None
    match_max: float | None = None
    # Bytes that immediately precede the float (keeps us off animation junk)
    prefix: bytes = b"\x03\x00\x00\x00\x04\x00\x00\x00\x03\x00\x00\x00"


# Tunables discovered in block 405 (03-04-03 float slots + type-2 timer).
AI_PARAMS: list[AiParam] = [
    AiParam(
        "acquiring_timer",
        "Acquiring Timer",
        "SE3 lock-on time in seconds. How long after spotting you before "
        "the AI commits to a shot. Default 0.362. Lower = they fire sooner.",
        marker=b"Acquiring Timer",
        default=ACQUIRE_DEFAULT,
        default_bytes=ACQUIRE_DEFAULT_BYTES,
        vmin=0.001,
        vmax=2.0,
        step=0.01,
        decimals=3,
        # Fastest Huffman-compatible float (~0.033 s). Never written —
        # all block-405 timer writes crashed launch.
        lethal=0.033,
        window=300,
        match_min=0.001,
        match_max=2.0,
        prefix=b"\x02\x00\x00\x00",
    ),
    AiParam(
        "lookat_fire_delay",
        "Aim-then-Fire Delay",
        "Delay on the LookAtAndFire node (seconds). Lower = they snap "
        "from looking to shooting faster.",
        marker=b"LookAtAndFire",
        default=0.25,
        default_bytes=struct.pack("<f", 0.25),
        vmin=0.001,
        vmax=5.0,
        step=0.01,
        decimals=3,
        lethal=None,
        match_min=0.01,
        match_max=2.0,
        prefix=b"\x04\x00\x00\x00",
    ),
    AiParam(
        "threat_range",
        "Threat Engage Range",
        "RangeCheckToCurrentThreat distance (metres). How far away the "
        "AI will treat you as a combat threat AFTER they already know "
        "you exist. Default 23 m. This is not vision / detection range "
        "and will not make snipers see you at 500 m. Writes crash launch.",
        marker=b"RangeCheckToCurrentThreat",
        default=23.0,
        default_bytes=struct.pack("<f", 23.0),
        vmin=1.0,
        vmax=80.0,
        step=5.0,
        decimals=0,
        lethal=None,
        match_min=5.0,
        match_max=80.0,
    ),
    AiParam(
        "look_at_range",
        "Look-At Range",
        "Look At node distance (metres). Default 15 m. Combat look "
        "distance, not how far they can spot you. Writes crash launch.",
        marker=b"Look At",
        default=15.0,
        default_bytes=struct.pack("<f", 15.0),
        vmin=1.0,
        vmax=80.0,
        step=5.0,
        decimals=0,
        lethal=None,
        match_min=1.0,
        match_max=80.0,
    ),
    AiParam(
        "close_combat_range",
        "Close-Combat Range",
        "Close Combat node distance (metres). Infantry close to this "
        "range before the close-fight loop.",
        marker=b"Close Combat",
        default=25.0,
        default_bytes=struct.pack("<f", 25.0),
        vmin=1.0,
        vmax=500.0,
        step=1.0,
        decimals=0,
        lethal=None,
        match_min=1.0,
        match_max=500.0,
    ),
    AiParam(
        "advance_range",
        "Advance Range",
        "Advance On Position distance (metres).",
        marker=b"Advance On Position",
        default=30.0,
        default_bytes=struct.pack("<f", 30.0),
        vmin=1.0,
        vmax=500.0,
        step=1.0,
        decimals=0,
        lethal=None,
        match_min=1.0,
        match_max=500.0,
    ),
    AiParam(
        "movement_speed",
        "Movement Speed",
        "AI Movement Speed scale. 0.5 is the stock value. Higher = they "
        "close and reposition faster.",
        marker=b"Movement Speed",
        default=0.5,
        default_bytes=struct.pack("<f", 0.5),
        vmin=0.05,
        vmax=5.0,
        step=0.05,
        decimals=2,
        lethal=None,
        match_min=0.05,
        match_max=5.0,
    ),
    AiParam(
        "artillery_range",
        "Artillery Combat Range",
        "Artillery Combat node distance (metres).",
        marker=b"Artillery Combat",
        default=25.0,
        default_bytes=struct.pack("<f", 25.0),
        vmin=1.0,
        vmax=2000.0,
        step=5.0,
        decimals=0,
        lethal=None,
        match_min=1.0,
        match_max=2000.0,
    ),
]

AI_PARAM_BY_KEY = {p.key: p for p in AI_PARAMS}

# Removed from UI: was only used by "Make All Snipers One-Shot Lethal",
# which only tried acquiring_timer and always crashed. Do not re-enable.
SNIPER_LETHAL_KEYS: tuple[str, ...] = ()


def _in_range(val: float, p: AiParam) -> bool:
    lo = p.match_min if p.match_min is not None else p.vmin
    hi = p.match_max if p.match_max is not None else p.vmax
    return lo <= val <= hi


def _marker_positions(block: bytes, marker: bytes) -> list[int]:
    out: list[int] = []
    pos = 0
    while True:
        pos = block.find(marker, pos)
        if pos < 0:
            break
        out.append(pos)
        pos += len(marker)
    return out


def _floats_after_prefix(block: bytes, param: AiParam) -> list[tuple[int, float]]:
    """(offset_of_float, value) for every prefix+float near a marker."""
    marks = _marker_positions(block, param.marker)
    found: list[tuple[int, float]] = []
    pref = param.prefix
    for mp in marks:
        start = max(0, mp)
        end = min(len(block) - len(pref) - 4, mp + param.window)
        pos = start
        while pos <= end:
            hit = block.find(pref, pos, end + len(pref))
            if hit < 0:
                break
            foff = hit + len(pref)
            if foff + 4 <= len(block):
                val = struct.unpack_from("<f", block, foff)[0]
                if val == val and _in_range(val, param):
                    found.append((foff, val))
            pos = hit + 1
    return found


def read_param(block: bytes, param: AiParam) -> float | None:
    """Return the current value of *param*, or None if not found."""
    hits = _floats_after_prefix(block, param)
    if not hits:
        return None
    from collections import Counter
    counted = Counter(round(v, 4) for _off, v in hits)
    return counted.most_common(1)[0][0]


def read_all_params(block: bytes) -> dict[str, float]:
    out: dict[str, float] = {}
    for p in AI_PARAMS:
        v = read_param(block, p)
        if v is not None:
            out[p.key] = v
    return out


def load_block(base_path: str) -> bytes:
    with open(base_path, "rb") as fh:
        raw = fh.read()
    if raw[:8] != b"AsuraZbb":
        raise ValueError(f"Not AsuraZbb (got {raw[:8]!r})")
    _, _, data = read_block(raw, AI_BLOCK)
    return data


def _replace_near_markers(
    block: bytearray,
    param: AiParam,
    new_value: float,
) -> int:
    marks = _marker_positions(bytes(block), param.marker)
    if not marks:
        return 0
    current = read_param(bytes(block), param)
    if current is None:
        return 0
    if abs(current - new_value) < 10 ** (-(param.decimals + 1)):
        return 0

    if abs(current - param.default) < 0.001:
        old_bytes = param.default_bytes
    else:
        old_bytes = struct.pack("<f", current)
    if abs(new_value - param.default) < 0.001:
        new_bytes = param.default_bytes
    else:
        new_bytes = struct.pack("<f", new_value)

    n = 0
    for foff, val in _floats_after_prefix(bytes(block), param):
        if abs(val - current) > 0.02 and abs(val - param.default) > 0.02:
            continue
        have = block[foff : foff + 4]
        if have == old_bytes or abs(val - current) < 0.02:
            block[foff : foff + 4] = new_bytes
            n += 1
    # Acquiring timer also sits as a raw 4-byte pattern next to
    # "Set Variable" copies — sweep those so all 4 stay in sync.
    if param.key == "acquiring_timer" and n < 4:
        pos = 0
        blob = bytes(block)
        while True:
            pos = blob.find(old_bytes, pos)
            if pos < 0:
                break
            if any(abs(pos - mp) < param.window for mp in marks):
                if block[pos : pos + 4] == old_bytes:
                    block[pos : pos + 4] = new_bytes
                    n += 1
                    blob = bytes(block)
            pos += 4
    return n


# type-2 slot that actually holds the SE3 timer: 02 00 00 00 <float> 02 00 00 00
_TIMER_WRAP = b"\x02\x00\x00\x00"
_TIMER_WRAP_AFTER = b"\x02\x00\x00\x00"


def _apply_timer_to_block(block: bytearray, new_value: float) -> tuple[int, str]:
    """Replace only wrapped SE3 Acquiring Timer floats in block 405.

    Matches ``02 00 00 00 <float> 02 00 00 00`` within 300 bytes of an
    ``Acquiring Timer`` marker. A bare 4-byte sweep can hit unrelated
    values and crash the game on load.
    """
    marker = b"Acquiring Timer"
    window = 300
    marker_positions: list[int] = []
    pos = 0
    blob0 = bytes(block)
    while True:
        pos = blob0.find(marker, pos)
        if pos < 0:
            break
        marker_positions.append(pos)
        pos += len(marker)
    if not marker_positions:
        return 0, "No 'Acquiring Timer' markers found in the behaviour tree block."

    if abs(new_value - ACQUIRE_DEFAULT) < 0.001:
        new_bytes = ACQUIRE_DEFAULT_BYTES
    else:
        new_bytes = struct.pack("<f", new_value)

    hits: list[tuple[int, float]] = []
    for mp in marker_positions:
        start = max(0, mp - window)
        end = min(len(block) - 12, mp + window)
        pos = start
        while pos <= end:
            hit = block.find(_TIMER_WRAP, pos, end + 4)
            if hit < 0:
                break
            foff = hit + 4
            if block[foff + 4 : foff + 8] == _TIMER_WRAP_AFTER:
                val = struct.unpack_from("<f", block, foff)[0]
                if val == val and 0.001 <= val <= 2.0:
                    hits.append((foff, val))
            pos = hit + 1

    if not hits:
        return 0, "No wrapped acquiring-timer floats found near the markers."

    # The four node copies share one value. Use the most common in-range float.
    counted = Counter(round(v, 4) for _off, v in hits)
    current_value, _n = counted.most_common(1)[0]
    if abs(current_value - new_value) < 0.001:
        return 0, (
            f"AI acquiring timer is already set to {current_value:.4f}. "
            "No changes needed."
        )

    replacements = 0
    for foff, val in hits:
        if abs(val - current_value) > 0.02:
            continue
        if block[foff : foff + 4] == new_bytes:
            continue
        block[foff : foff + 4] = new_bytes
        replacements += 1
    if replacements == 0:
        return 0, (
            f"Could not replace the current timer value ({current_value:.4f})."
        )
    return replacements, (
        f"Modified AI acquiring timer — replaced {replacements} "
        f"occurrence(s) of {current_value:.4f} with {new_value:.4f}."
    )


def _wrapped_timer_offsets(block: bytes) -> list[int]:
    """Start offsets of every wrapped acquiring-timer float, including copies."""
    marker = b"Acquiring Timer"
    window = 300
    marks: list[int] = []
    pos = 0
    while True:
        pos = block.find(marker, pos)
        if pos < 0:
            break
        marks.append(pos)
        pos += len(marker)
    offs: list[int] = []
    wrap = b"\x02\x00\x00\x00"
    for mp in marks:
        start = max(0, mp - window)
        end = min(len(block) - 12, mp + window)
        pos = start
        while pos <= end:
            hit = block.find(wrap, pos, end + 4)
            if hit < 0:
                break
            foff = hit + 4
            if block[foff + 4 : foff + 8] == wrap:
                val = struct.unpack_from("<f", block, foff)[0]
                if val == val and 0.001 <= val <= 2.0:
                    offs.append(foff)
            pos = hit + 1
    return sorted(set(offs))


def write_acquiring_timer(
    base_path: str,
    new_value: float,
    backup: bool = True,
) -> tuple[bool, str]:
    """Refuse acquiring-timer writes (always crash launch).

    Proven-fail methods (do not retry without a new approach):
    - Python zlib recompress of block 405 (layout shift or identical pad)
    - Same-size zero-pad rewrite of the compressed slot
    - In-place Huffman patch of the original stream (~0.033 s, 14 bytes)

    Use in-game Custom Difficulty instead (Enemy Sniper Skill /
    Responsiveness). The float itself is documented in AI_PARAMS.
    """
    return False, (
        "Writing the AI acquiring timer crashes Sniper Elite 5 on launch. "
        "common.asr was not changed. Use in-game Custom Difficulty."
    )


def apply_params(
    base_path: str,
    values: dict[str, float],
    backup: bool = True,
) -> tuple[int, str]:
    """Refuse all block-405 writes (crash launch). See module docstring."""
    return 0, (
        "AI-tree writes into common.asr block 405 crash the game on launch. "
        "common.asr was not changed."
    )


def apply_sniper_lethal(base_path: str) -> tuple[int, str]:
    """Removed from UI. Kept so old call sites get a clear refusal."""
    return 0, (
        "One-shot sniper preset removed: it only tried the acquire timer "
        "(crashes launch) and duplicated Custom Difficulty. "
        "common.asr was not changed."
    )


def reset_params(base_path: str, keys: list[str] | None = None) -> tuple[int, str]:
    """Restore listed (or all) params to shipped defaults."""
    use = keys or [p.key for p in AI_PARAMS]
    values = {k: AI_PARAM_BY_KEY[k].default for k in use if k in AI_PARAM_BY_KEY}
    return apply_params(base_path, values)
