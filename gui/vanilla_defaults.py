"""Permanent vanilla default values for comparison in the property editor.

Values are snapshotted from the game's ``common.asr`` + ``common.asr.asrpatch``
(preferring ``.bak`` copies so later editor saves do not become the baseline)
and shipped as ``gui/vanilla_defaults.json``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

_DEFAULTS: dict[str, dict[str, float]] | None = None
_PATH: Path | None = None


def _candidate_paths() -> list[Path]:
    here = Path(__file__).resolve().parent
    paths = [
        here / "vanilla_defaults.json",
        here.parent / "data" / "vanilla_defaults.json",
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        root = Path(meipass)
        paths.insert(0, root / "gui" / "vanilla_defaults.json")
        paths.insert(1, root / "data" / "vanilla_defaults.json")
    return paths


def defaults_path() -> Optional[Path]:
    global _PATH
    if _PATH is not None:
        return _PATH
    for p in _candidate_paths():
        if p.is_file():
            _PATH = p
            return p
    return None


def load_defaults() -> dict[str, dict[str, float]]:
    """Load the shipped vanilla table (cached). Empty dict if missing."""
    global _DEFAULTS
    if _DEFAULTS is not None:
        return _DEFAULTS
    path = defaults_path()
    if path is None:
        _DEFAULTS = {}
        return _DEFAULTS
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            _DEFAULTS = {}
            return _DEFAULTS
        # Drop metadata key if present
        data.pop("_meta", None)
        _DEFAULTS = data
    except (OSError, json.JSONDecodeError):
        _DEFAULTS = {}
    return _DEFAULTS


def get_default(entity_name: str, prop_name: str) -> Optional[float]:
    """Vanilla value for *entity_name* / *prop_name*, or None if unknown."""
    table = load_defaults()
    ent = table.get(entity_name)
    if not ent:
        return None
    val = ent.get(prop_name)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def has_defaults_for(entity_name: str) -> bool:
    return bool(load_defaults().get(entity_name))


def reset_entity_to_defaults(asr_file, entity_name: str) -> int:
    """Write shipped vanilla values into the in-memory ASR body.

    Only touches **editable patch** properties that have an entry in
    ``vanilla_defaults.json``. Does **not** save to disk — the caller
    must write the asrpatch and the game must be restarted for values
    to take effect in-game.

    Returns the number of properties successfully written.
    """
    entity = asr_file.entities.get(entity_name)
    if entity is None:
        return 0
    n = 0
    for prop in list(entity.properties):
        if not prop.name or not getattr(prop, "editable", True):
            continue
        van = get_default(entity_name, prop.name)
        if van is None:
            continue
        if prop.is_float:
            if asr_file.set_float(entity_name, prop.name, float(van)):
                n += 1
        elif prop.is_int:
            if asr_file.set_int(entity_name, prop.name, int(round(van))):
                n += 1
    return n
