"""Fairness audit: subgroup performance + SHAP-importance divergence with a permutation test."""
from __future__ import annotations
import numpy as np
from scipy.spatial.distance import jensenshannon
from .data import FEATURES

MIN_N = 15            # subgroups smaller than this are reported but never flagged
ACC_GAP_FLAG = 0.10   # flag if subgroup accuracy deviates from overall by more than this


def age_group(age):
    return np.where(age < 55, "Age <55", np.where(age < 65, "Age 55-64", "Age >=65"))


def _importance(S):
    v = np.abs(S).mean(0)
    return v / v.sum()


def _div(S, mask):
    if mask.sum() < 2 or (~mask).sum() < 2:
        return 0.0
    return float(jensenshannon(_importance(S[mask]), _importance(S[~mask]), base=2))


def audit(y, pred, shap_abs, attrs: dict, rng, n_perm=500):
    """attrs: {attribute: array of subgroup labels}. shap_abs: (n,13) SHAP matrix.
    Returns dict with per-subgroup rows, flags and overall score."""
    y, pred = np.asarray(y), np.asarray(pred)
    overall = float((y == pred).mean())
    rows, flags = [], []
    for attr, lab in attrs.items():
        lab = np.asarray(lab)
        groups = sorted(set(lab))
        null = {g: [] for g in groups}
        for _ in range(n_perm):
            perm = rng.permutation(lab)
            for g in groups:
                null[g].append(_div(shap_abs, perm == g))
        for g in groups:
            m = lab == g
            n = int(m.sum())
            acc = float((y[m] == pred[m]).mean())
            pos, neg = m & (y == 1), m & (y == 0)
            tpr = float((pred[pos] == 1).mean()) if pos.any() else float("nan")
            fpr = float((pred[neg] == 1).mean()) if neg.any() else float("nan")
            d = _div(shap_abs, m)
            p = float((np.sum(np.array(null[g]) >= d) + 1) / (n_perm + 1))
            imp = _importance(shap_abs[m]) if n >= 2 else np.zeros(len(FEATURES))
            top = [FEATURES[i] for i in np.argsort(-imp)[:3]]
            row = {"attribute": attr, "subgroup": str(g), "n": n, "accuracy": acc,
                   "tpr": tpr, "fpr": fpr, "pos_rate": float((pred[m] == 1).mean()),
                   "acc_gap": acc - overall, "shap_divergence": d, "shap_p": p, "top_features": top}
            rows.append(row)
            if n >= MIN_N:
                if abs(acc - overall) > ACC_GAP_FLAG:
                    flags.append({"severity": "high" if abs(acc - overall) > 0.2 else "medium",
                                  "subgroup": f"{attr}: {g}", "divergence": abs(acc - overall),
                                  "message": f"Accuracy {acc:.1%} differs from overall {overall:.1%} (n={n})."})
                if p < 0.05:
                    flags.append({"severity": "medium", "subgroup": f"{attr}: {g}", "divergence": d,
                                  "message": f"SHAP importance profile differs from the rest "
                                             f"(JS={d:.3f}, permutation p={p:.3f}, n={n})."})
    elig = [abs(r["acc_gap"]) for r in rows if r["n"] >= MIN_N]
    return {"overall_accuracy": overall, "score": float(1 - max(elig)) if elig else 1.0,
            "subgroups": rows, "flags": flags}
