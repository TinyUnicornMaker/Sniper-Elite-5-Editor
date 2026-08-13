"""Research helper: Survival end-of-wave enemy outline (“detective vision”).

Static RE (see ENEMY_STATS.md section 5b) found no menu flag and no
common.asr knob. This script only helps the next experiments:

* Dump the Custom Difficulty trailer (``0x3FA777FE``) from a ``.sav``
* Label mapped vs unmapped dwords for A/B token flips
* Print known binary anchors (entity class / AMP outline vars)

Does **not** write game files. Quit the game before any future save patch.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

TABLE_SIG = 0x3FA777FE
TABLE_SIZE = 96

# Relative offset → label. Combat slots proven by prior +1 save diffs.
MAPPED: dict[int, str] = {
    0: "signature",
    4: "const? (+04)",
    8: "const? (+08)",
    12: "preset/mode hash? (varies profile vs campaign)",
    16: "Player Resilience (mapped)",
    20: "Enemy Resilience (mapped)",
    24: "UNMAPPED — sniping/tactical candidate",
    28: "UNMAPPED — sniping/tactical candidate",
    32: "UNMAPPED — sniping/tactical candidate",
    36: "Enemy Aggression (mapped)",
    40: "Enemy Accuracy (mapped)",
    44: "UNMAPPED",
    48: "Enemy Skill (mapped)",
    52: "separator",
    56: "Enemy Perceptiveness (mapped)",
    60: "Enemy Responsiveness (mapped)",
    64: "Health Regeneration (mapped)",
    68: "UNMAPPED — HUD/Radar/Tagging candidate",
    72: "UNMAPPED — HUD/Radar/Tagging candidate",
    76: "UNMAPPED — HUD/Radar/Tagging candidate",
    80: "Enemy Sniper Skill (mapped)",
    84: "UNMAPPED",
    88: "UNMAPPED",
    92: "separator",
}

BINARY_ANCHORS = (
    "SE_ENTITYCLASS_SURVIVALGAMEMANAGER  VA 0x140d8bf18",
    "Factory 0x140966100  vtable 0x140d8cbd0  object 0x48 (parent-1 at -0x80)",
    "Wave-stage helper 0x140966d30 (cmp 1/4, sentinel 0x3E7) — no cmp 5 in cluster",
    "Asura_XRay_Skin_Outline_* (shared render; no .debug lea)",
    "Full cvar dump: NO Survival outline var (AMP PenetrationShowOutline is MP only)",
    "Console: ListVars / SearchVars / Input.CommandConsoleUsingTextEntry @ 0x140321014",
    "Try in-game ~ or Ctrl+Tab (SE3 bind). Game.IsDevMode / Cheat.* exist.",
)


def find_tables(data: bytes) -> list[int]:
    sig = struct.pack("<I", TABLE_SIG)
    out: list[int] = []
    start = 0
    while True:
        i = data.find(sig, start)
        if i < 0:
            break
        if i + TABLE_SIZE <= len(data):
            out.append(i)
        start = i + 1
    return out


def dump_table(data: bytes, off: int) -> None:
    print(f"\nTable @ file offset {off} (0x{off:X}), {TABLE_SIZE} bytes")
    print(f"{'rel':>4}  {'token':>12}  label")
    print("-" * 72)
    for rel in range(0, TABLE_SIZE, 4):
        tok = struct.unpack_from("<I", data, off + rel)[0]
        label = MAPPED.get(rel, "UNMAPPED")
        mark = ""
        if "UNMAPPED" in label:
            mark = "  <--- A/B candidate"
        print(f"+{rel:02d}  0x{tok:08X}  {label}{mark}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "saves",
        nargs="*",
        type=Path,
        help="One or more slotN.sav (profile or campaign). "
             "Default: print anchors only.",
    )
    ap.add_argument(
        "--diff",
        nargs=2,
        type=Path,
        metavar=("A", "B"),
        help="Compare two saves: print only dwords that differ in the table.",
    )
    args = ap.parse_args(argv)

    print("Survival wave-end outline — research dump")
    print("Binary anchors:")
    for a in BINARY_ANCHORS:
        print(f"  - {a}")
    print(
        "\nNo common.asr / asrpatch / GraphicsOptions knob found.\n"
        "Next: in-game SearchVars outline|highlight|surviv  "
        "OR live-patch remaining-count threshold in SurvivalGameManager."
    )

    paths: list[Path] = list(args.saves)
    if args.diff:
        paths = list(args.diff)

    if not paths:
        return 0

    if args.diff:
        a, b = args.diff
        da, db = a.read_bytes(), b.read_bytes()
        ta, tb = find_tables(da), find_tables(db)
        if not ta or not tb:
            print("Missing difficulty table in one or both saves", file=sys.stderr)
            return 1
        oa, ob = ta[0], tb[0]
        print(f"\nDiff {a.name}@{oa} vs {b.name}@{ob}")
        any_diff = False
        for rel in range(0, TABLE_SIZE, 4):
            va = struct.unpack_from("<I", da, oa + rel)[0]
            vb = struct.unpack_from("<I", db, ob + rel)[0]
            if va != vb:
                any_diff = True
                print(
                    f"  +{rel:02d}  0x{va:08X} -> 0x{vb:08X}  "
                    f"({MAPPED.get(rel, 'UNMAPPED')})"
                )
        if not any_diff:
            print("  (no table dword differences)")
        return 0

    for p in paths:
        data = p.read_bytes()
        offs = find_tables(data)
        print(f"\n=== {p} size={len(data)} tables={offs} ===")
        if not offs:
            print("  No 0x3FA777FE table found")
            continue
        for off in offs:
            dump_table(data, off)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
