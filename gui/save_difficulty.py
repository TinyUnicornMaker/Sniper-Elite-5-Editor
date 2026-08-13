"""Read/write Custom Difficulty tokens in SE5 campaign and profile saves.

Research / documentation helpers only — the Save Difficulty tab is not
wired into the main window. See ENEMY_STATS.md.

Each Combat / toughness slider is a 4-byte runtime token in a 96-byte
trailer table (not a 0–4 int, not in common.asr). The table can move
when the cpnf header grows; locate it by signature, not a fixed offset.

Only two observed steps per slider are known. Labels are those steps,
not the full Greatly Reduced → Greatly Increased range.

In-place 4-byte patches only. Do not grow or recompress the save.
Quit the game before writing or an autosave will overwrite the patch.
"""
from __future__ import annotations

import os
import re
import shutil
import struct
import tempfile
from dataclasses import dataclass, field

APP_ID = "1029690"
TABLE_SIG = 0x3FA777FE
TABLE_SIZE = 96
SEARCH_LIMIT = 16384
SEP_A = 52
SEP_B = 92

_ENVS_RE = re.compile(rb"Envs\\(M\d+_[A-Za-z0-9]+)")


@dataclass(frozen=True)
class SliderStep:
    token: int
    label: str
    deadly: bool = False


@dataclass(frozen=True)
class Slider:
    key: str
    label: str
    rel: int
    tip: str
    steps: tuple[SliderStep, ...]


# rel = byte offset from the 0x3FA777FE table start.
SLIDERS: tuple[Slider, ...] = (
    Slider(
        "player_resilience", "Player Resilience", 16,
        "How much damage YOU take, including bleeds. "
        "The +1 token from this session made you more vulnerable.",
        (
            SliderStep(0x349D2BE6, "Tougher (observed)"),
            SliderStep(0x642D90B0, "More vulnerable (observed +1)", True),
        ),
    ),
    Slider(
        "health_regen", "Health Regeneration", 64,
        "How much health comes back, and how fast. "
        "The +1 token from this session is slower / less regen.",
        (
            SliderStep(0xB619DE2B, "More regen (observed)"),
            SliderStep(0x3D802D75, "Less / slower (observed +1)", True),
        ),
    ),
    Slider(
        "enemy_resilience", "Enemy Resilience", 20,
        "How tanky enemies are against YOUR shots. "
        "Higher does not make their snipers deadlier.",
        (
            SliderStep(0xF0CD89E9, "Lower (observed)"),
            SliderStep(0x1208795C, "Tankier (observed +1)"),
        ),
    ),
    Slider(
        "enemy_sniper_skill", "Enemy Sniper Skill", 80,
        "Sniper lock / lead / miss once they are in a sniper fight.",
        (
            SliderStep(0x3AD9E73D, "Observed"),
            SliderStep(0x35C38F87, "Observed +1 (harder)", True),
        ),
    ),
    Slider(
        "enemy_accuracy", "Enemy Accuracy", 40,
        "Hit chance for every enemy, not only snipers.",
        (
            SliderStep(0x0DCBFB91, "Observed"),
            SliderStep(0x5562CAA0, "Observed +1 (harder)", True),
        ),
    ),
    Slider(
        "enemy_skill", "Enemy Skill", 48,
        "General intelligence: cover, flanking, which goal.",
        (
            SliderStep(0x5BE71758, "Observed"),
            SliderStep(0x0C56C54B, "Observed +1 (harder)", True),
        ),
    ),
    Slider(
        "enemy_aggression", "Enemy Aggression", 36,
        "How hard they hunt after they know you exist.",
        (
            SliderStep(0x0A9717DB, "Observed"),
            SliderStep(0x8EBC652A, "Observed +1 (harder)", True),
        ),
    ),
    Slider(
        "enemy_perceptiveness", "Enemy Perceptiveness", 56,
        "Hearing and vision scale. Only Reduced and Normal are mapped. "
        "There is no 500 m field; this is the real sight-range knob.",
        (
            SliderStep(0x97617C4C, "Reduced"),
            SliderStep(0xA3CB2E99, "Normal", True),
        ),
    ),
    Slider(
        "enemy_responsiveness", "Enemy Responsiveness", 60,
        "How fast the awareness meter climbs, and how fast they act.",
        (
            SliderStep(0xA5326FEB, "Observed"),
            SliderStep(0x302E451E, "Observed +1 (harder)", True),
        ),
    ),
)

SLIDER_BY_KEY = {s.key: s for s in SLIDERS}

# Incoming-fire preset: tokens that hurt the player. Leaves enemy
# resilience alone (tankier enemies do not help their shots).
DEADLY_KEYS = {
    "player_resilience",
    "health_regen",
    "enemy_sniper_skill",
    "enemy_accuracy",
    "enemy_skill",
    "enemy_aggression",
    "enemy_perceptiveness",
    "enemy_responsiveness",
}


@dataclass
class SaveSlot:
    path: str
    name: str
    mtime: float
    kind: str  # "profile" | "campaign"
    mission: str
    table_off: int | None
    tokens: dict[str, int] = field(default_factory=dict)


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _known_tokens() -> set[int]:
    return {step.token for sl in SLIDERS for step in sl.steps}


def _looks_like_table(data: bytes, off: int) -> bool:
    if off < 0 or off + TABLE_SIZE > len(data):
        return False
    if _u32(data, off) != TABLE_SIG:
        return False
    if _u32(data, off + SEP_A) != 0 or _u32(data, off + SEP_B) != 0:
        return False
    known = _known_tokens()
    hits = 0
    for sl in SLIDERS:
        if _u32(data, off + sl.rel) in known:
            hits += 1
    return hits >= 2


def locate_table(data: bytes) -> int | None:
    """Return file offset of the 96-byte token table, or None."""
    needle = struct.pack("<I", TABLE_SIG)
    limit = min(len(data), SEARCH_LIMIT)
    start = 0
    while True:
        i = data.find(needle, start, limit)
        if i < 0:
            break
        if _looks_like_table(data, i):
            return i
        start = i + 1
    return None


def read_tokens(data: bytes, table_off: int | None = None) -> dict[str, int]:
    if table_off is None:
        table_off = locate_table(data)
    if table_off is None:
        return {}
    return {sl.key: _u32(data, table_off + sl.rel) for sl in SLIDERS}


def mission_label(data: bytes) -> str:
    m = _ENVS_RE.search(data[:SEARCH_LIMIT])
    if not m:
        return ""
    raw = m.group(1).decode("ascii", errors="replace")
    return raw.replace("_", " ", 1)


def step_for_token(slider: Slider, token: int) -> SliderStep | None:
    for step in slider.steps:
        if step.token == token:
            return step
    return None


def deadly_tokens() -> dict[str, int]:
    out: dict[str, int] = {}
    for sl in SLIDERS:
        if sl.key not in DEADLY_KEYS:
            continue
        picks = [s for s in sl.steps if s.deadly]
        if picks:
            out[sl.key] = picks[-1].token
    return out


def bak_path(path: str) -> str:
    return path + ".se5edit.bak"


def ensure_save_backup(path: str) -> tuple[bool, str]:
    bak = bak_path(path)
    if os.path.isfile(bak):
        return True, f"Keeping existing backup {os.path.basename(bak)}"
    try:
        shutil.copy2(path, bak)
    except OSError as exc:
        return False, f"Backup failed: {exc}"
    return True, f"Wrote {os.path.basename(bak)}"


def apply_tokens(path: str, wanted: dict[str, int]) -> tuple[int, str]:
    """Patch *wanted* slider keys into *path*. Returns (n_changed, message)."""
    if not path or not os.path.isfile(path):
        return 0, "Save not found"
    with open(path, "rb") as fh:
        data = bytearray(fh.read())
    table = locate_table(bytes(data))
    if table is None:
        return 0, "No Custom Difficulty table in this slot (profile wrappers without a campaign blob are skipped)"
    changed: list[str] = []
    for key, token in wanted.items():
        sl = SLIDER_BY_KEY.get(key)
        if sl is None:
            continue
        off = table + sl.rel
        old = _u32(bytes(data), off)
        if old == token:
            continue
        data[off:off + 4] = struct.pack("<I", token)
        old_s = step_for_token(sl, old)
        new_s = step_for_token(sl, token)
        old_l = old_s.label if old_s else f"0x{old:08X}"
        new_l = new_s.label if new_s else f"0x{token:08X}"
        changed.append(f"{sl.label}: {old_l} → {new_l}")
    if not changed:
        return 0, "Already matches — nothing written"

    ok, bak_msg = ensure_save_backup(path)
    if not ok:
        return 0, bak_msg

    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".se5edit_", dir=directory)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except OSError as exc:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return 0, f"Write failed: {exc}"

    check = locate_table(bytes(data))
    if check != table:
        return len(changed), (
            f"Wrote {len(changed)} slider(s) but the table no longer locates "
            f"at the same offset. Restore {os.path.basename(bak_path(path))}. "
            + "; ".join(changed)
        )
    return len(changed), bak_msg + " · " + "; ".join(changed)


def restore_save(path: str) -> tuple[bool, str]:
    bak = bak_path(path)
    if not os.path.isfile(bak):
        return False, f"No backup {os.path.basename(bak)}"
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".se5edit_", dir=directory)
    try:
        shutil.copyfile(bak, tmp)
        os.replace(tmp, path)
    except OSError as exc:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return False, f"Restore failed: {exc}"
    return True, f"Restored {os.path.basename(path)} from {os.path.basename(bak)}"


def _profile_roots() -> list[str]:
    home = os.path.expanduser("~")
    local = os.environ.get("LOCALAPPDATA", "")
    return [
        os.path.join(
            home, ".steam/debian-installation/steamapps/compatdata",
            APP_ID, "pfx/drive_c/users/steamuser/AppData/Local/"
            "Sniper Elite 5/PC_ProfileSaves",
        ),
        os.path.join(
            home, ".steam/steam/steamapps/compatdata",
            APP_ID, "pfx/drive_c/users/steamuser/AppData/Local/"
            "Sniper Elite 5/PC_ProfileSaves",
        ),
        os.path.join(
            home, ".local/share/Steam/steamapps/compatdata",
            APP_ID, "pfx/drive_c/users/steamuser/AppData/Local/"
            "Sniper Elite 5/PC_ProfileSaves",
        ),
        os.path.join(local, "Sniper Elite 5", "PC_ProfileSaves") if local else "",
    ]


def find_profile_dir() -> str:
    for root in _profile_roots():
        if not root or not os.path.isdir(root):
            continue
        try:
            names = os.listdir(root)
        except OSError:
            continue
        # Prefer a Steam-id folder that actually has slot files.
        for name in names:
            sub = os.path.join(root, name)
            if not os.path.isdir(sub):
                continue
            if any(fn.startswith("slot") and fn.endswith(".sav")
                   for fn in os.listdir(sub)):
                return sub
        if any(fn.startswith("slot") and fn.endswith(".sav")
               for fn in names):
            return root
    return ""


def list_slots(profile_dir: str) -> list[SaveSlot]:
    if not profile_dir or not os.path.isdir(profile_dir):
        return []
    out: list[SaveSlot] = []
    try:
        names = os.listdir(profile_dir)
    except OSError:
        return []
    for name in names:
        if not name.startswith("slot") or not name.endswith(".sav"):
            continue
        path = os.path.join(profile_dir, name)
        try:
            st = os.stat(path)
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        table = locate_table(data)
        kind = "profile" if name.lower() in ("slot0.sav", "slot1.sav") else "campaign"
        # slot0 on this profile carries the live Custom Difficulty table.
        if name.lower() == "slot0.sav" and table is not None:
            kind = "profile"
        out.append(SaveSlot(
            path=path,
            name=name,
            mtime=st.st_mtime,
            kind=kind,
            mission=mission_label(data),
            table_off=table,
            tokens=read_tokens(data, table) if table is not None else {},
        ))
    out.sort(key=lambda s: s.mtime, reverse=True)
    return out
