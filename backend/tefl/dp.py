"""Differential privacy: DP-SGD step + RDP accountant for the Poisson-sampled Gaussian mechanism.

Accountant: Renyi-DP of the sampled Gaussian mechanism at integer orders (Mironov, Talwar & Zhang 2019),
composed over T steps and converted to (eps, delta) with the tight conversion of Balle et al. (2020).
"""
from __future__ import annotations
import math
import numpy as np
from .nn import per_example_grads

ORDERS = list(range(2, 257))


def _logsumexp(a):
    m = max(a)
    return m + math.log(sum(math.exp(x - m) for x in a))


def rdp_sgm(q: float, sigma: float, alpha: int) -> float:
    """RDP epsilon (per step) of the sampled Gaussian mechanism at integer order alpha."""
    if sigma <= 0:
        return math.inf
    if q >= 1.0:
        return alpha / (2 * sigma ** 2)
    if q <= 0:
        return 0.0
    terms = []
    for k in range(alpha + 1):
        lc = math.lgamma(alpha + 1) - math.lgamma(k + 1) - math.lgamma(alpha - k + 1)
        terms.append(lc + (alpha - k) * math.log1p(-q) + k * math.log(q)
                     + (k * k - k) / (2 * sigma ** 2))
    return _logsumexp(terms) / (alpha - 1)


def epsilon(q: float, sigma: float, steps: int, delta: float = 1e-5) -> float:
    """(eps, delta)-DP epsilon after `steps` compositions."""
    if sigma <= 0 or steps <= 0:
        return math.inf if sigma <= 0 else 0.0
    best = math.inf
    for a in ORDERS:
        r = steps * rdp_sgm(q, sigma, a)
        e = r + math.log1p(-1.0 / a) - (math.log(delta) + math.log(a)) / (a - 1)
        best = min(best, e)
    return max(best, 0.0)


def local_train(theta, X, y, steps, batch, lr, clip, sigma, rng):
    """`steps` SGD steps with Poisson sampling (rate q = batch/n).

    clip=None -> ordinary (non-private) minibatch SGD.
    clip=C, sigma>=0 -> DP-SGD: per-example clipping to norm C, Gaussian noise N(0, (sigma*C)^2),
    normalised by the expected batch size (as in Opacus).
    """
    theta = theta.copy()
    n = len(y)
    q = min(1.0, batch / n)
    for _ in range(steps):
        mask = rng.random(n) < q
        if not mask.any():
            continue
        G = per_example_grads(theta, X[mask], y[mask])
        if clip is None:
            g = G.sum(0) / mask.sum()
        else:
            norms = np.linalg.norm(G, axis=1)
            G = G * np.minimum(1.0, clip / np.maximum(norms, 1e-12))[:, None]
            g = (G.sum(0) + rng.normal(0.0, sigma * clip, G.shape[1])) / (q * n)
        theta -= lr * g
    return theta
