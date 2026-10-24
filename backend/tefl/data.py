"""Data loading, hospital partitioning (non-IID) and standardisation.

Real data : UCI Cleveland heart-disease (processed.cleveland.data, 303 rows -> 297 complete).
Fallback  : a *synthetic* cohort with the same schema (clearly flagged everywhere it is used).
"""
from __future__ import annotations
import os
import urllib.request
from dataclasses import dataclass
import numpy as np

FEATURES = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
            "thalach", "exang", "oldpeak", "slope", "ca", "thal"]
UCI_URL = ("https://archive.ics.uci.edu/ml/machine-learning-databases/"
           "heart-disease/processed.cleveland.data")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


@dataclass
class Cohort:
    X: np.ndarray          # (n, 13) raw feature values
    y: np.ndarray          # (n,) 0/1
    name: str              # "cleveland" | "synthetic"

    @property
    def age(self): return self.X[:, 0]
    @property
    def sex(self): return self.X[:, 1]


def load_cleveland(path: str | None = None, download: bool = True) -> Cohort:
    """Load the real UCI Cleveland file (cached in backend/data/)."""
    path = path or os.path.join(DATA_DIR, "processed.cleveland.data")
    if not os.path.exists(path):
        if not download:
            raise FileNotFoundError(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(UCI_URL, path)
    rows = []
    with open(path) as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) != 14 or "?" in parts:
                continue                      # 6 rows have missing ca/thal
            rows.append([float(p) for p in parts])
    a = np.array(rows)
    return Cohort(a[:, :13], (a[:, 13] > 0).astype(int), "cleveland")


def make_synthetic(n: int = 297, seed: int = 0) -> Cohort:
    """Synthetic stand-in with Cleveland-like, class-conditional marginals.

    NOT real patient data. Marginals are rough approximations of published
    descriptive statistics, used only when the real file is unavailable.
    """
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.46).astype(int)
    X = np.zeros((n, 13))
    def pick(vals, p0, p1):
        return np.array([rng.choice(vals, p=(p1 if yi else p0)) for yi in y], float)
    X[:, 0] = np.clip(np.where(y, rng.normal(56.6, 8, n), rng.normal(52.6, 9.5, n)), 29, 77).round()
    X[:, 1] = np.where(y, rng.random(n) < .82, rng.random(n) < .56).astype(float)
    X[:, 2] = pick([1, 2, 3, 4], [.10, .25, .40, .25], [.04, .06, .12, .78])
    X[:, 3] = np.clip(np.where(y, rng.normal(134, 19, n), rng.normal(129, 16, n)), 94, 200).round()
    X[:, 4] = np.clip(np.where(y, rng.normal(251, 49, n), rng.normal(243, 53, n)), 126, 564).round()
    X[:, 5] = np.where(y, rng.random(n) < .16, rng.random(n) < .14).astype(float)
    X[:, 6] = pick([0, 1, 2], [.55, .01, .44], [.40, .02, .58])
    th = np.where(y, rng.normal(139, 22, n), rng.normal(158, 19, n)) - 0.6 * (X[:, 0] - 54)
    X[:, 7] = np.clip(th, 71, 202).round()
    X[:, 8] = np.where(y, rng.random(n) < .55, rng.random(n) < .14).astype(float)
    X[:, 9] = np.clip(np.where(y, rng.gamma(1.6, 1.0, n), rng.gamma(0.9, 0.65, n)), 0, 6.2).round(1)
    X[:, 10] = pick([1, 2, 3], [.60, .32, .08], [.25, .64, .11])
    X[:, 11] = pick([0, 1, 2, 3], [.78, .14, .06, .02], [.33, .30, .22, .15])
    X[:, 12] = pick([3, 6, 7], [.80, .04, .16], [.27, .07, .66])
    return Cohort(X, y, "synthetic")


def load_cohort(source: str = "auto", seed: int = 0) -> Cohort:
    if source == "synthetic":
        return make_synthetic(seed=seed)
    if source == "cleveland":
        return load_cleveland()
    try:                                        # auto
        return load_cleveland()
    except Exception:
        return make_synthetic(seed=seed)


class Standardizer:
    """Global normalisation constants (agreed publicly before training)."""
    def fit(self, X):
        self.mu = X.mean(0)
        self.sd = X.std(0)
        self.sd[self.sd == 0] = 1.0
        return self
    def transform(self, X):
        return (X - self.mu) / self.sd


class HospitalAssigner:
    """Assigns patients to K hospitals with label skew (Dirichlet alpha) and
    age skew (strength `skew`). alpha=None -> IID. The same assigner is used for
    train and test patients so each site has a site-specific local test split."""
    def __init__(self, K: int, alpha: float | None, skew: float, age_mu: float,
                 age_sd: float, rng: np.random.Generator):
        self.K, self.skew, self.age_mu, self.age_sd = K, skew, age_mu, age_sd
        if alpha is None:
            self.pi = np.full((K, 2), 1.0 / K)
        else:                                   # P(hospital | class)
            self.pi = rng.dirichlet([alpha] * K, size=2).T
        self.s = np.linspace(-1, 1, K)

    def assign(self, y, age, rng):
        z = (age - self.age_mu) / self.age_sd
        logit = np.log(self.pi[:, y].T + 1e-12) + self.skew * np.outer(z, self.s)
        logit -= logit.max(1, keepdims=True)
        p = np.exp(logit); p /= p.sum(1, keepdims=True)
        u = rng.random(len(y))[:, None]
        return (p.cumsum(1) < u).sum(1).clip(0, self.K - 1)


def partition_train(y, age, K, alpha, skew, rng, min_per_class=5, tries=2000):
    """Return (assigner, hospital_ids) with every hospital holding >= min_per_class
    samples of each class (needed for stable local training)."""
    for _ in range(tries):
        asg = HospitalAssigner(K, alpha, skew, age.mean(), age.std(), rng)
        h = asg.assign(y, age, rng)
        ok = all(((h == k) & (y == c)).sum() >= min_per_class for k in range(K) for c in (0, 1))
        if ok:
            return asg, h
    raise RuntimeError("could not build a valid non-IID partition; relax alpha/min_per_class")
