"""In-place bit patches inside an existing zlib/deflate payload.

Rebellion's inflater rejects a Python-recompressed ZBB block even when
the uncompressed bytes are almost unchanged. The SE3 acquiring timer
literals can be rewritten in the original stream if the new IEEE bytes
keep the same Huffman code lengths.
"""
from __future__ import annotations

import struct
import zlib
from collections import Counter
from dataclasses import dataclass

LEN_BASE = [
    3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51,
    59, 67, 83, 99, 115, 131, 163, 195, 227, 258,
]
LEN_EXTRA = [
    0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4,
    4, 5, 5, 5, 5, 0,
]
DIST_BASE = [
    1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385,
    513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577,
]
DIST_EXTRA = [
    0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10,
    10, 11, 11, 12, 12, 13, 13,
]
_CLEN_ORDER = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]


class _Bits:
    def __init__(self, buf: bytes | bytearray, start: int, end: int):
        self.buf = buf
        self.pos = start
        self.end = end
        self.bit = 0

    def tell(self) -> tuple[int, int]:
        return self.pos, self.bit

    def get(self, n: int) -> int:
        v = 0
        got = 0
        while got < n:
            if self.pos >= self.end:
                raise EOFError("deflate truncated")
            b = self.buf[self.pos]
            take = min(8 - self.bit, n - got)
            v |= ((b >> self.bit) & ((1 << take) - 1)) << got
            self.bit += take
            got += take
            if self.bit == 8:
                self.bit = 0
                self.pos += 1
        return v

    def byte_align(self) -> None:
        if self.bit:
            self.bit = 0
            self.pos += 1


def _build_huffman(lengths: list[int]):
    counts = [0] * 16
    for length in lengths:
        if length:
            counts[length] += 1
    next_code = [0] * 16
    code = 0
    for nbits in range(1, 16):
        code = (code + counts[nbits - 1]) << 1
        next_code[nbits] = code
    decode: dict[tuple[int, int], int] = {}
    encode: dict[int, tuple[int, int]] = {}
    for sym, length in enumerate(lengths):
        if not length:
            continue
        c = next_code[length]
        next_code[length] += 1
        rev = 0
        cc = c
        for _ in range(length):
            rev = (rev << 1) | (cc & 1)
            cc >>= 1
        decode[(rev, length)] = sym
        encode[sym] = (rev, length)
    maxlen = max((length for length in lengths if length), default=0)
    return decode, encode, maxlen


def _decode_sym(bits: _Bits, decode: dict, maxlen: int) -> int:
    code = 0
    for length in range(1, maxlen + 1):
        code |= bits.get(1) << (length - 1)
        hit = decode.get((code, length))
        if hit is not None:
            return hit
    raise ValueError("invalid Huffman symbol")


@dataclass(frozen=True)
class LiteralSite:
    out_off: int
    byte_pos: int
    bit: int
    nbits: int
    code: int
    symbol: int
    encode: dict[int, tuple[int, int]]


def _inflate_sites(comp: bytes, wanted: set[int]) -> list[LiteralSite]:
    bits = _Bits(comp, 2, len(comp) - 4)
    out = bytearray()
    sites: list[LiteralSite] = []
    while True:
        bfinal = bits.get(1)
        btype = bits.get(2)
        if btype == 0:
            bits.byte_align()
            length = bits.get(16)
            nlen = bits.get(16)
            if (length ^ 0xFFFF) != nlen:
                raise ValueError("corrupt stored block")
            src = bits.pos
            for i in range(length):
                o = len(out)
                val = comp[src + i]
                if o in wanted:
                    sites.append(LiteralSite(o, src + i, 0, 8, val, val, {}))
                out.append(val)
            bits.pos += length
            bits.bit = 0
        elif btype in (1, 2):
            if btype == 1:
                lit_len = [8] * 144 + [9] * 112 + [7] * 24 + [8] * 8
                dist_len = [5] * 32
            else:
                nlit = bits.get(5) + 257
                ndist = bits.get(5) + 1
                nclen = bits.get(4) + 4
                clens = [0] * 19
                for i in range(nclen):
                    clens[_CLEN_ORDER[i]] = bits.get(3)
                cl_dec, _, cl_max = _build_huffman(clens)
                lens: list[int] = []
                while len(lens) < nlit + ndist:
                    sym = _decode_sym(bits, cl_dec, cl_max)
                    if sym < 16:
                        lens.append(sym)
                    elif sym == 16:
                        lens.extend([lens[-1]] * (bits.get(2) + 3))
                    elif sym == 17:
                        lens.extend([0] * (bits.get(3) + 3))
                    else:
                        lens.extend([0] * (bits.get(7) + 11))
                lit_len = lens[:nlit]
                dist_len = lens[nlit:]
            lit_dec, lit_enc, lit_max = _build_huffman(lit_len)
            dist_dec, _, dist_max = _build_huffman(dist_len)
            while True:
                start = bits.tell()
                sym = _decode_sym(bits, lit_dec, lit_max)
                if sym < 256:
                    o = len(out)
                    if o in wanted:
                        code, nbits = lit_enc[sym]
                        sites.append(LiteralSite(
                            o, start[0], start[1], nbits, code, sym, lit_enc
                        ))
                    out.append(sym)
                elif sym == 256:
                    break
                else:
                    length = LEN_BASE[sym - 257]
                    extra = LEN_EXTRA[sym - 257]
                    if extra:
                        length += bits.get(extra)
                    dcode = _decode_sym(bits, dist_dec, dist_max)
                    dist = DIST_BASE[dcode]
                    dextra = DIST_EXTRA[dcode]
                    if dextra:
                        dist += bits.get(dextra)
                    for _ in range(length):
                        out.append(out[-dist])
        else:
            raise ValueError(f"bad BTYPE {btype}")
        if bfinal:
            break
    return sites


def _write_bits(buf: bytearray, byte_pos: int, bit: int, nbits: int, value: int) -> None:
    for i in range(nbits):
        if (value >> i) & 1:
            buf[byte_pos] |= 1 << bit
        else:
            buf[byte_pos] &= ~(1 << bit)
        bit += 1
        if bit == 8:
            bit = 0
            byte_pos += 1


def _compatible_bytes(encode: dict[int, tuple[int, int]], lengths: list[int]) -> list[list[int]]:
    by_len: dict[int, list[int]] = {}
    for sym, (_code, nbits) in encode.items():
        if 0 <= sym <= 255:
            by_len.setdefault(nbits, []).append(sym)
    return [sorted(by_len.get(nbits, [])) for nbits in lengths]


def smallest_compatible_float(
    encode: dict[int, tuple[int, int]],
    lengths: list[int],
    min_value: float = 0.001,
    max_value: float = 0.361,
) -> float | None:
    """Smallest positive float whose IEEE bytes fit *lengths* in *encode*."""
    allowed = _compatible_bytes(encode, lengths)
    if any(not col for col in allowed):
        return None
    best: float | None = None
    for b3 in allowed[3]:
        for b2 in allowed[2]:
            for b1 in allowed[1]:
                for b0 in allowed[0]:
                    val = struct.unpack("<f", bytes((b0, b1, b2, b3)))[0]
                    if val != val or val < min_value or val > max_value:
                        continue
                    if best is None or val < best:
                        best = val
    return best


def nearest_compatible_float(
    encode: dict[int, tuple[int, int]],
    lengths: list[int],
    target: float,
    min_value: float = 0.001,
    max_value: float = 2.0,
) -> float | None:
    packed = struct.pack("<f", target)
    if all(
        packed[i] in encode and encode[packed[i]][1] == lengths[i]
        for i in range(4)
    ):
        return target
    allowed = _compatible_bytes(encode, lengths)
    if any(not col for col in allowed):
        return None
    best: tuple[float, float] | None = None
    for b3 in allowed[3]:
        for b2 in allowed[2]:
            for b1 in allowed[1]:
                for b0 in allowed[0]:
                    val = struct.unpack("<f", bytes((b0, b1, b2, b3)))[0]
                    if val != val or val < min_value or val > max_value:
                        continue
                    dist = abs(val - target)
                    if best is None or dist < best[0]:
                        best = (dist, val)
    return None if best is None else best[1]


def patch_wrapped_floats(
    comp: bytes,
    uncompressed: bytes,
    sites_out: list[int],
    new_value: float,
) -> tuple[bytes, float, int]:
    """Patch Huffman literals at *sites_out* (start of each 4-byte float).

    Match-copied copies of those floats update automatically. Returns
    ``(new_compressed, actual_value, literal_sites_patched)``.
    """
    wanted = set()
    for off in sites_out:
        wanted.update(range(off, off + 4))
    sites = _inflate_sites(comp, wanted)
    by_off = {s.out_off: s for s in sites}
    literal_starts = [off for off in sites_out if off in by_off]
    if not literal_starts:
        raise RuntimeError("timer floats are not Huffman literals in this stream")

    first = [by_off[literal_starts[0] + i] for i in range(4)]
    encode = first[0].encode
    lengths = [s.nbits for s in first]
    for off in literal_starts[1:]:
        other = [by_off[off + i] for i in range(4)]
        if [s.nbits for s in other] != lengths:
            raise RuntimeError("timer copies use different Huffman lengths")

    actual = nearest_compatible_float(encode, lengths, new_value)
    if actual is None:
        raise RuntimeError("no Huffman-compatible float in the allowed range")
    new_bytes = struct.pack("<f", actual)

    buf = bytearray(comp)
    patched = 0
    for off in literal_starts:
        for i in range(4):
            site = by_off[off + i]
            new_sym = new_bytes[i]
            if new_sym not in encode or encode[new_sym][1] != site.nbits:
                raise RuntimeError("compatible float failed a site check")
            new_code, nbits = encode[new_sym]
            _write_bits(buf, site.byte_pos, site.bit, nbits, new_code)
            patched += 1

    # Match-copied copies of these floats (including other 0.362 slots
    # that share the same literals) update automatically. Adler32 must
    # come from the real inflated payload, not a guessed byte list.
    inflated = zlib.decompress(bytes(buf[2:-4]), -12)
    if len(inflated) != len(uncompressed):
        raise RuntimeError("in-place deflate patch changed uncompressed size")
    for off in sites_out:
        if inflated[off : off + 4] != new_bytes:
            raise RuntimeError("patched literals did not inflate to the new timer")
    adler = zlib.adler32(inflated) & 0xFFFFFFFF
    struct.pack_into(">I", buf, len(buf) - 4, adler)
    check = zlib.decompress(bytes(buf), 12)
    if check != inflated:
        raise RuntimeError("in-place deflate patch failed zlib round-trip")
    return bytes(buf), actual, patched
