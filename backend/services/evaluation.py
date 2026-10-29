"""Deterministic Evaluation Script for General Disease Prediction Model.

Evaluates performance on a held-out clinical validation set:
- Per-disease Precision, Recall, and F1-score
- Macro-F1 and Top-3 Accuracy
- Expected Calibration Error (ECE) across reliability bins
- Outputs comprehensive metrics and updates docs/MODEL_CARD.md.
"""
from __future__ import annotations
import json
import os
import sys
import numpy as np
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.general_disease_model import (
    GeneralDiseaseModel,
    featurize_input,
    DISEASE_KEYS,
    DISEASE_DISPLAY_NAMES,
    MODEL_VERSION,
)


def load_dataset() -> List[dict]:
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "synthetic_clinical_supplement.json"
    )
    with open(data_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
        return doc["data"]


def compute_expected_calibration_error(confidences: np.ndarray, accuracies: np.ndarray, n_bins: int = 10) -> Tuple[float, List[dict]]:
    """Computes Expected Calibration Error (ECE) with equal-width confidence bins."""
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n_samples = len(confidences)
    bin_details = []

    for i in range(n_bins):
        low, high = bin_boundaries[i], bin_boundaries[i + 1]
        mask = (confidences > low) & (confidences <= high)
        bin_count = int(np.sum(mask))

        if bin_count > 0:
            bin_acc = float(np.mean(accuracies[mask]))
            bin_conf = float(np.mean(confidences[mask]))
            abs_diff = abs(bin_acc - bin_conf)
            weight = bin_count / n_samples
            ece += weight * abs_diff

            bin_details.append({
                "bin": f"{low:.1f}-{high:.1f}",
                "count": bin_count,
                "confidence": round(bin_conf, 3),
                "accuracy": round(bin_acc, 3),
                "calibrationGap": round(abs_diff, 3)
            })

    return round(float(ece), 4), bin_details


def run_evaluation(seed: int = 42) -> dict:
    cohort = load_dataset()
    rng = np.random.default_rng(seed)
    indices = np.arange(len(cohort))
    rng.shuffle(indices)

    # 80 / 20 split
    split_idx = int(0.80 * len(cohort))
    train_indices = indices[:split_idx]
    test_indices = indices[split_idx:]

    test_samples = [cohort[i] for i in test_indices]

    model = GeneralDiseaseModel()
    dis_to_idx = {code: i for i, code in enumerate(DISEASE_KEYS)}

    y_true_indices = []
    y_pred_probs = []

    for item in test_samples:
        pt = item["patient"]
        enc = item["encounter"]
        gt = item["ground_truth_diagnosis"]

        x = featurize_input(
            age=pt["age"],
            sex=pt["sex"],
            symptoms=enc["symptoms"],
            symptom_duration_days=enc.get("symptom_duration_days", 1),
            vitals=enc.get("vitals", {}),
            optional_labs=enc.get("optional_labs", {})
        )

        probs = model.predict_proba(x)
        y_true_indices.append(dis_to_idx[gt])
        y_pred_probs.append(probs)

    y_true = np.array(y_true_indices, dtype=np.int32)
    y_probs = np.array(y_pred_probs, dtype=np.float32)

    # Top-1 and Top-3 predictions
    top1_preds = np.argmax(y_probs, axis=1)
    top3_preds = np.argsort(y_probs, axis=1)[:, -3:]

    # Top-1 accuracy
    top1_acc = float(np.mean(top1_preds == y_true))
    # Top-3 accuracy
    top3_acc = float(np.mean([y_true[i] in top3_preds[i] for i in range(len(y_true))]))

    # Per-disease precision, recall, F1
    per_disease = {}
    f1_list = []
    prec_list = []
    rec_list = []

    for code, idx in dis_to_idx.items():
        tp = int(np.sum((top1_preds == idx) & (y_true == idx)))
        fp = int(np.sum((top1_preds == idx) & (y_true != idx)))
        fn = int(np.sum((top1_preds != idx) & (y_true == idx)))
        support = int(np.sum(y_true == idx))

        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        prec_list.append(prec)
        rec_list.append(rec)
        f1_list.append(f1)

        per_disease[code] = {
            "name": DISEASE_DISPLAY_NAMES.get(code, code),
            "support": support,
            "precision": round(prec, 3),
            "recall": round(rec, 3),
            "f1": round(f1, 3)
        }

    macro_f1 = float(np.mean(f1_list))
    macro_prec = float(np.mean(prec_list))
    macro_rec = float(np.mean(rec_list))

    # Calibration ECE
    top1_confs = np.max(y_probs, axis=1)
    top1_correct = (top1_preds == y_true).astype(np.float32)
    ece, bin_details = compute_expected_calibration_error(top1_confs, top1_correct, n_bins=10)

    report = {
        "modelVersion": MODEL_VERSION,
        "testSetSize": len(test_samples),
        "macroF1": round(macro_f1, 3),
        "macro_f1": round(macro_f1, 3),
        "macroPrecision": round(macro_prec, 3),
        "macro_precision": round(macro_prec, 3),
        "macroRecall": round(macro_rec, 3),
        "macro_recall": round(macro_rec, 3),
        "top1Accuracy": round(top1_acc, 3),
        "top1_accuracy": round(top1_acc, 3),
        "top3Accuracy": round(top3_acc, 3),
        "top3_accuracy": round(top3_acc, 3),
        "expectedCalibrationError": ece,
        "expected_calibration_error": ece,
        "calibrationBins": bin_details,
        "calibration_bins": bin_details,
        "perDisease": per_disease,
        "per_disease": per_disease,
    }

    return report


evaluate_general_disease_model = run_evaluation


def generate_model_card(report: dict, output_path: str):
    md = f"""# Model Card: TrustFed AI General Disease Differential Inference Engine

**Model Identifier**: `{report['modelVersion']}`  
**Architecture**: Calibrated Multinomial Diagnostic Linear Model ($W \\in \\mathbb{{R}}^{{55 \\times 18}}, b \\in \\mathbb{{R}}^{{18}}$)  
**Task**: Multi-class differential diagnosis across 18 common outpatient and emergency conditions.  
**Federated Learning Compatibility**: Weight-averaging compatible (FedAvg & TEFL DP-SGD).

---

## 1. Multi-Dimensional Performance Summary

> [!IMPORTANT]
> **No Headline Accuracy Claim**: In accordance with rigorous clinical evaluation standards, TrustFed AI does not cite a single oversimplified headline accuracy metric. Clinical diagnostic performance is reported through multi-class Top-3 coverage, Macro-F1, and Expected Calibration Error (ECE).

| Metric | Held-Out Test Evaluation | Clinical Interpretation |
| :--- | :--- | :--- |
| **Top-3 Differential Coverage** | **{report['top3Accuracy'] * 100:.1f}%** | In {report['top3Accuracy'] * 100:.1f}% of cases, the true diagnosis is included in the top-3 differential presented to the physician. |
| **Top-1 Strict Accuracy** | **{report['top1Accuracy'] * 100:.1f}%** | Strict top-1 exact match on presenting clinical features. |
| **Macro-F1 Score** | **{report['macroF1']:.3f}** | Unweighted average harmonic mean across all 18 condition classes. |
| **Macro Precision** | **{report['macroPrecision']:.3f}** | Average positive predictive value across conditions. |
| **Macro Recall** | **{report['macroRecall']:.3f}** | Average clinical sensitivity across conditions. |
| **Expected Calibration Error (ECE)** | **{report['expectedCalibrationError']:.4f}** | Quantifies probability calibration. Low ECE indicates predicted probabilities closely match empirical probabilities. |

---

## 2. Per-Condition Performance Breakdown

Evaluated on $N = {report['testSetSize']}$ held-out test cohort across all 18 clinical phenotypes:

| Disease Code | Clinical Condition Name | Test Support | Precision | Recall | F1-Score |
| :--- | :--- | :---: | :---: | :---: | :---: |
"""
    for code, d in report["perDisease"].items():
        md += f"| `{code}` | {d['name']} | {d['support']} | {d['precision']:.3f} | {d['recall']:.3f} | **{d['f1']:.3f}** |\n"

    md += """
---

## 3. Probability Calibration (ECE & Reliability Bins)

Predicted probabilities are scaled using temperature calibration ($T = 1.0$). Bins evaluate confidence versus empirical accuracy:

| Confidence Bin | Sample Count | Mean Confidence | Empirical Accuracy | Calibration Gap |
| :---: | :---: | :---: | :---: | :---: |
"""
    for b in report["calibrationBins"]:
        md += f"| {b['bin']} | {b['count']} | {b['confidence']:.3f} | {b['accuracy']:.3f} | {b['calibrationGap']:.3f} |\n"

    md += """
---

## 4. Native Missingness Handling & Adaptive Questioning

1. **Native Missingness Indicators**: Continuous vitals (Temp, BP, HR, SpO2, Resp Rate, Glucose) and labs (Platelets, WBC) are accompanied by binary indicators (`is_missing_<feature>`). Rather than imputing with artifacts, the model learns the clinical context of missing diagnostic investigations.
2. **Adaptive Questioning**: When top-1 probability is below 0.65, the inference engine computes the Expected Information Gain (EIG) over currently unmeasured parameters and surfaces the single most decisive observation to the clinician (e.g., *"Add SpO2 to improve this result"*).

---

## 5. Red-Flag Safety Overrides

The model is bound by deterministic clinical safety guardrails ([red_flags.py](file:///d:/projects/TrustFed/backend/services/red_flags.py)) that trigger immediate urgent warnings overriding routine ambulatory outputs:
- **Acute Coronary Syndrome (ACS)**: Chest pain with diaphoresis, dyspnea, tachycardia, or ST deviation.
- **Severe Hypoxemia**: Measured $\\text{SpO}_2 < 92\\%$.
- **Acute Stroke**: Positive FAST neurological indicators (facial droop, arm weakness, speech difficulty).
- **Suspected Meningitis**: Pyrexia combined with nuchal rigidity / neck stiffness.
- **High Fever in Infant**: Age $< 1$ year with core temperature $\\ge 38.5^\\circ\\text{C}$.
- **Hypovolemic Shock**: Severe dehydration from vomiting/diarrhea with systolic $\\text{BP} < 90\\text{ mmHg}$.

---

## 6. Known Limitations & Clinical Caution

1. **Synthetic & Clean Baseline Cohort**: The baseline pre-training supplement was generated from validated medical phenotype distributions. Real-world emergency room presentations involve complex polypharmacy, multi-morbidity, and inconsistent patient histories.
2. **Ambulatory vs Emergency Triage**: Model weights represent initial clinical triage likelihoods and must never replace diagnostic investigations (cultures, imaging, ECG).
3. **Mandatory Clinician Verification**: All suggested causes and remedies are labeled: *"Suggested, clinician must verify."*
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md.strip() + "\n")


if __name__ == "__main__":
    report = run_evaluation(seed=42)
    doc_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs",
        "MODEL_CARD.md"
    )
    generate_model_card(report, doc_path)
    print(f"Evaluation complete. Model card saved to {doc_path}")
    print(f"Top-3 Accuracy: {report['top3Accuracy']*100:.1f}%, Macro-F1: {report['macroF1']:.3f}, ECE: {report['expectedCalibrationError']}")
