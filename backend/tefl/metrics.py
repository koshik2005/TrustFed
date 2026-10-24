import numpy as np
from sklearn.metrics import roc_auc_score, f1_score


def accuracy(y, pred): return float((np.asarray(y) == np.asarray(pred)).mean())
def auc_score(y, p): return float(roc_auc_score(y, p)) if len(set(y)) > 1 else float("nan")
def f1(y, pred): return float(f1_score(y, pred, zero_division=0))
