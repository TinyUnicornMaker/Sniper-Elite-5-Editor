"""Read/write player skill floats in common.asr block 0."""
from __future__ import annotations

import os
import struct

from gui.asr_backup import ensure_backup, looks_healthy
from gui.player_catalog import (
    PLAYER_SKILLS, PlayerSkill, resilience_scale, LETHAL_DIFFICULTY,
    clamp_skill_float,
)
from gui.zbb_util import read_block, rewrite_block, validate_zbb

SKILL_BLOCK = 0
TYPE1 = b"\x01\x00\x00\x00"


def _skill_by_name(name: str) -> PlayerSkill | None:
    for s in PLAYER_SKILLS:
        if s.name == name or s.display == name:
            return s
    return None


def _find_skill_float(block: bytes, skill: PlayerSkill) -> tuple[int, float] | None:
    """Return (offset, value) of the type-1 tuple for *skill*, or None.

    Match is name-scoped, then hash. Several perks share a hash, so a
    hash-only or value-only replace would overwrite the wrong floats.
    """
    name = skill.name.encode("ascii")
    pos = 0
    needle_hash = struct.pack("<I", skill.hash)
    while True:
        i = block.find(name, pos)
        if i < 0:
            return None
        window = block[i : i + 180]
        off = 0
        while True:
            j = window.find(TYPE1, off)
            if j < 0:
                break
            if j + 12 <= len(window) and window[j + 8 : j + 12] == needle_hash:
                val = struct.unpack_from("<f", window, j + 4)[0]
                return i + j + 4, val
            off = j + 1
        pos = i + 1


def read_skills(block: bytes) -> dict[str, float]:
    out: dict[str, float] = {}
    for s in PLAYER_SKILLS:
        hit = _find_skill_float(block, s)
        if hit:
            out[s.name] = hit[1]
    return out


def load_skill_block(base_path: str) -> bytes:
    with open(base_path, "rb") as fh:
        raw = fh.read()
    if raw[:8] != b"AsuraZbb":
        raise ValueError(f"Not AsuraZbb ({raw[:8]!r})")
    _, _, data = read_block(raw, SKILL_BLOCK)
    return data


def apply_skills(
    base_path: str,
    values: dict[str, float],
    backup: bool = True,
) -> tuple[int, str]:
    """Write skill magnitudes at the name+hash offset only.

    Values are floats. Exact 0.0 is raised to a small positive floor —
    zeroing these perks previously crashed the game on launch.
    """
    if not base_path or not os.path.isfile(base_path):
        return 0, "common.asr not found"
    return 0, (
        "Player-skill writes into common.asr block 0 are disabled — "
        "recompressing that block crashed launch."
    )
    live_err = looks_healthy(base_path)
    if live_err:
        return 0, (
            f"Refusing to write — common.asr is unhealthy ({live_err}). "
            "Verify game files in Steam, then reopen the folder."
        )
    if backup:
        ok, bak_msg = ensure_backup(base_path)
        if not ok:
            return 0, bak_msg

    wanted: list[tuple[PlayerSkill, float]] = []
    for name, raw_val in values.items():
        skill = _skill_by_name(name)
        if not skill:
            continue
        wanted.append((skill, clamp_skill_float(raw_val, skill.vmin, skill.vmax)))
    if not wanted:
        return 0, "No recognised skill names to write"

    with open(base_path, "rb") as fh:
        raw = fh.read()
    if raw[:8] != b"AsuraZbb":
        return 0, f"Not AsuraZbb ({raw[:8]!r})"

    written: list[str] = []
    missing: list[str] = []

    def mutate(block: bytearray) -> None:
        for skill, new_val in wanted:
            hit = _find_skill_float(bytes(block), skill)
            if not hit:
                missing.append(skill.name)
                continue
            off, old = hit
            packed = struct.pack("<f", new_val)
            if block[off : off + 4] == packed:
                continue
            block[off : off + 4] = packed
            written.append(f"{skill.display} {old:g}→{new_val:g}")

    try:
        new_raw = rewrite_block(raw, SKILL_BLOCK, mutate)
    except Exception as exc:
        return 0, f"Block 0 rewrite failed: {exc}"

    if not written:
        extra = f" (missing: {', '.join(missing)})" if missing else ""
        return 0, "No skill bytes changed" + extra

    err = validate_zbb(new_raw)
    if err:
        return 0, (
            f"Refused to save — archive index would break ({err}). "
            "Leave common.asr alone and verify game files if it already fails."
        )

    with open(base_path, "wb") as fh:
        fh.write(new_raw)
    msg = "Wrote " + ", ".join(written)
    if missing:
        msg += f" (not found: {', '.join(missing)})"
    return len(written), msg


def apply_resilience_step(base_path: str, step: int) -> tuple[int, str]:
    """Scale every resilience-tagged skill from its default by *step* (0–4)."""
    scale = resilience_scale(step)
    values = {
        s.name: clamp_skill_float(s.default * scale, s.vmin, s.vmax)
        for s in PLAYER_SKILLS
        if s.resilience
    }
    n, msg = apply_skills(base_path, values)
    return n, f"{msg} (resilience step={step}, scale={scale:g})"


def apply_lethal_player(base_path: str) -> tuple[int, str]:
    """Historical helper for the removed one-shot button.

    Kept for scripts; prefer in-game Custom Difficulty for lethality.
    """
    return apply_resilience_step(base_path, LETHAL_DIFFICULTY["player_resilience"])
