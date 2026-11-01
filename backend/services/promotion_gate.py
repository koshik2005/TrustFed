"""Model Promotion Gate: Statistical Verification Engine for Model Upgrades.

Enforces three mandatory gating criteria before a candidate model can be promoted:
1. Macro-F1 Improvement: The LOWER bound of the bootstrap 95% CI must be strictly above zero (CI_lower > 0).
   Tiny, statistically insignificant gains (where CI_lower <= 0) are rejected.
2. No Per-Disease Regression: No individual disease class may suffer a recall/F1 drop exceeding tolerance.
3. No Fairness Degradation: Demographic disparity across sensitive groups (e.g. sex) must not worsen.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


def compute_class_metrics(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Computes per-class precision, recall, and F1-score."""
    precisions = np.zeros(num_classes, dtype=np.float64)
    recalls = np.zeros(num_classes, dtype=np.float64)
    f1s = np.zeros(num_classes, dtype=np.float64)

    for c in range(num_classes):
        tp = np.sum((y_pred == c) & (y_true == c))
        fp = np.sum((y_pred == c) & (y_true != c))
        fn = np.sum((y_pred != c) & (y_true == c))

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        precisions[c] = prec
        recalls[c] = rec
        f1s[c] = f1

    return precisions, recalls, f1s


def compute_macro_f1(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> float:
    _, _, f1s = compute_class_metrics(y_true, y_pred, num_classes)
    return float(np.mean(f1s))


def compute_fairness_disparity(y_true: np.ndarray, y_pred: np.ndarray, sensitive_attr: np.ndarray) -> float:
    """Computes equal opportunity / recall disparity across binary sensitive groups (e.g. 0 vs 1)."""
    groups = np.unique(sensitive_attr)
    if len(groups) < 2:
        return 0.0

    accs = []
    for g in groups:
        mask = (sensitive_attr == g)
        if np.sum(mask) > 0:
            acc = float(np.mean(y_true[mask] == y_pred[mask]))
            accs.append(acc)

    if len(accs) >= 2:
        return float(abs(accs[0] - accs[1]))
    return 0.0


def evaluate_promotion_gate(
    candidate_preds: np.ndarray,
    baseline_preds: np.ndarray,
    ground_truth: np.ndarray,
    sensitive_attr: Optional[np.ndarray] = None,
    disease_names: Optional[List[str]] = None,
    n_bootstrap: int = 1000,
    per_disease_tolerance: float = 0.02,
    fairness_tolerance: float = 0.01,
    random_seed: int = 42
) -> Dict[str, Any]:
    """Evaluates whether a candidate model passes the promotion gate against a baseline model.
    
    Returns a structured decision dictionary with verification details.
    """
    y_true = np.asarray(ground_truth, dtype=np.int32)
    y_cand = np.asarray(candidate_preds, dtype=np.int32)
    y_base = np.asarray(baseline_preds, dtype=np.int32)

    assert len(y_true) == len(y_cand) == len(y_base), "Dataset length mismatch between predictions and ground truth"
    n_samples = len(y_true)

    # Determine number of classes
    num_classes = max(int(np.max(y_true)), int(np.max(y_cand)), int(np.max(y_base))) + 1
    names = disease_names or [f"disease_{i}" for i in range(num_classes)]

    # 1. Point metrics
    macro_f1_base = compute_macro_f1(y_true, y_base, num_classes)
    macro_f1_cand = compute_macro_f1(y_true, y_cand, num_classes)
    delta_macro_f1 = macro_f1_cand - macro_f1_base

    _, rec_base, f1_base = compute_class_metrics(y_true, y_base, num_classes)
    _, rec_cand, f1_cand = compute_class_metrics(y_true, y_cand, num_classes)

    # 2. Bootstrap 95% Confidence Interval for Macro-F1 Improvement
    rng = np.random.default_rng(random_seed)
    bootstrap_deltas = np.zeros(n_bootstrap, dtype=np.float64)

    for b in range(n_bootstrap):
        boot_idx = rng.choice(n_samples, size=n_samples, replace=True)
        boot_true = y_true[boot_idx]
        boot_cand = y_cand[boot_idx]
        boot_base = y_base[boot_idx]

        f1_c = compute_macro_f1(boot_true, boot_cand, num_classes)
        f1_b = compute_macro_f1(boot_true, boot_base, num_classes)
        bootstrap_deltas[b] = f1_c - f1_b

    ci_lower = float(np.percentile(bootstrap_deltas, 2.5))
    ci_upper = float(np.percentile(bootstrap_deltas, 97.5))

    reasons: List[str] = []

    # Check Gate 1: Lower bound of Macro-F1 improvement CI must be strictly > 0
    ci_passed = bool(ci_lower > 0.0)
    if not ci_passed:
        reasons.append(
            f"Macro-F1 improvement 95% CI [{ci_lower:+.4f}, {ci_upper:+.4f}] lower bound is not strictly positive. "
            f"Statistically insignificant or uncertain gain (observed mean delta: {delta_macro_f1:+.4f})."
        )

    # Check Gate 2: No per-disease regression beyond tolerance
    regressions: List[Dict[str, Any]] = []
    for c in range(num_classes):
        drop = float(rec_base[c] - rec_cand[c])
        if drop > per_disease_tolerance:
            d_name = names[c] if c < len(names) else f"Class_{c}"
            regressions.append({
                "class_index": c,
                "disease": d_name,
                "baseline_recall": round(float(rec_base[c]), 4),
                "candidate_recall": round(float(rec_cand[c]), 4),
                "recall_drop": round(drop, 4),
                "tolerance": per_disease_tolerance
            })

    per_disease_passed = (len(regressions) == 0)
    if not per_disease_passed:
        reasons.append(
            f"Per-disease recall regression beyond tolerance ({per_disease_tolerance:.1%}) in {len(regressions)} condition(s): "
            + ", ".join([f"{r['disease']} (-{r['recall_drop']:.1%})" for r in regressions])
        )

    # Check Gate 3: No fairness degradation
    fairness_passed = True
    disparity_base = 0.0
    disparity_cand = 0.0
    delta_disparity = 0.0

    if sensitive_attr is not None:
        sens = np.asarray(sensitive_attr)
        disparity_base = compute_fairness_disparity(y_true, y_base, sens)
        disparity_cand = compute_fairness_disparity(y_true, y_cand, sens)
        delta_disparity = disparity_cand - disparity_base

        if delta_disparity > fairness_tolerance:
            fairness_passed = False
            reasons.append(
                f"Demographic parity / recall disparity degraded by {delta_disparity:+.4f} "
                f"(baseline: {disparity_base:.4f}, candidate: {disparity_cand:.4f}, tolerance: {fairness_tolerance:.4f})."
            )

    # Final Promotion Decision
    promoted = ci_passed and per_disease_passed and fairness_passed

    return {
        "promoted": promoted,
        "status": "APPROVED_FOR_PROMOTION" if promoted else "REJECTED_BY_PROMOTION_GATE",
        "macro_f1": {
            "baseline": round(macro_f1_base, 4),
            "candidate": round(macro_f1_cand, 4),
            "delta_mean": round(delta_macro_f1, 4),
            "ci_95": [round(ci_lower, 4), round(ci_upper, 4)],
            "ci_lower": round(ci_lower, 4),
            "ci_upper": round(ci_upper, 4),
            "passed": ci_passed
        },
        "per_disease": {
            "passed": per_disease_passed,
            "tolerance": per_disease_tolerance,
            "regressions": regressions,
            "regressed_classes_count": len(regressions)
        },
        "fairness": {
            "passed": fairness_passed,
            "baseline_disparity": round(disparity_base, 4),
            "candidate_disparity": round(disparity_cand, 4),
            "delta_disparity": round(delta_disparity, 4),
            "tolerance": fairness_tolerance
        },
        "reasons": reasons if not promoted else ["All statistical promotion gates passed: CI_lower > 0, zero regression beyond tolerance, zero fairness degradation."]
    }

