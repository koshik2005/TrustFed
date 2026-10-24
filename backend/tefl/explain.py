r"""Exact Shapley values (baseline/interventional SHAP) for the 13-feature model.

phi_j = sum_{S subset F\{j}} |S|!(d-|S|-1)!/d! [ f(x_{S u j}, b_{rest}) - f(x_S, b_{rest}) ],
with f = logit margin (z1 - z0) and b = reference vector (population mean after standardisation = 0).
All 2^13 coalitions are evaluated, so values are exact and satisfy sum(phi) = f(x) - f(b).
"""
from __future__ import annotations
import math
import numpy as np
from . import nn

D = 13
_MASKS = ((np.arange(1 << D)[:, None] >> np.arange(D)) & 1).astype(bool)      # (8192, 13)
_POP = _MASKS.sum(1)
_W = np.array([math.factorial(s) * math.factorial(D - s - 1) / math.factorial(D) for s in range(D)])
_IDX = [np.where(~_MASKS[:, j])[0] for j in range(D)]


def shap_values(theta, x, baseline=None):
    """Exact Shapley values for one standardised instance x (shape (13,))."""
    b = np.zeros(D) if baseline is None else baseline
    Z = np.where(_MASKS, x[None, :], b[None, :])
    f = nn.logit_margin(theta, Z)
    phi = np.zeros(D)
    for j in range(D):
        S = _IDX[j]
        phi[j] = np.sum(_W[_POP[S]] * (f[S | (1 << j)] - f[S]))
    return phi, float(f[-1] - f[0])          # phi, f(x)-f(b)


def shap_matrix(theta, X, baseline=None):
    return np.array([shap_values(theta, x, baseline)[0] for x in X])
