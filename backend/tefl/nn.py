"""Tiny MLP (13-32-16-2) in numpy with per-example gradients (needed by DP-SGD)."""
from __future__ import annotations
import numpy as np

SHAPES = [(13, 32), (32,), (32, 16), (16,), (16, 2), (2,)]
SIZES = [int(np.prod(s)) for s in SHAPES]
N_PARAMS = sum(SIZES)                                   # 1010


def init_params(rng, d_in=13):
    parts = []
    dims = [(d_in, 32), (32, 16), (16, 2)]
    for a, b in dims:
        parts.append((rng.standard_normal((a, b)) * np.sqrt(2.0 / a)).ravel())
        parts.append(np.zeros(b))
    return np.concatenate(parts)


def unpack(theta):
    out, i = [], 0
    for shp, sz in zip(SHAPES, SIZES):
        out.append(theta[i:i + sz].reshape(shp)); i += sz
    return out


def forward(theta, X):
    W1, b1, W2, b2, W3, b3 = unpack(theta)
    z1 = X @ W1 + b1; a1 = np.maximum(z1, 0)
    z2 = a1 @ W2 + b2; a2 = np.maximum(z2, 0)
    z3 = a2 @ W3 + b3
    return z3, (X, z1, a1, z2, a2)


def softmax(z):
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def predict_proba(theta, X):
    return softmax(forward(theta, X)[0])


def logit_margin(theta, X):
    z = forward(theta, X)[0]
    return z[:, 1] - z[:, 0]


def losses(theta, X, y):
    p = predict_proba(theta, X)
    return -np.log(np.clip(p[np.arange(len(y)), y], 1e-12, None))


def per_example_grads(theta, X, y):
    """Returns (B, N_PARAMS) matrix of per-example gradients of the CE loss."""
    W1, b1, W2, b2, W3, b3 = unpack(theta)
    z3, (x, z1, a1, z2, a2) = forward(theta, X)
    B = len(y)
    d3 = softmax(z3); d3[np.arange(B), y] -= 1.0
    d2 = (d3 @ W3.T) * (z2 > 0)
    d1 = (d2 @ W2.T) * (z1 > 0)
    g = [np.einsum("bi,bj->bij", x, d1).reshape(B, -1), d1,
         np.einsum("bi,bj->bij", a1, d2).reshape(B, -1), d2,
         np.einsum("bi,bj->bij", a2, d3).reshape(B, -1), d3]
    return np.concatenate(g, axis=1)
