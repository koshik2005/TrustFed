"""Secure aggregation: additive secret sharing over Z_{2^64} (fixed-point) + Paillier (HE) tier.

Tier 1 (hospital -> regional hub): every hospital splits its update into m random additive shares
(one per hospital of the hub). A hub only ever sees per-member partial sums, each of which is
uniformly random; only the total is revealed.
Tier 2 (hub -> global): optional Paillier encryption with SIMD-style packing, so the aggregation
server only handles ciphertexts; a separate key authority decrypts the *sum* only.
"""
from __future__ import annotations
import math
import secrets
import numpy as np

SCALE = float(1 << 24)             # fixed-point precision 2^-24
_U64 = np.uint64


def encode(v: np.ndarray) -> np.ndarray:
    return np.rint(v * SCALE).astype(np.int64).astype(_U64)


def decode(u: np.ndarray) -> np.ndarray:
    return u.astype(np.int64).astype(np.float64) / SCALE


def share(v_enc: np.ndarray, m: int, rng: np.random.Generator):
    """Split an encoded vector into m additive shares mod 2^64."""
    shares = [rng.integers(0, 2 ** 64, size=v_enc.shape, dtype=_U64) for _ in range(m - 1)]
    last = v_enc.copy()
    with np.errstate(over="ignore"):
        for s in shares:
            last = last - s
    return shares + [last]


def secure_sum(vectors: list[np.ndarray], rng) -> np.ndarray:
    """Secure sum of float vectors held by the m parties of one hub. Returns the exact (fixed-point) sum.
    Returned value is what the hub learns: the *aggregate* only."""
    m = len(vectors)
    all_shares = [share(encode(v), m, rng) for v in vectors]        # all_shares[i][j]: i -> member j
    with np.errstate(over="ignore"):
        partials = [sum((all_shares[i][j] for i in range(m)), start=np.zeros_like(all_shares[0][0]))
                    for j in range(m)]                               # member j's partial sum
        total = sum(partials, start=np.zeros_like(partials[0]))
    return total                                                     # encoded ring element


# ───────────────────────────── Paillier (pure Python) ─────────────────────────────
def _is_probable_prime(n: int, k: int = 40) -> bool:
    if n < 2: return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29):
        if n % p == 0: return n == p
    d, s = n - 1, 0
    while d % 2 == 0: d //= 2; s += 1
    for _ in range(k):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1): continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1: break
        else:
            return False
    return True


def _gen_prime(bits: int) -> int:
    while True:
        c = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if _is_probable_prime(c): return c


class Paillier:
    """Textbook Paillier with g = n+1. Key authority holds (lam, mu); everybody else gets n."""
    def __init__(self, bits: int = 1024):
        while True:
            p, q = _gen_prime(bits // 2), _gen_prime(bits // 2)
            if p != q and math.gcd(p * q, (p - 1) * (q - 1)) == 1:
                break
        self.n, self.n2 = p * q, (p * q) ** 2
        self.lam = math.lcm(p - 1, q - 1)
        self.mu = pow(self.lam, -1, self.n)
        self.bits = bits

    def encrypt(self, m: int) -> int:
        r = secrets.randbelow(self.n - 1) + 1
        return ((1 + (m % self.n) * self.n) * pow(r, self.n, self.n2)) % self.n2

    def add(self, c1: int, c2: int) -> int:
        return (c1 * c2) % self.n2

    def decrypt(self, c: int) -> int:
        x = pow(c, self.lam, self.n2)
        return (((x - 1) // self.n) * self.mu) % self.n


SLOT_BITS, OFFSET = 52, 1 << 46      # each int64 value is offset to be non-negative and packed in 52-bit slots


def he_encrypt_vector(pk: Paillier, ring_vec: np.ndarray) -> list[int]:
    """Encrypt a ring-encoded (uint64 == int64) vector using packed slots."""
    vals = [int(v) + OFFSET for v in ring_vec.astype(np.int64)]
    per = (pk.bits - 8) // SLOT_BITS
    cts = []
    for i in range(0, len(vals), per):
        chunk = vals[i:i + per]
        packed = 0
        for j, v in enumerate(chunk):
            packed |= v << (SLOT_BITS * j)
        cts.append(pk.encrypt(packed))
    return cts


def he_sum_ciphertexts(pk: Paillier, vectors: list[list[int]]) -> list[int]:
    out = vectors[0]
    for v in vectors[1:]:
        out = [pk.add(a, b) for a, b in zip(out, v)]
    return out


def he_decrypt_vector(sk: Paillier, cts: list[int], length: int, n_summands: int) -> np.ndarray:
    per = (sk.bits - 8) // SLOT_BITS
    mask = (1 << SLOT_BITS) - 1
    vals = []
    for c in cts:
        packed = sk.decrypt(c)
        for j in range(per):
            vals.append((packed >> (SLOT_BITS * j)) & mask)
    vals = vals[:length]
    return np.array([v - n_summands * OFFSET for v in vals], dtype=np.int64)
