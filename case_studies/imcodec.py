"""Teaching codec helpers for Lesson 5 (`05_graph_image_compression.ipynb`).

Low-level bitstream plumbing lives here so the notebook can show the transform,
quantizer and symbol construction without drowning in byte handling.

Two codecs share every component except the transform:

    DCT codec  : separable orthonormal DCT-II on each 8x8 block
    EA-GFT codec: eigenbasis of a per-block weighted grid Laplacian, with the
                  weak-edge mask transmitted as side information

Both produce a real byte string that `decode()` turns back into pixels using
nothing but those bytes and the conventions documented in `CONTAINER`.

Conventions that encoder and decoder must agree on
--------------------------------------------------
* Blocks are raster-ordered, top-left origin, image zero-padded (edge-replicated)
  to a multiple of the block size; the true H, W are in the header.
* Samples are level-shifted by -128 before transforming, +128 after.
* Coefficients are scanned in zigzag order (DCT) or ascending-eigenvalue order
  (GFT); both are fixed and derived identically at each end.
* Eigenvector signs are canonicalised (see `canonical_signs`), and a block with
  no weak edges uses the analytic DCT basis rather than an eigensolver, which
  removes the only badly degenerate case.
"""

from __future__ import annotations

import struct
import zlib
import numpy as np

__all__ = [
    "dct_matrix", "dct2", "idct2", "zigzag_order", "JPEG_LUMA_Q",
    "BitWriter", "BitReader", "canonical_huffman", "build_huffman",
    "encode_symbols", "decode_symbols",
    "block_edges", "weak_edge_mask", "grid_laplacian", "canonical_signs",
    "block_basis", "gft_order",
    "pad_to_blocks", "unpad", "blockify", "unblockify",
    "encode", "decode", "CONTAINER",
    "mse", "psnr", "bpp", "compression_ratio",
]

MAGIC = b"GTC1"
CONTAINER = """
offset  type    field
0       4s      magic 'GTC1'
4       B       version (=1)
5       B       method  0 = DCT, 1 = EA-GFT
6       H       height  (true, before padding)
8       H       width
10      B       block size B
11      B       predictor 0 = none, 1 = causal DC prediction
12      f       quantizer step delta   (uniform) ; 0 => JPEG table mode
16      f       weak edge weight w_e   (GFT only, else 0)
20      B       edge threshold T       (GFT only, else 0)
21      B       mask mode 0 = none, 1 = raw bits, 2 = zlib(raw bits)
22      I       mask byte length
26      I       DC huffman table byte length
30      I       AC huffman table byte length
34      I       coefficient payload byte length
38      ...     mask bytes | DC table | AC table | payload
"""
_HDR = "<4sBBHHBBffBBIIII"
_HDR_SIZE = struct.calcsize(_HDR)


# =========================================================================
# 1. DCT
# =========================================================================
def dct_matrix(B: int) -> np.ndarray:
    """Orthonormal DCT-II matrix C with C[k, n] = a_k cos(pi (2n+1) k / 2B)."""
    n = np.arange(B)
    k = np.arange(B)[:, None]
    C = np.cos(np.pi * (2 * n + 1) * k / (2 * B))
    C *= np.sqrt(2.0 / B)
    C[0] /= np.sqrt(2.0)
    return C


def dct2(X, C):
    """F = C X C^T  (separable 2-D DCT of one block)."""
    return C @ X @ C.T


def idct2(F, C):
    """X = C^T F C."""
    return C.T @ F @ C


def zigzag_order(B: int) -> np.ndarray:
    """Flat indices of a BxB block in zigzag (low to high frequency) order."""
    idx = []
    for s in range(2 * B - 1):
        band = [(u, s - u) for u in range(B) if 0 <= s - u < B]
        idx.extend(band if s % 2 else band[::-1])
    return np.array([u * B + v for u, v in idx], dtype=np.int64)


# Annex K luminance quantisation table from ITU-T T.81 (informative example).
JPEG_LUMA_Q = np.array([
    [16, 11, 10, 16, 24, 40, 51, 61], [12, 12, 14, 19, 26, 58, 60, 55],
    [14, 13, 16, 24, 40, 57, 69, 56], [14, 17, 22, 29, 51, 87, 80, 62],
    [18, 22, 37, 56, 68, 109, 103, 77], [24, 35, 55, 64, 81, 104, 113, 92],
    [49, 64, 78, 87, 103, 121, 120, 101], [72, 92, 95, 98, 112, 100, 103, 99],
], dtype=np.float64)


# =========================================================================
# 2. bit-level IO
# =========================================================================
class BitWriter:
    """MSB-first bit accumulator."""

    def __init__(self):
        self._bits = bytearray()

    def bit(self, b):
        self._bits.append(1 if b else 0)

    def bits(self, value, n):
        for i in range(n - 1, -1, -1):
            self._bits.append((value >> i) & 1)

    def write_code(self, code_str):
        for ch in code_str:
            self._bits.append(1 if ch == "1" else 0)

    def __len__(self):
        return len(self._bits)

    def tobytes(self):
        pad = (-len(self._bits)) % 8
        arr = np.frombuffer(bytes(self._bits) + b"\x00" * pad, dtype=np.uint8)
        return np.packbits(arr).tobytes()


class BitReader:
    """MSB-first bit source over a byte string."""

    def __init__(self, data: bytes):
        self._bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
        self._i = 0

    def bit(self):
        b = int(self._bits[self._i])
        self._i += 1
        return b

    def bits(self, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | self.bit()
        return v

    @property
    def pos(self):
        return self._i


# =========================================================================
# 3. canonical Huffman
# =========================================================================
def _huffman_depths(freq):
    """Unrestricted Huffman code lengths via the usual two-queue merge."""
    import heapq
    syms = [s for s, f in freq.items() if f > 0]
    if not syms:
        return {}
    if len(syms) == 1:
        return {syms[0]: 1}
    heap = [(freq[s], i, [s]) for i, s in enumerate(syms)]
    heapq.heapify(heap)
    depth = {s: 0 for s in syms}
    cnt = len(heap)
    while len(heap) > 1:
        f1, _, g1 = heapq.heappop(heap)
        f2, _, g2 = heapq.heappop(heap)
        for s in g1 + g2:
            depth[s] += 1
        heapq.heappush(heap, (f1 + f2, cnt, g1 + g2))
        cnt += 1
    return depth


def _limit_lengths(counts, max_len=16):
    """ITU-T T.81 Figure K.3: shorten over-long codes while PRESERVING the Kraft
    equality, so the canonical assignment stays a valid prefix code. Ad-hoc
    'move one symbol up a level' rebalancing does not preserve it and silently
    produces a table whose decoder desynchronises."""
    counts = list(counts) + [0] * (33 - len(counts))
    i = 32
    while i > max_len:
        if counts[i] > 0:
            j = i - 1
            while counts[j] == 0:
                j -= 1
            counts[i] -= 2
            counts[i - 1] += 1
            counts[j + 1] += 2
            counts[j] -= 1
        else:
            i -= 1
    while len(counts) > max_len + 1 and counts[-1] == 0:
        counts.pop()
    return counts


def _code_lengths(freq, max_len=16):
    """Length-limited Huffman lengths. Symbols are assigned to lengths by
    decreasing frequency, which is optimal once the length multiset is fixed."""
    depth = _huffman_depths(freq)
    if not depth:
        return {}
    counts = [0] * 33
    for s in depth:
        counts[depth[s]] += 1
    counts = _limit_lengths(counts, max_len)
    order = sorted(depth, key=lambda s: (-freq[s], s))
    out, i = {}, 0
    for ln in range(1, len(counts)):
        for _ in range(counts[ln]):
            out[order[i]] = ln
            i += 1
    assert i == len(order), "length assignment lost symbols"
    kraft = sum(2.0 ** -l for l in out.values())
    assert abs(kraft - 1.0) < 1e-9, f"invalid prefix code, Kraft sum = {kraft}"
    return out


def canonical_huffman(depth):
    """Canonical code assignment: sort by (length, symbol), assign increasing codes."""
    if not depth:
        return {}, {}
    order = sorted(depth, key=lambda s: (depth[s], s))
    codes, code, prev_len = {}, 0, None
    for s in order:
        ln = depth[s]
        if prev_len is None:
            code = 0
        else:
            code = (code + 1) << (ln - prev_len)
        codes[s] = format(code, "0{}b".format(ln))
        prev_len = ln
    decode_map = {v: k for k, v in codes.items()}
    return codes, decode_map


def build_huffman(freq):
    """freq -> (codes, table_bytes). Table is 16 length-counts then symbols,
    exactly as a JPEG DHT segment, so the decoder can rebuild canonically."""
    depth = _code_lengths(freq)
    codes, _ = canonical_huffman(depth)
    counts = [0] * 16
    for s in depth:
        counts[depth[s] - 1] += 1
    order = sorted(depth, key=lambda s: (depth[s], s))
    table = bytes(counts) + bytes(order)
    return codes, table


def _codes_from_table(table: bytes):
    counts = list(table[:16])
    syms = list(table[16:])
    depth, i = {}, 0
    for ln in range(1, 17):
        for _ in range(counts[ln - 1]):
            depth[syms[i]] = ln
            i += 1
    _, decode_map = canonical_huffman(depth)
    return decode_map


def encode_symbols(writer, symbols, codes):
    for s in symbols:
        writer.write_code(codes[s])


def decode_symbols(reader, decode_map, n):
    out, buf = [], ""
    while len(out) < n:
        buf += "1" if reader.bit() else "0"
        if buf in decode_map:
            out.append(decode_map[buf])
            buf = ""
    return out


# =========================================================================
# 4. graphs on a block
# =========================================================================
def block_edges(B: int):
    """The 2B(B-1) four-neighbour grid edges, in a FIXED documented order:
    all horizontal edges in raster order, then all vertical edges."""
    edges = []
    for r in range(B):                       # horizontal: (r,c)-(r,c+1)
        for c in range(B - 1):
            edges.append((r * B + c, r * B + c + 1))
    for r in range(B - 1):                   # vertical: (r,c)-(r+1,c)
        for c in range(B):
            edges.append((r * B + c, (r + 1) * B + c))
    return edges


def weak_edge_mask(block, edges, threshold):
    """1 where |difference| across a grid edge exceeds `threshold` (an image edge)."""
    x = np.asarray(block, float).ravel()
    return np.array([abs(x[i] - x[j]) > threshold for i, j in edges], dtype=np.uint8)


def grid_laplacian(mask, edges, n, w_strong=1.0, w_weak=0.1):
    W = np.zeros((n, n))
    for (i, j), m in zip(edges, mask):
        w = w_weak if m else w_strong
        W[i, j] = W[j, i] = w
    return np.diag(W.sum(1)) - W


def canonical_signs(U):
    """Fix each eigenvector's sign so encoder and decoder agree: make the entry
    of largest magnitude positive, breaking ties by the lowest index."""
    U = np.array(U, float)
    for k in range(U.shape[1]):
        col = U[:, k]
        idx = int(np.argmax(np.abs(col)))
        if col[idx] < 0:
            U[:, k] = -col
    return U


def block_basis(mask, edges, B, w_weak=0.1, C=None):
    """Orthonormal basis for one block, plus the scan order.

    With no weak edges the grid Laplacian's eigenvalues are heavily repeated, so
    an eigensolver's choice within each eigenspace is arbitrary. In that case we
    use the ANALYTIC separable DCT basis -- which is a valid eigenbasis of that
    Laplacian -- making the no-edge case both deterministic and exactly the DCT.
    """
    n = B * B
    if not mask.any():
        C = dct_matrix(B) if C is None else C
        U = np.kron(C, C).T                 # columns = vec of DCT basis images
        return U, zigzag_order(B)
    L = grid_laplacian(mask, edges, n, 1.0, w_weak)
    lam, U = np.linalg.eigh(L)
    order = np.argsort(lam, kind="stable")
    return canonical_signs(U[:, order]), np.arange(n)


def gft_order(n):
    return np.arange(n)


# =========================================================================
# 5. blocking
# =========================================================================
def pad_to_blocks(img, B):
    H, W = img.shape
    ph, pw = (-H) % B, (-W) % B
    if ph or pw:
        img = np.pad(img, ((0, ph), (0, pw)), mode="edge")
    return img, H, W


def unpad(img, H, W):
    return img[:H, :W]


def blockify(img, B):
    H, W = img.shape
    return (img.reshape(H // B, B, W // B, B).swapaxes(1, 2)
               .reshape(-1, B, B))


def unblockify(blocks, H, W, B):
    return (blocks.reshape(H // B, W // B, B, B).swapaxes(1, 2)
                  .reshape(H, W))


# =========================================================================
# 6. symbol construction (JPEG-style run/size categories)
# =========================================================================
def _category(v):
    v = int(abs(v))
    return 0 if v == 0 else int(v).bit_length()


def _amp_bits(v, s):
    return int(v) if v > 0 else int(v) + (1 << s) - 1


def _amp_value(bits, s):
    if s == 0:
        return 0
    return bits if bits >= (1 << (s - 1)) else bits - (1 << s) + 1


def _block_symbols(q, dc_prev):
    """q: quantised coefficients already in scan order. Returns
    (dc_sym, dc_extra, ac_syms, ac_extra, dc_value) JPEG-style."""
    diff = int(q[0]) - dc_prev
    s = _category(diff)
    dc = (s, (_amp_bits(diff, s), s) if s else None)
    ac_syms, ac_extra, run = [], [], 0
    for v in q[1:]:
        v = int(v)
        if v == 0:
            run += 1
            continue
        while run > 15:
            ac_syms.append(0xF0)             # ZRL
            ac_extra.append(None)
            run -= 16
        sz = _category(v)
        ac_syms.append((run << 4) | sz)
        ac_extra.append((_amp_bits(v, sz), sz))
        run = 0
    # T.81 F.1.2.2.1: the end-of-block symbol is emitted only when the scan ends
    # in zeros. If the LAST coefficient is nonzero the decoder's index reaches the
    # block size on its own; sending an EOB there would leave a symbol unread and
    # desynchronise every following block.
    if int(q[-1]) == 0:
        ac_syms.append(0x00)                 # EOB
        ac_extra.append(None)
    return dc, ac_syms, ac_extra, int(q[0])


# =========================================================================
# 7. prediction
# =========================================================================
def predict_block(recon, br, bc, B):
    """Causal DC predictor from already-reconstructed neighbours.

    Uses the mean of the reconstructed row above and column to the left of this
    block. At the image border the missing side is dropped; with neither
    available the prediction is the mid-level 128. The decoder reproduces this
    exactly because it only reads pixels it has already reconstructed.
    """
    r0, c0 = br * B, bc * B
    vals = []
    if r0 > 0:
        vals.append(recon[r0 - 1, c0:c0 + B])
    if c0 > 0:
        vals.append(recon[r0:r0 + B, c0 - 1])
    if not vals:
        return np.full((B, B), 128.0)
    return np.full((B, B), float(np.concatenate(vals).mean()))


# =========================================================================
# 8. the codecs
# =========================================================================
def encode(img, method="dct", B=8, delta=16.0, predictor=0,
           threshold=25, w_weak=0.1, mask_mode=2, qtable=None):
    """Encode a uint8 grayscale image into bytes. `method` in {'dct','gft'}."""
    img = np.asarray(img)
    assert img.dtype == np.uint8 and img.ndim == 2
    padded, H, W = pad_to_blocks(img.astype(np.float64), B)
    Hp, Wp = padded.shape
    nbr, nbc = Hp // B, Wp // B
    C = dct_matrix(B)
    edges = block_edges(B)
    use_table = qtable is not None
    Q = np.asarray(qtable, float).ravel() if use_table else None

    recon = np.zeros_like(padded)
    masks, dc_syms, dc_extra, ac_syms, ac_extra = [], [], [], [], []
    dc_prev = 0
    zz = zigzag_order(B)

    for br in range(nbr):
        for bc in range(nbc):
            blk = padded[br * B:(br + 1) * B, bc * B:(bc + 1) * B]
            if predictor:
                p = predict_block(recon, br, bc, B)
                src = blk - p
            else:
                p = None
                src = blk - 128.0

            if method == "dct":
                F = dct2(src, C).ravel()[zz]
                m = None
            else:
                # Book section 4.3.2 detects image edges on the signal actually
                # being transformed -- the residual when prediction is on. With a
                # DC predictor the offset is constant, so the differences (and
                # hence the mask) are identical either way; with a richer
                # predictor they would not be.
                m = weak_edge_mask(src, edges, threshold)
                masks.append(m)
                U, order = block_basis(m, edges, B, w_weak, C)
                F = (U.T @ src.ravel())[order]

            step = Q[zz] if use_table else delta
            q = np.round(F / step).astype(np.int64)
            d, a_s, a_e, dc_prev = _block_symbols(q, dc_prev)
            dc_syms.append(d[0]); dc_extra.append(d[1])
            ac_syms.extend(a_s); ac_extra.extend(a_e)

            # mirror the decoder so prediction references match exactly
            Fr = q.astype(float) * step
            if method == "dct":
                flat = np.zeros(B * B); flat[zz] = Fr
                rec = idct2(flat.reshape(B, B), C)
            else:
                flat = np.zeros(B * B); flat[order] = Fr
                rec = (U @ flat).reshape(B, B)
            rec = rec + (p if predictor else 128.0)
            recon[br * B:(br + 1) * B, bc * B:(bc + 1) * B] = np.clip(
                np.round(rec), 0, 255)

    dc_codes, dc_table = build_huffman(_freq(dc_syms))
    ac_codes, ac_table = build_huffman(_freq(ac_syms))
    bw = BitWriter()
    ai = 0
    for i, s in enumerate(dc_syms):
        bw.write_code(dc_codes[s])
        if dc_extra[i]:
            bw.bits(*dc_extra[i])
        k_pos = 1
        while k_pos < B * B:
            sym = ac_syms[ai]
            bw.write_code(ac_codes[sym])
            if ac_extra[ai]:
                bw.bits(*ac_extra[ai])
            ai += 1
            if sym == 0x00:
                break
            k_pos += 16 if sym == 0xF0 else (sym >> 4) + 1
    payload = bw.tobytes()

    if method == "gft" and masks:
        raw = np.packbits(np.concatenate(masks)).tobytes()
        if mask_mode == 2:
            comp = zlib.compress(raw, 9)
            mask_bytes, mm = (comp, 2) if len(comp) < len(raw) else (raw, 1)
        else:
            mask_bytes, mm = raw, 1
    else:
        mask_bytes, mm = b"", 0

    head = struct.pack(_HDR, MAGIC, 1, 0 if method == "dct" else 1, H, W, B,
                       predictor, 0.0 if use_table else float(delta),
                       float(w_weak) if method == "gft" else 0.0,
                       int(threshold) if method == "gft" else 0, mm,
                       len(mask_bytes), len(dc_table), len(ac_table), len(payload))
    return head + mask_bytes + dc_table + ac_table + payload


def _freq(syms):
    f = {}
    for s in syms:
        f[s] = f.get(s, 0) + 1
    return f


def decode(data: bytes, qtable=None):
    """Reconstruct the image from encoded bytes alone."""
    (magic, ver, meth, H, W, B, predictor, delta, w_weak, threshold,
     mm, mlen, dclen, aclen, plen) = struct.unpack(_HDR, data[:_HDR_SIZE])
    assert magic == MAGIC and ver == 1, "not a GTC1 stream"
    o = _HDR_SIZE
    mask_bytes = data[o:o + mlen]; o += mlen
    dc_table = data[o:o + dclen]; o += dclen
    ac_table = data[o:o + aclen]; o += aclen
    payload = data[o:o + plen]

    dc_map = _codes_from_table(dc_table)
    ac_map = _codes_from_table(ac_table)
    C = dct_matrix(B)
    edges = block_edges(B)
    zz = zigzag_order(B)
    n = B * B
    Hp, Wp = H + (-H) % B, W + (-W) % B
    nbr, nbc = Hp // B, Wp // B
    use_table = (delta == 0.0)
    Q = np.asarray(qtable, float).ravel() if use_table else None

    if meth == 1 and mlen:
        raw = zlib.decompress(mask_bytes) if mm == 2 else mask_bytes
        allbits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8))
        nE = len(edges)
        masks = [allbits[k * nE:(k + 1) * nE] for k in range(nbr * nbc)]
    else:
        masks = None

    br_ = BitReader(payload)
    recon = np.zeros((Hp, Wp))
    dc_prev = 0

    def read_sym(dmap):
        buf = ""
        while True:
            buf += "1" if br_.bit() else "0"
            if buf in dmap:
                return dmap[buf]

    for bi in range(nbr * nbc):
        s = read_sym(dc_map)
        diff = _amp_value(br_.bits(s), s) if s else 0
        dc_prev += diff
        q = np.zeros(n, dtype=np.int64)
        q[0] = dc_prev
        k = 1
        while k < n:
            sym = read_sym(ac_map)
            if sym == 0x00:
                break
            run, sz = sym >> 4, sym & 0xF
            if sym == 0xF0:
                k += 16
                continue
            k += run
            q[k] = _amp_value(br_.bits(sz), sz)
            k += 1

        row, col = divmod(bi, nbc)
        step = Q[zz] if use_table else delta
        Fr = q.astype(float) * step
        if meth == 0:
            flat = np.zeros(n); flat[zz] = Fr
            rec = idct2(flat.reshape(B, B), C)
        else:
            U, order = block_basis(masks[bi].astype(np.uint8), edges, B, w_weak, C)
            flat = np.zeros(n); flat[order] = Fr
            rec = (U @ flat).reshape(B, B)
        if predictor:
            rec = rec + predict_block(recon, row, col, B)
        else:
            rec = rec + 128.0
        recon[row * B:(row + 1) * B, col * B:(col + 1) * B] = np.clip(
            np.round(rec), 0, 255)

    return unpad(recon, H, W).astype(np.uint8)


# =========================================================================
# 9. metrics
# =========================================================================
def mse(a, b):
    return float(np.mean((np.asarray(a, float) - np.asarray(b, float)) ** 2))


def psnr(a, b, peak=255.0):
    m = mse(a, b)
    return float("inf") if m == 0 else float(10 * np.log10(peak ** 2 / m))


def bpp(nbytes, H, W):
    return 8.0 * nbytes / (H * W)


def compression_ratio(nbytes, H, W):
    return (H * W) / nbytes
