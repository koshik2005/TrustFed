"""Real model inference + exact SHAP for one patient (replaces the old hard-coded rule)."""
from __future__ import annotations
import numpy as np
from tefl import nn, explain
from tefl.data import FEATURES

# frontend field -> (model feature, display name, (min, max))
FIELD_MAP = {
    "age": ("age", "Age", (1, 120)), "sex": ("sex", "Sex (1=M)", (0, 1)),
    "chestPainType": ("cp", "Chest Pain Type", (1, 4)), "restingBP": ("trestbps", "Resting BP", (60, 260)),
    "cholesterol": ("chol", "Cholesterol", (80, 700)), "fastingBloodSugar": ("fbs", "Fasting Sugar >120", (0, 1)),
    "restingECG": ("restecg", "Resting ECG", (0, 2)), "maxHeartRate": ("thalach", "Max Heart Rate", (40, 250)),
    "exerciseAngina": ("exang", "Exercise Angina", (0, 1)), "oldPeak": ("oldpeak", "ST Depression", (0, 10)),
    "slope": ("slope", "ST Slope", (1, 3)), "ca": ("ca", "Major Vessels (ca)", (0, 4)), "thal": ("thal", "Thalassemia", (3, 7)),
}


def load_model(path: str) -> dict:
    z = np.load(path, allow_pickle=False)
    return {"theta": z["theta"], "mu": z["mu"], "sd": z["sd"], "dataset": str(z["dataset"])}


def vitals_to_vector(v: dict) -> np.ndarray:
    row = {}
    missing = [k for k in FIELD_MAP if k not in v or v[k] in (None, "")]
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")
    for k, (feat, _, (lo, hi)) in FIELD_MAP.items():
        try:
            x = float(v[k])
        except (TypeError, ValueError):
            raise ValueError(f"{k} must be a number")
        if not lo <= x <= hi:
            raise ValueError(f"{k}={x} outside plausible range [{lo}, {hi}]")
        row[feat] = x
    return np.array([row[f] for f in FEATURES])


def risk_label(p: float) -> str:
    return "Low" if p < 0.33 else ("Medium" if p < 0.66 else "High")


def predict(model: dict, vitals: dict) -> dict:
    raw = vitals_to_vector(vitals)
    x = (raw - model["mu"]) / model["sd"]
    p = float(nn.predict_proba(model["theta"], x[None])[0, 1])
    phi, _ = explain.shap_values(model["theta"], x)
    shap = []
    for (k, (feat, label, _)), val in zip(FIELD_MAP.items(), raw):
        shap.append({"feature": label, "value": float(phi[FEATURES.index(feat)]), "featureValue": float(val)})
    shap.sort(key=lambda d: -abs(d["value"]))
    return {"riskScore": p, "riskLabel": risk_label(p), "confidence": max(p, 1 - p), "shapValues": shap,
            "dataset": model["dataset"]}


def template_explanation(vitals: dict, p: float, shap: list) -> str:
    up = [s for s in shap if s["value"] > 0][:2]
    down = [s for s in shap if s["value"] < 0][:1]
    txt = f"The model estimates a {p:.0%} probability of heart disease ({risk_label(p)} risk)."
    if up:
        txt += " Main contributors raising risk: " + ", ".join(f"{s['feature']} ({s['featureValue']:g})" for s in up) + "."
    if down:
        txt += f" Main protective factor: {down[0]['feature']} ({down[0]['featureValue']:g})."
    return txt + " This is a decision-support estimate, not a diagnosis."
