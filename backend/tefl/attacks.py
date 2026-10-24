"""Membership-inference attack (Yeom et al. loss-threshold) used to *empirically* test privacy."""
from __future__ import annotations
import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve
from . import nn


def loss_threshold_mia(theta, X_mem, y_mem, X_non, y_non):
    """Score = -loss. AUC=0.5 -> no leakage. advantage = max(TPR-FPR)."""
    s = np.concatenate([-nn.losses(theta, X_mem, y_mem), -nn.losses(theta, X_non, y_non)])
    lab = np.concatenate([np.ones(len(y_mem)), np.zeros(len(y_non))])
    auc = float(roc_auc_score(lab, s))
    fpr, tpr, _ = roc_curve(lab, s)
    return {"auc": auc, "advantage": float(np.max(tpr - fpr)),
            "balanced_acc": float(np.max(0.5 * (tpr + 1 - fpr)))}
