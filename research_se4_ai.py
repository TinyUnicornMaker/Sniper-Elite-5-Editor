#!/usr/bin/env python3
"""Read-only SE4 vs SE5 AI dump. Does not write game files.

SE4 Misc/Common.asr block 306 = AXBT (sense names still ASCII).
SE4 block 309 = goal graph (Push BT).
SE5 misc/common.asr block 405 / 407 = same jobs, names stripped.
"""
from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

SE4_DEFAULT = Path(
    "/home/rapunzel/.steam/debian-installation/steamapps/common/"
    "Sniper Elite 4/Misc/Common.asr"
)
SE5_DEFAULT = Path(
    "/home/rapunzel/.steam/debian-installation/steamapps/common/"
    "Sniper Elite 5/misc/common.asr"
)

SENSE_MARKERS = (
    b"HearingScore",
    b"Hearing Score",
    b"HasVisualThreat",
    b"HadVisualThreatRecently",
    b"TimeSinceVisualThreat",
    b"TrackNoVisualThreatTime",
    b"LookAtAndShootWhenLOS",
    b"IfNoLineOfSightCloseFurther",
    b"Is Inside Goal Volume",
    b"Is Position In Field Of Fire",
    b"RangeCheckToCurrentThreat",
    b"SE3 Acquiring Timer",
)


def _zbb_block(raw: bytes, index: int) -> bytes:
    _, _, first_comp, _ = struct.unpack_from("<IIII", raw, 8)
    pos, comp = 24, first_comp
    for _ in range(index):
        pos += comp
        comp, _ = struct.unpack_from("<II", raw, pos)
        pos += 8
    return zlib.decompress(raw[pos : pos + comp], 12)


def _bt_paths(block: bytes) -> list[str]:
    out, pos = [], 0
    while True:
        p = block.find(b"BehaviourTrees\\", pos)
        if p < 0:
            break
        e = p
        while e < len(block) and 32 <= block[e] < 127:
            e += 1
        out.append(block[p:e].decode("ascii"))
        pos = p + 1
    return sorted(set(out))


def _goal_volume_ranges(block: bytes) -> list[tuple[int, float, str]]:
    """(?Range float sitting on Is Inside Goal Volume nodes)."""
    found = []
    pos = 0
    needle = b"Is Inside Goal Volume"
    while True:
        p = block.find(needle, pos)
        if p < 0:
            break
        # structured ?Range then 300/500 at +176 from the name
        if p + 180 <= len(block):
            val = struct.unpack_from("<f", block, p + 176)[0]
            nxt = ""
            wp = block.find(b"Waypoint Zone", p, p + 400)
            if wp >= 0:
                nxt = " +Waypoint Zone"
            if val == val and 1 <= val <= 2000:
                found.append((p, val, nxt))
        pos = p + 1
    return found


def dump_se4(path: Path) -> None:
    raw = path.read_bytes()
    b306 = _zbb_block(raw, 306)
    b309 = _zbb_block(raw, 309)
    print(f"SE4 {path}  size={len(raw)}")
    print(f"  blk 306 AXBT@{b306.find(b'AXBT')} AXBB@{b306.find(b'AXBB')}")
    print("  BehaviourTrees:")
    for p in _bt_paths(b306):
        print(f"    {p}")
    print("  Sense markers:")
    for m in SENSE_MARKERS:
        print(f"    {m.decode():36} x{b306.count(m)}")
    print("  Goal-volume ?Range:")
    for off, val, extra in _goal_volume_ranges(b306):
        print(f"    @{off}  {val:g} m{extra}")
    print("  Goal names (blk 309 around Push BT):")
    start = b309.find(b"Push BT")
    if start < 0:
        return
    i, end = max(0, start - 200), min(len(b309), start + 6000)
    while i < end:
        if 32 <= b309[i] < 127:
            j = i
            while j < end and 32 <= b309[j] < 127:
                j += 1
            s = b309[i:j].decode("ascii")
            if sum(c.isalpha() for c in s) >= 4 and "shader" not in s.lower():
                if not any(x in s for x in (".tga", "g_x", "DXBC", "RDEF")):
                    print(f"    {s}")
            i = j
        else:
            i += 1


def dump_se5_missing(path: Path) -> None:
    raw = path.read_bytes()
    # reuse editor helper
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gui.zbb_util import read_block

    _, _, b405 = read_block(raw, 405)
    _, _, b407 = read_block(raw, 407)
    print(f"\nSE5 {path}")
    print("  Sense markers leftover in 405/407:")
    for m in SENSE_MARKERS:
        print(f"    {m.decode():36} 405={b405.count(m)} 407={b407.count(m)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--se4", type=Path, default=SE4_DEFAULT)
    ap.add_argument("--se5", type=Path, default=SE5_DEFAULT)
    args = ap.parse_args()
    if args.se4.is_file():
        dump_se4(args.se4)
    else:
        print("SE4 Common.asr not found:", args.se4)
    if args.se5.is_file():
        dump_se5_missing(args.se5)
    else:
        print("SE5 common.asr not found:", args.se5)


if __name__ == "__main__":
    main()
