"""Helpers for reading/rewriting a single AsuraZbb block in common.asr."""
from __future__ import annotations

import struct
import zlib
from typing import Callable


def navigate_to_block(raw: bytes, block_number: int) -> tuple[int, int]:
    """Return ``(data_offset, compressed_size)`` for a ZBB block."""
    extra = raw[8:24]
    _, _, first_comp, _ = struct.unpack("<IIII", extra)
    pos = 24
    comp_size = first_comp
    for _ in range(block_number):
        pos += comp_size
        if pos + 8 > len(raw):
            raise ValueError(f"Block {block_number} not found (file too short)")
        comp_size, _ = struct.unpack("<II", raw[pos : pos + 8])
        pos += 8
    return pos, comp_size


def read_block(raw: bytes, block_number: int) -> tuple[int, int, bytes]:
    """Return ``(offset, compressed_size, decompressed_bytes)``."""
    pos, comp = navigate_to_block(raw, block_number)
    data = zlib.decompress(raw[pos : pos + comp], 12)
    return pos, comp, data


def compress_block(data: bytes, target_comp: int | None = None) -> bytes:
    """Compress a ZBB payload with wbits=12.

    When *target_comp* is set the result is padded with trailing zeros so
    it is exactly that long. Later blocks then keep their original file
    offsets. Growing past *target_comp* is refused — shifting block 406+
    has crashed the game on load.
    """

    def _one(level: int) -> bytes:
        co = zlib.compressobj(level, zlib.DEFLATED, 12)
        out = co.compress(data) + co.flush()
        if zlib.decompress(out, 12) != data:
            raise RuntimeError("Compression round-trip verification failed")
        return out

    out = _one(6)
    if target_comp is None:
        return out
    if len(out) > target_comp:
        for level in (9, 8, 7, 5, 4, 3, 2, 1):
            cand = _one(level)
            if len(cand) <= target_comp:
                out = cand
                break
        else:
            raise RuntimeError(
                f"Compressed block is {len(out)} bytes; original slot is "
                f"{target_comp}. Refusing to shift later blocks."
            )
    if len(out) < target_comp:
        out = out + b"\x00" * (target_comp - len(out))
    return out


def rewrite_block(
    raw: bytes,
    block_number: int,
    mutator: Callable[[bytearray], None],
) -> bytes:
    """Decompress *block_number*, run *mutator*, recompress, return new file.

    The compressed payload is padded back to the original slot size so
    every later block stays at the same file offset. Headers and the
    file length are left unchanged.
    """
    block_pos, block_comp, original = read_block(raw, block_number)
    block_data = bytearray(original)
    mutator(block_data)

    if len(block_data) != len(original):
        raise RuntimeError(
            f"Block {block_number} uncompressed size changed "
            f"({len(original)} → {len(block_data)}); refusing to write."
        )

    recompressed = compress_block(bytes(block_data), target_comp=block_comp)
    if len(recompressed) != block_comp:
        raise RuntimeError(
            f"Padded compressed size {len(recompressed)} != slot {block_comp}"
        )

    out = bytearray(raw)
    out[block_pos : block_pos + block_comp] = recompressed
    return bytes(out)


def validate_zbb(raw: bytes, check_blocks: int = 8) -> str | None:
    """Return an error string if the ZBB index cannot walk *check_blocks*."""
    if raw[:8] != b"AsuraZbb":
        return f"Not AsuraZbb (got {raw[:8]!r})"
    try:
        n = min(check_blocks, 408)
        for i in range(n):
            read_block(raw, i)
        # Also prove the last known AI/glint blocks are still reachable
        if check_blocks >= 8:
            read_block(raw, 405)
            read_block(raw, 406)
    except Exception as exc:
        return str(exc)
    return None
