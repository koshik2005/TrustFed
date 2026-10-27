"""Hierarchical federated learning: hospitals -> regional hubs (SMPC) -> global server (optional HE)."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
import numpy as np
from . import nn, dp, secagg
from .metrics import accuracy, auc_score


@dataclass
class FLConfig:
    rounds: int = 40
    local_epochs: int = 1
    batch: int = 16
    lr: float = 0.1
    clip: float | None = None       # None -> non-private; else per-example clip norm C
    sigma: float = 0.0              # noise multiplier (DP-SGD)
    secagg: bool = False            # additive secret sharing inside each hub
    he: bool = False                # Paillier tier between hubs and global server
    he_bits: int = 1024
    hubs: list[list[int]] | None = None
    delta: float = 1e-5
    seed: int = 0


@dataclass
class FLResult:
    theta: np.ndarray
    history: list[dict] = field(default_factory=list)
    epsilon: float = float("inf")
    seconds: float = 0.0
    agg_seconds: float = 0.0


def default_hubs(K: int) -> list[list[int]]:
    """Split K hospitals into 2 regional hubs (East/West); one hub when K<4."""
    if K < 4:
        return [list(range(K))]
    cut = (K + 1) // 2
    return [list(range(cut)), list(range(cut, K))]


def eps_after(cfg: FLConfig, sizes, rounds_done: int) -> float:
    if cfg.clip is None or cfg.sigma <= 0:
        return float("inf")
    worst = 0.0
    for n in sizes:
        steps = max(1, round(cfg.local_epochs * n / cfg.batch)) * rounds_done
        worst = max(worst, dp.epsilon(min(1.0, cfg.batch / n), cfg.sigma, steps, cfg.delta))
    return worst


def calibrate_sigma(cfg: FLConfig, sizes, target_eps: float, lo: float = 0.3, hi: float = 3.5) -> float:
    """Smallest noise multiplier whose worst-hospital epsilon after all rounds is <= target_eps (bisection)."""
    from dataclasses import replace
    def eps(sig): return eps_after(replace(cfg, sigma=sig), sizes, cfg.rounds)
    if eps(lo) <= target_eps: return lo
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if eps(mid) > target_eps else (lo, mid)
    return hi


def aggregate(vectors: list[np.ndarray], cfg: FLConfig, hubs, rng, pk=None):
    """Return the *sum* of the hospitals' vectors computed with the configured protocol."""
    if not cfg.secagg:
        return np.sum(vectors, axis=0)
    ring_totals = [secagg.secure_sum([vectors[i] for i in hub], rng) for hub in hubs]
    if cfg.he:
        cts = [secagg.he_encrypt_vector(pk, rt) for rt in ring_totals]      # hubs encrypt
        agg = secagg.he_sum_ciphertexts(pk, cts)                            # server: ciphertexts only
        ints = secagg.he_decrypt_vector(pk, agg, len(ring_totals[0]), len(hubs))  # key authority
        return ints.astype(np.float64) / secagg.SCALE
    with np.errstate(over="ignore"):
        total = sum(ring_totals[1:], start=ring_totals[0])
    return secagg.decode(total)


def run_federated(hospitals, X_test, y_test, cfg: FLConfig, theta0=None, on_round=None) -> FLResult:
    """hospitals: list of (X_i, y_i). Test set is only used for monitoring."""
    rng = np.random.default_rng(cfg.seed)
    srng = np.random.default_rng(cfg.seed + 10_000)   # separate stream for secret shares
    K = len(hospitals)
    hubs = cfg.hubs or default_hubs(K)
    theta = nn.init_params(rng) if theta0 is None else theta0.copy()
    sizes = [len(y) for _, y in hospitals]
    pk = secagg.Paillier(cfg.he_bits) if (cfg.secagg and cfg.he) else None
    res = FLResult(theta)
    t0 = time.time()
    for r in range(1, cfg.rounds + 1):
        vecs = []
        for (X, y), n in zip(hospitals, sizes):
            steps = max(1, round(cfg.local_epochs * n / cfg.batch))
            th = dp.local_train(theta, X, y, steps, cfg.batch, cfg.lr, cfg.clip, cfg.sigma, rng)
            vecs.append(np.concatenate([n * th, [float(n)]]))
        ta = time.time()
        total = aggregate(vecs, cfg, hubs, srng, pk)
        res.agg_seconds += time.time() - ta
        theta = total[:-1] / total[-1]
        pr = nn.predict_proba(theta, X_test)
        res.history.append({
            "round": r,
            "accuracy": accuracy(y_test, pr.argmax(1)),
            "loss": float(nn.losses(theta, X_test, y_test).mean()),
            "epsilon": eps_after(cfg, sizes, r) if (on_round or r in (1, cfg.rounds) or r % 5 == 0) else None,
        })
        if on_round is not None:
            on_round(r, res.history[-1], theta)
    res.theta = theta
    res.epsilon = eps_after(cfg, sizes, cfg.rounds)
    res.seconds = time.time() - t0
    return res


def run_centralized(X, y, X_test, y_test, cfg: FLConfig, n_hospitals: int) -> FLResult:
    """Pooled non-private upper bound with the same total number of SGD steps per sample."""
    rng = np.random.default_rng(cfg.seed)
    theta = nn.init_params(rng)
    steps = max(1, round(cfg.local_epochs * len(y) / cfg.batch)) * cfg.rounds
    theta = dp.local_train(theta, X, y, steps, cfg.batch, cfg.lr, None, 0.0, rng)
    return FLResult(theta)


def run_local_only(hospitals, cfg: FLConfig) -> list[np.ndarray]:
    """Each hospital trains alone for rounds*epochs (no collaboration)."""
    rng = np.random.default_rng(cfg.seed)
    out = []
    for X, y in hospitals:
        th = nn.init_params(rng)
        steps = max(1, round(cfg.local_epochs * len(y) / cfg.batch)) * cfg.rounds
        out.append(dp.local_train(th, X, y, steps, cfg.batch, cfg.lr, None, 0.0, rng))
    return out
