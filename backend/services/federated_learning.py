"""Phase 5: Multi-Tier Hierarchical Federated Learning Engine.

Hospitals (Local DP-SGD on confirmed trainable encounters)
  -> Regional Hubs (Weighted FedAvg / SMPC)
    -> Global Admin (Global Aggregation, Promotion Gate, Versioning & Rollback).
"""
from __future__ import annotations
import datetime
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
from sqlalchemy.orm import Session

from db import models
from services import store, general_disease_model
from tefl import dp, secagg

ARTIFACT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "artifacts"
)


# ── 1. Hospital Eligibility & Data Extraction ──────────────────────────────────

DEFAULT_MIN_CONFIRMED_RECORDS = 5


def check_hospital_eligibility(
    db: Session,
    hospital_id: str,
    min_records: int = DEFAULT_MIN_CONFIRMED_RECORDS
) -> Dict[str, Any]:
    """Evaluates whether a hospital node is eligible to participate in a training round.
    
    Criteria:
    - Hospital must exist and have status == 'active'.
    - Suspended or removed hospitals are strictly excluded.
    - Hospital must have at least `min_records` doctor-confirmed, trainable encounters.
    """
    hospital = db.query(models.Hospital).filter_by(id=hospital_id).first()
    if not hospital:
        return {
            "hospitalId": hospital_id,
            "name": "Unknown Hospital",
            "hubId": None,
            "status": "not_found",
            "confirmedCount": 0,
            "eligible": False,
            "reason": f"Hospital '{hospital_id}' not found in registry."
        }

    if hospital.status != "active":
        return {
            "hospitalId": hospital.id,
            "name": hospital.name,
            "hubId": hospital.hub_id,
            "status": hospital.status,
            "confirmedCount": 0,
            "eligible": False,
            "reason": f"Hospital is currently {hospital.status}. Excluded from training."
        }

    confirmed_count = (
        db.query(models.Encounter)
        .filter_by(hospital_id=hospital.id, trainable=True)
        .filter(models.Encounter.doctor_confirmed_diagnosis != None)
        .count()
    )

    if confirmed_count < min_records:
        return {
            "hospitalId": hospital.id,
            "name": hospital.name,
            "hubId": hospital.hub_id,
            "status": hospital.status,
            "confirmedCount": confirmed_count,
            "eligible": False,
            "reason": f"Insufficient confirmed records ({confirmed_count}/{min_records} required)."
        }

    return {
        "hospitalId": hospital.id,
        "name": hospital.name,
        "hubId": hospital.hub_id,
        "status": hospital.status,
        "confirmedCount": confirmed_count,
        "eligible": True,
        "reason": "Hospital meets all eligibility criteria for federated round."
    }


def get_hospital_trainable_data(
    db: Session,
    hospital_id: str
) -> Tuple[np.ndarray, np.ndarray]:
    """Extracts and featurizes doctor-confirmed, trainable encounters for a hospital.
    
    Guarantees:
    - Only doctor-confirmed (trainable == True) encounters are extracted.
    - Raw identifiers NEVER leave this function.
    - Featurizes inputs using standardized clinical vectorizer.
    """
    encounters = (
        db.query(models.Encounter)
        .filter_by(hospital_id=hospital_id, trainable=True)
        .filter(models.Encounter.doctor_confirmed_diagnosis != None)
        .all()
    )

    if not encounters:
        return np.empty((0, len(general_disease_model.FEATURE_NAMES)), dtype=np.float32), np.empty(0, dtype=np.int32)

    X_list = []
    y_list = []
    dis_to_idx = {code: i for i, code in enumerate(general_disease_model.DISEASE_KEYS)}

    for enc in encounters:
        pt = db.query(models.Patient).filter_by(id=enc.patient_id).first()
        age = pt.age if pt else 40
        sex = pt.sex if pt else 0

        symptoms = json.loads(enc.symptoms) if enc.symptoms else []
        vitals = json.loads(enc.vitals) if enc.vitals else {}
        labs = json.loads(enc.optional_labs) if enc.optional_labs else {}

        x = general_disease_model.featurize_input(
            age=age,
            sex=sex,
            symptoms=symptoms,
            symptom_duration_days=enc.symptom_duration_days or 1,
            vitals=vitals,
            optional_labs=labs
        )
        X_list.append(x)

        gt_code = str(enc.doctor_confirmed_diagnosis).strip().lower()
        idx = dis_to_idx.get(gt_code, 0)
        y_list.append(idx)

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int32)


# ── 2. Local DP-SGD Training on Hospital Node ──────────────────────────────────

def local_train_dp_sgd(
    W_init: np.ndarray,
    b_init: np.ndarray,
    X: np.ndarray,
    y: np.ndarray,
    config: Dict[str, Any],
    rng: np.random.Generator
) -> Tuple[np.ndarray, np.ndarray]:
    """Executes multi-class local training using DP-SGD (Differential Privacy).
    
    Mechanisms:
    - Per-example gradient clipping to norm C.
    - Gaussian noise addition proportional to sigma * C.
    - Weight update: theta = theta - lr * clipped_noisy_gradient.
    """
    W = W_init.copy().astype(np.float32)
    b = b_init.copy().astype(np.float32)
    N = len(y)
    if N == 0:
        return W, b

    lr = float(config.get("lr", 0.05))
    clip = float(config.get("clip", 1.0)) if config.get("dp", True) else None
    sigma = float(config.get("noise_multiplier", config.get("sigma", 1.0))) if config.get("dp", True) else 0.0
    epochs = int(config.get("local_epochs", 1))
    batch_size = min(int(config.get("batch_size", 16)), N)

    d_in, n_classes = W.shape

    for _ in range(epochs):
        indices = rng.permutation(N)
        for start_idx in range(0, N, batch_size):
            batch_idx = indices[start_idx:start_idx + batch_size]
            B = len(batch_idx)
            X_b = X[batch_idx]
            y_b = y[batch_idx]

            # Forward pass: logits in R^{B x 18}
            logits = X_b @ W + b
            logits_max = np.max(logits, axis=1, keepdims=True)
            exp_logits = np.exp(logits - logits_max)
            probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)

            # Per-example gradients
            # d_i = p_i - e_{y_i} in R^{18}
            d = probs.copy()
            d[np.arange(B), y_b] -= 1.0

            # Gradient wrt W: x_i^T d_i in R^{55 x 18}
            # Gradient wrt b: d_i in R^{18}
            G_W = np.einsum("bi,bj->bij", X_b, d).reshape(B, -1)  # shape (B, 55*18)
            G_b = d                                                # shape (B, 18)
            G = np.concatenate([G_W, G_b], axis=1)                 # shape (B, 1008)

            if clip is not None:
                # Per-example L2 norm clipping
                norms = np.linalg.norm(G, axis=1)
                clip_factors = np.minimum(1.0, clip / np.maximum(norms, 1e-12))
                G_clipped = G * clip_factors[:, None]

                # Average clipped gradients + calibrated Gaussian noise
                sum_g = np.sum(G_clipped, axis=0)
                if sigma > 0.0:
                    noise = rng.normal(0.0, sigma * clip, size=G.shape[1])
                    g_step = (sum_g + noise) / B
                else:
                    g_step = sum_g / B
            else:
                g_step = np.mean(G, axis=0)

            # Unpack and update parameters
            g_W_step = g_step[:d_in * n_classes].reshape(d_in, n_classes)
            g_b_step = g_step[d_in * n_classes:]

            W -= lr * g_W_step
            b -= lr * g_b_step

    return W, b


def hospital_train_round(
    hospital_id: str,
    base_W: np.ndarray,
    base_b: np.ndarray,
    config: Dict[str, Any],
    db: Session,
    rng: np.random.Generator
) -> Dict[str, Any]:
    """Hospital Node Training execution.
    
    Guarantees:
    - Trains strictly on doctor-confirmed, trainable encounters.
    - Only model weights (W, b) and sample count leave the hospital.
    - Zero personal identifiers, contacts, or patient MRNs in update payload.
    """
    eligibility = check_hospital_eligibility(db, hospital_id, config.get("min_records", DEFAULT_MIN_CONFIRMED_RECORDS))
    if not eligibility["eligible"]:
        return {
            "eligible": False,
            "hospitalId": hospital_id,
            "reason": eligibility["reason"]
        }

    X, y = get_hospital_trainable_data(db, hospital_id)
    if len(y) == 0:
        return {
            "eligible": False,
            "hospitalId": hospital_id,
            "reason": "No doctor-confirmed encounters found."
        }

    updated_W, updated_b = local_train_dp_sgd(base_W, base_b, X, y, config, rng)

    # Privacy verification: payload contains strictly numerical parameter updates
    return {
        "eligible": True,
        "hospitalId": hospital_id,
        "hubId": eligibility.get("hubId"),
        "numSamples": int(len(y)),
        "weightsW": updated_W.tolist(),
        "weightsB": updated_b.tolist(),
        "modelVersion": config.get("modelVersion", general_disease_model.MODEL_VERSION)
    }


# ── 3. Regional Hub Aggregation ────────────────────────────────────────────────

def aggregate_regional_hub(
    hub_id: str,
    hospital_updates: List[Dict[str, Any]],
    config: Dict[str, Any],
    db: Session,
    rng: Optional[np.random.Generator] = None
) -> Optional[Dict[str, Any]]:
    """Aggregates local updates from hospitals in a specific regional hub.
    
    Executes sample-weighted FedAvg aggregation across hub members.
    Logs regional aggregation event in audit ledger.
    """
    hub_updates = [u for u in hospital_updates if u.get("hubId") == hub_id and u.get("eligible")]
    if not hub_updates:
        return None

    total_samples = sum(u["numSamples"] for u in hub_updates)
    if total_samples <= 0:
        return None

    d_in = len(general_disease_model.FEATURE_NAMES)
    n_classes = len(general_disease_model.DISEASE_KEYS)

    W_agg = np.zeros((d_in, n_classes), dtype=np.float64)
    b_agg = np.zeros(n_classes, dtype=np.float64)

    for u in hub_updates:
        weight = u["numSamples"] / total_samples
        W_agg += weight * np.array(u["weightsW"], dtype=np.float64)
        b_agg += weight * np.array(u["weightsB"], dtype=np.float64)

    participating = [u["hospitalId"] for u in hub_updates]

    store.add_audit(
        db,
        session_id=config.get("sessionId"),
        node_id=hub_id,
        event_type="regional_aggregation",
        description=f"Regional hub '{hub_id}' aggregated updates from {len(hub_updates)} hospitals ({total_samples} samples)."
    )

    return {
        "hubId": hub_id,
        "totalSamples": total_samples,
        "participatingHospitals": participating,
        "weightsW": W_agg.astype(np.float32).tolist(),
        "weightsB": b_agg.astype(np.float32).tolist()
    }


# ── 4. Global Server Aggregation & Divergence Safeguard ─────────────────────────

def check_model_divergence(
    W: np.ndarray,
    b: np.ndarray,
    max_norm: float = 100.0
) -> Tuple[bool, str]:
    """Safeguards against divergence: halts candidate promotion on numerical explosion."""
    if np.isnan(W).any() or np.isnan(b).any():
        return True, "Model divergence detected: weights contain NaN values."
    if np.isinf(W).any() or np.isinf(b).any():
        return True, "Model divergence detected: weights contain Inf values."
    
    w_norm = float(np.linalg.norm(W))
    b_norm = float(np.linalg.norm(b))
    if w_norm > max_norm or b_norm > max_norm:
        return True, f"Model divergence detected: parameter norm exploded (W_norm={w_norm:.2f}, b_norm={b_norm:.2f} > {max_norm})."

    return False, ""


def aggregate_global_candidate(
    regional_updates: List[Dict[str, Any]],
    config: Dict[str, Any],
    db: Session
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], List[str]]:
    """Aggregates regional hub models into a global candidate model."""
    valid_updates = [u for u in regional_updates if u and u.get("totalSamples", 0) > 0]
    if not valid_updates:
        return None, None, []

    total_samples = sum(u["totalSamples"] for u in valid_updates)
    d_in = len(general_disease_model.FEATURE_NAMES)
    n_classes = len(general_disease_model.DISEASE_KEYS)

    W_global = np.zeros((d_in, n_classes), dtype=np.float64)
    b_global = np.zeros(n_classes, dtype=np.float64)

    for u in valid_updates:
        weight = u["totalSamples"] / total_samples
        W_global += weight * np.array(u["weightsW"], dtype=np.float64)
        b_global += weight * np.array(u["weightsB"], dtype=np.float64)

    W_cand = W_global.astype(np.float32)
    b_cand = b_global.astype(np.float32)
    participating_hubs = [u["hubId"] for u in valid_updates]

    store.add_audit(
        db,
        session_id=config.get("sessionId"),
        node_id="GlobalServer",
        event_type="global_aggregation",
        description=f"Global server aggregated candidate model across {len(valid_updates)} regional hubs ({total_samples} samples total)."
    )

    return W_cand, b_cand, participating_hubs


# ── 5. Promotion Gate, Multi-Metric Evaluation & Rollback ───────────────────────

def load_heldout_validation_cohort() -> List[dict]:
    """Loads standardized held-out clinical validation set."""
    supplement_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "synthetic_clinical_supplement.json"
    )
    if os.path.exists(supplement_path):
        with open(supplement_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
            data = doc.get("data", [])
            # Return last 20% as held-out validation cohort
            split_idx = int(0.80 * len(data))
            return data[split_idx:]
    return []


def evaluate_model_on_cohort(
    W: np.ndarray,
    b: np.ndarray,
    cohort: List[dict]
) -> Dict[str, Any]:
    """Evaluates multi-class macro-F1, per-disease F1, and demographic parity across validation cohort."""
    if not cohort:
        return {"macroF1": 0.0, "perDiseaseF1": {}, "fairnessGap": 0.0}

    dis_to_idx = {code: i for i, code in enumerate(general_disease_model.DISEASE_KEYS)}
    X_list = []
    y_true = []
    sexes = []

    for item in cohort:
        pt = item["patient"]
        enc = item["encounter"]
        gt = item["ground_truth_diagnosis"]

        x = general_disease_model.featurize_input(
            age=pt["age"],
            sex=pt["sex"],
            symptoms=enc["symptoms"],
            symptom_duration_days=enc.get("symptom_duration_days", 1),
            vitals=enc.get("vitals", {}),
            optional_labs=enc.get("optional_labs", {})
        )
        X_list.append(x)
        y_true.append(dis_to_idx[gt])
        sexes.append(pt["sex"])

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_true, dtype=np.int32)

    # Predict
    logits = X @ W + b
    preds = np.argmax(logits, axis=1)

    # Per-disease F1
    per_disease = {}
    f1_list = []
    for code, idx in dis_to_idx.items():
        tp = int(np.sum((preds == idx) & (y == idx)))
        fp = int(np.sum((preds == idx) & (y != idx)))
        fn = int(np.sum((preds != idx) & (y == idx)))
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        f1_list.append(f1)
        per_disease[code] = round(float(f1), 4)

    macro_f1 = float(np.mean(f1_list))

    # Fairness disparity: accuracy gap across sex (0=Female vs 1=Male)
    sexes_arr = np.array(sexes)
    f_mask = sexes_arr == 0
    m_mask = sexes_arr == 1
    f_acc = float(np.mean(preds[f_mask] == y[f_mask])) if f_mask.any() else 0.0
    m_acc = float(np.mean(preds[m_mask] == y[m_mask])) if m_mask.any() else 0.0
    fairness_gap = abs(f_acc - m_acc)

    return {
        "macroF1": round(macro_f1, 4),
        "perDiseaseF1": per_disease,
        "fairnessGap": round(fairness_gap, 4),
        "femaleAccuracy": round(f_acc, 4),
        "maleAccuracy": round(m_acc, 4),
    }


def evaluate_and_promote_gate(
    candidate_W: np.ndarray,
    candidate_b: np.ndarray,
    current_model: general_disease_model.GeneralDiseaseModel,
    config: Dict[str, Any],
    db: Session,
    validation_cohort: Optional[List[dict]] = None
) -> Dict[str, Any]:
    """Promotion Gate:
    Promote ONLY if:
    1. No divergence (NaNs/Infs/weight explosion).
    2. Overall Macro-F1 improves (or meets tolerance).
    3. No individual disease regresses beyond configured tolerance (default 0.05).
    4. Fairness audit does not degrade beyond tolerance.
    """
    # 1. Divergence check
    is_divergent, div_reason = check_model_divergence(candidate_W, candidate_b)
    if is_divergent:
        store.add_audit(
            db,
            session_id=config.get("sessionId"),
            node_id="GlobalServer",
            event_type="model_divergence_rejected",
            description=f"Candidate model rejected: {div_reason}"
        )
        return {
            "promoted": False,
            "diverged": True,
            "reason": div_reason,
            "modelVersion": current_model.version
        }

    cohort = validation_cohort or load_heldout_validation_cohort()
    if not cohort:
        return {
            "promoted": False,
            "reason": "Validation cohort not available for promotion gate.",
            "modelVersion": current_model.version
        }

    # Evaluate current baseline
    curr_eval = evaluate_model_on_cohort(current_model.W, current_model.b, cohort)
    cand_eval = evaluate_model_on_cohort(candidate_W, candidate_b, cohort)

    reg_tol = float(config.get("regression_tolerance", 0.05))
    fair_tol = float(config.get("fairness_tolerance", 0.05))

    rejections: List[str] = []

    # Criterion A: Overall Macro-F1
    if cand_eval["macroF1"] < curr_eval["macroF1"] - 0.001:
        rejections.append(
            f"Overall Macro-F1 dropped from {curr_eval['macroF1']:.3f} to {cand_eval['macroF1']:.3f}."
        )

    # Criterion B: Per-disease regression check
    for disease, curr_f1 in curr_eval["perDiseaseF1"].items():
        cand_f1 = cand_eval["perDiseaseF1"].get(disease, 0.0)
        drop = curr_f1 - cand_f1
        if drop > reg_tol:
            rejections.append(
                f"Disease '{disease}' regressed by {drop:.3f} (F1 dropped from {curr_f1:.3f} to {cand_f1:.3f}, exceeds tolerance {reg_tol})."
            )

    # Criterion C: Fairness audit degradation check
    fair_delta = cand_eval["fairnessGap"] - curr_eval["fairnessGap"]
    if fair_delta > fair_tol:
        rejections.append(
            f"Fairness disparity gap increased by {fair_delta:.3f} (exceeds tolerance {fair_tol})."
        )

    if rejections:
        # Reject candidate model
        rejection_summary = "; ".join(rejections)
        store.add_audit(
            db,
            session_id=config.get("sessionId"),
            node_id="GlobalServer",
            event_type="model_rejected",
            description=f"Promotion gate blocked candidate model: {rejection_summary}"
        )
        return {
            "promoted": False,
            "diverged": False,
            "reason": rejection_summary,
            "rejections": rejections,
            "currentMetrics": curr_eval,
            "candidateMetrics": cand_eval,
            "modelVersion": current_model.version
        }

    # All criteria passed: PROMOTE MODEL
    # Determine new version identifier (guaranteeing uniqueness across all runs)
    parts = current_model.version.split("-v")
    base_prefix = parts[0] if len(parts) > 1 else "TF-GenDisease"
    try:
        ver_num = float(parts[1]) if len(parts) > 1 else 1.0
    except ValueError:
        ver_num = 1.0

    existing_ver_rows = db.query(models.ModelVersion.version).all()
    existing_ver_set = {v[0] for v in existing_ver_rows}

    next_ver = ver_num + 0.1
    candidate_ver_str = f"{base_prefix}-v{next_ver:.1f}"
    while candidate_ver_str in existing_ver_set:
        next_ver += 0.1
        candidate_ver_str = f"{base_prefix}-v{next_ver:.1f}"
    new_version = candidate_ver_str

    # Save artifact checkpoint
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    checkpoint_path = os.path.join(ARTIFACT_DIR, f"{new_version}.npz")
    np.savez(checkpoint_path, W=candidate_W, b=candidate_b, version=new_version)

    # Update database model_versions table
    # Archive previous active global model
    prev_active = db.query(models.ModelVersion).filter_by(scope="global", status="active").all()
    for m in prev_active:
        m.status = "archived"

    new_mv = models.ModelVersion(
        version=new_version,
        scope="global",
        scope_id=None,
        disease_category="General Multi-Condition",
        metrics=json.dumps(cand_eval),
        model_path=checkpoint_path,
        status="active"
    )
    db.add(new_mv)
    db.commit()

    # Update active singleton instance in memory so hospitals receive it immediately
    general_disease_model.set_model_weights(candidate_W, candidate_b, new_version)

    store.add_audit(
        db,
        session_id=config.get("sessionId"),
        node_id="GlobalServer",
        event_type="model_promoted",
        description=f"Candidate model successfully PROMOTED to {new_version}. Macro-F1: {cand_eval['macroF1']:.3f} (was {curr_eval['macroF1']:.3f}). Zero regressions > {reg_tol}."
    )

    return {
        "promoted": True,
        "diverged": False,
        "modelVersion": new_version,
        "previousVersion": current_model.version,
        "currentMetrics": curr_eval,
        "promotedMetrics": cand_eval,
        "modelPath": checkpoint_path
    }


def rollback_global_model(target_version: str, db: Session) -> Dict[str, Any]:
    """Rolls back the active global model to a previously promoted version.
    
    Guarantees:
    - 1-click rollback to any valid archived version or initial baseline.
    - Updates active singleton so predictions immediately use rolled-back weights.
    - Logs rollback event to hash-chained audit ledger.
    """
    mv = db.query(models.ModelVersion).filter_by(version=target_version).first()

    # Base model handling
    if target_version == "TF-GenDisease-v1.0":
        base = general_disease_model.GeneralDiseaseModel()
        general_disease_model.set_model_weights(base.W, base.b, target_version)
        current_active = db.query(models.ModelVersion).filter_by(scope="global", status="active").all()
        for c in current_active:
            c.status = "archived"
        if mv:
            mv.status = "active"
        db.commit()

        store.add_audit(
            db,
            session_id=None,
            node_id="GlobalServer",
            event_type="model_rollback",
            description=f"Global model rolled back to base version: {target_version}"
        )
        return {"status": "success", "activeVersion": target_version}

    if not mv:
        raise ValueError(f"Target model version '{target_version}' not found in registry.")

    if not mv.model_path or not os.path.exists(mv.model_path):
        raise FileNotFoundError(f"Model checkpoint for '{target_version}' is missing on disk.")

    data = np.load(mv.model_path)
    W = data["W"]
    b = data["b"]

    # Update database records
    current_active = db.query(models.ModelVersion).filter_by(scope="global", status="active").all()
    for c in current_active:
        c.status = "archived"

    mv.status = "active"
    db.commit()

    # Re-activate in memory
    general_disease_model.set_model_weights(W, b, target_version)

    store.add_audit(
        db,
        session_id=None,
        node_id="GlobalServer",
        event_type="model_rollback",
        description=f"Global model successfully rolled back to version: {target_version}"
    )

    return {
        "status": "success",
        "activeVersion": target_version,
        "modelPath": mv.model_path
    }


# ── 6. Optional De-Identified Record Sharing (Allow-List Serializer) ────────────

def calculate_age_band(age: int) -> str:
    """Bins exact age into de-identified decadal age bands."""
    if age < 10: return "0-9"
    elif age < 20: return "10-19"
    elif age < 30: return "20-29"
    elif age < 40: return "30-39"
    elif age < 50: return "40-49"
    elif age < 60: return "50-59"
    elif age < 70: return "60-69"
    else: return "70+"


ALLOWED_DEIDENTIFIED_KEYS = {
    "age_band", "sex", "symptoms", "vitals", "confirmed_diagnosis", "cause", "treatment"
}


def serialize_deidentified_record(
    patient: models.Patient,
    encounter: models.Encounter
) -> Dict[str, Any]:
    """Strict allow-list serializer for regional de-identified research sharing.
    
    Enforces HIPAA Safe Harbor:
    - Age is coarsened to decadal age-band.
    - Biological sex only.
    - Symptoms and sanitized vitals only.
    - Confirmed clinical diagnosis, etiology cause, and treatment only.
    - STRICT PROHIBITION: Never includes names, contacts, MRNs, patient IDs, addresses, or exact DOBs.
    """
    symptoms_list = json.loads(encounter.symptoms) if encounter.symptoms else []
    vitals_dict = json.loads(encounter.vitals) if encounter.vitals else {}

    sex_label = "Female" if patient.sex == 0 else ("Male" if patient.sex == 1 else "Other")

    record = {
        "age_band": calculate_age_band(patient.age),
        "sex": sex_label,
        "symptoms": symptoms_list,
        "vitals": vitals_dict,
        "confirmed_diagnosis": encounter.doctor_confirmed_diagnosis,
        "cause": encounter.cause,
        "treatment": encounter.treatment,
    }

    # Strict assertion: Ensure zero non-allow-listed keys exist
    for k in list(record.keys()):
        if k not in ALLOWED_DEIDENTIFIED_KEYS:
            del record[k]

    return record


def get_regional_deidentified_records(
    hub_id: str,
    db: Session,
    user: Optional[models.User] = None
) -> Dict[str, Any]:
    """Returns de-identified clinical records for consenting hospitals within a regional hub.
    
    Guarantees:
    - Default is OFF (share_deidentified boolean).
    - Requires both hospital.share_deidentified == True AND an active ConsentRecord.
    - Non-consenting hospitals return zero records.
    - All output is passed through the allow-list serializer.
    """
    hospitals = db.query(models.Hospital).filter_by(hub_id=hub_id).all()
    records: List[Dict[str, Any]] = []
    consenting_hospitals = []
    non_consenting_hospitals = []

    for hosp in hospitals:
        # Check explicit consent record
        active_consent = (
            db.query(models.ConsentRecord)
            .filter_by(
                hospital_id=hosp.id,
                consent_type="FEDERATED_TRAINING_DEIDENTIFIED",
                status="granted"
            )
            .first()
        )

        has_permission = bool(hosp.share_deidentified and active_consent)

        if has_permission:
            consenting_hospitals.append(hosp.id)
            encounters = (
                db.query(models.Encounter)
                .filter_by(hospital_id=hosp.id, trainable=True)
                .filter(models.Encounter.doctor_confirmed_diagnosis != None)
                .all()
            )
            for enc in encounters:
                pt = db.query(models.Patient).filter_by(id=enc.patient_id).first()
                if pt:
                    rec = serialize_deidentified_record(pt, enc)
                    # Verify allow-list invariants
                    assert "name" not in rec and "contact" not in rec and "patient_identifier" not in rec
                    records.append(rec)
        else:
            non_consenting_hospitals.append(hosp.id)

    store.add_audit(
        db,
        session_id=None,
        node_id=hub_id,
        event_type="deidentified_sharing_accessed",
        description=f"Regional hub '{hub_id}' accessed {len(records)} de-identified records from {len(consenting_hospitals)} consenting hospitals."
    )

    return {
        "hubId": hub_id,
        "totalRecords": len(records),
        "consentingHospitals": consenting_hospitals,
        "nonConsentingHospitals": non_consenting_hospitals,
        "records": records
    }


# ── 7. Honest Privacy Accounting Calculator ───────────────────────────────────

def get_honest_privacy_accounting(
    cohort_sizes: List[int],
    rounds: int,
    sigma: float,
    clip: float = 1.0,
    target_epsilon: Optional[float] = None,
    delta: float = 1e-5,
    batch_size: int = 16
) -> Dict[str, Any]:
    """Honest Differential Privacy Accounting.
    
    Guarantees:
    - Computes actual epsilon spent using RDP accountant for exact sigma used.
    - If target epsilon cannot be achieved with stability ceiling (sigma <= 3.5),
      reports the real actual spent epsilon and evaluates targetMet = False.
    - Never falsifies or clamps the displayed epsilon to match an unachieved target.
    """
    if not cohort_sizes or sigma <= 0 or rounds <= 0:
        return {
            "actualEpsilon": float("inf") if sigma <= 0 else 0.0,
            "targetEpsilon": target_epsilon,
            "targetMet": False,
            "sigma": sigma,
            "delta": delta,
            "warning": "DP noise multiplier is zero or round count is zero."
        }

    # Evaluate worst-case hospital epsilon
    worst_eps = 0.0
    for n in cohort_sizes:
        if n > 0:
            q = min(1.0, batch_size / n)
            steps = max(1, round(n / batch_size)) * rounds
            eps_val = dp.epsilon(q, sigma, steps, delta)
            worst_eps = max(worst_eps, eps_val)

    actual_eps = round(float(worst_eps), 3)

    target_met = True
    warning = None

    if target_epsilon is not None:
        if actual_eps > float(target_epsilon) + 0.01:
            target_met = False
            warning = (
                f"Target epsilon of {target_epsilon:.2f} cannot be achieved because hospital cohort size "
                f"is small. Reporting certified actual spent epsilon ({actual_eps:.2f}) honestly."
            )

    return {
        "epsilon": actual_eps,
        "actualEpsilon": actual_eps,
        "targetEpsilon": target_epsilon,
        "targetMet": target_met,
        "sigma": sigma,
        "sigmaActual": sigma,
        "clip": clip,
        "delta": delta,
        "warning": warning,
        "disclaimer": warning
    }


# ── 8. Full Hierarchical Federated Round Orchestrator ─────────────────────────

def run_hierarchical_federated_round(
    config: Dict[str, Any],
    db: Session,
    seed: int = 42
) -> Dict[str, Any]:
    """Orchestrates an end-to-end multi-tier federated learning round:
    
    Hospital Tier -> Regional Hub Tier -> Global Server Tier -> Promotion Gate.
    """
    rng = np.random.default_rng(seed)
    session_id = f"FL-{datetime.date.today().year}-{rng.integers(100, 999)}"
    config["sessionId"] = session_id

    store.add_audit(
        db,
        session_id=session_id,
        node_id="GlobalServer",
        event_type="federated_round_triggered",
        description=f"Global admin triggered federated round {session_id} across regional hubs."
    )

    current_model = general_disease_model.get_model()
    base_W = current_model.W.copy()
    base_b = current_model.b.copy()

    # Step 1: Query all registered hubs and hospitals
    hubs = db.query(models.RegionalHub).filter_by(status="active").all()
    all_hospitals = db.query(models.Hospital).all()

    # Step 2: Hospital tier training
    hospital_updates = []
    eligibility_reports = []

    for hosp in all_hospitals:
        report = check_hospital_eligibility(db, hosp.id, config.get("min_records", DEFAULT_MIN_CONFIRMED_RECORDS))
        eligibility_reports.append(report)

        if report["eligible"]:
            update = hospital_train_round(hosp.id, base_W, base_b, config, db, rng)
            if update.get("eligible"):
                hospital_updates.append(update)
                store.add_audit(
                    db,
                    session_id=session_id,
                    node_id=hosp.id,
                    event_type="hospital_update_received",
                    description=f"Hospital '{hosp.id}' trained locally on {update['numSamples']} doctor-confirmed encounters (DP-SGD)."
                )

    if not hospital_updates:
        store.add_audit(
            db,
            session_id=session_id,
            node_id="GlobalServer",
            event_type="round_aborted",
            description="Round aborted: no eligible hospital nodes with minimum confirmed records."
        )
        return {
            "sessionId": session_id,
            "status": "aborted",
            "reason": "No eligible hospitals available.",
            "eligibility": eligibility_reports
        }

    # Step 3: Regional tier aggregation
    regional_updates = []
    for hub in hubs:
        reg_agg = aggregate_regional_hub(hub.id, hospital_updates, config, db, rng)
        if reg_agg:
            regional_updates.append(reg_agg)

    if not regional_updates:
        return {
            "sessionId": session_id,
            "status": "aborted",
            "reason": "No regional hub updates formed.",
            "eligibility": eligibility_reports
        }

    # Step 4: Global tier aggregation
    candidate_W, candidate_b, participating_hubs = aggregate_global_candidate(regional_updates, config, db)
    if candidate_W is None:
        return {
            "sessionId": session_id,
            "status": "aborted",
            "reason": "Global candidate aggregation failed.",
            "eligibility": eligibility_reports
        }

    # Step 5: Promotion gate evaluation
    gate_res = evaluate_and_promote_gate(candidate_W, candidate_b, current_model, config, db)

    # Privacy calculation
    cohort_sizes = [u["numSamples"] for u in hospital_updates]
    privacy = get_honest_privacy_accounting(
        cohort_sizes=cohort_sizes,
        rounds=1,
        sigma=float(config.get("noise_multiplier", 1.0)),
        clip=float(config.get("clip", 1.0)),
        target_epsilon=config.get("target_epsilon")
    )

    return {
        "sessionId": session_id,
        "status": "promoted" if gate_res["promoted"] else ("rejected" if not gate_res.get("diverged") else "diverged"),
        "gateResult": gate_res,
        "privacy": privacy,
        "participatingHospitals": [u["hospitalId"] for u in hospital_updates],
        "participatingHubs": participating_hubs,
        "totalHospitalUpdates": len(hospital_updates),
        "eligibilityReports": eligibility_reports
    }
