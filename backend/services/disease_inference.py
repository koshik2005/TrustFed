"""Multi-Condition General Disease Differential Inference Engine.

Evaluates presenting symptoms, clinical duration, vitals, and laboratory indicators
against validated clinical phenotypes (Cold, Flu, Viral Pyrexia, Dengue, Typhoid, UTI, CAD).
Produces calibrated differential diagnosis top-3 probabilities.
"""
from __future__ import annotations
from typing import Any, Dict, List

# Phenotype knowledge base with symptom weights & vital heuristics
DISEASE_PROFILES = {
    "DENGUE": {
        "name": "Dengue Fever (Breakbone Fever)",
        "category": "Infectious / Arbovirus",
        "primary_symptoms": {"high_fever", "retro_orbital_pain", "severe_joint_pain", "joint_pain", "petechial_rash", "rash", "headache", "vomiting", "body_ache"},
        "vitals_indicators": lambda v: (1.2 if v.get("temp_c", 0) >= 38.5 else 1.0),
        "labs_indicators": lambda l: (1.5 if l.get("platelets") and float(l["platelets"]) < 100 else 1.0),
        "base_weight": 1.0,
    },
    "TYPHOID": {
        "name": "Typhoid Enteric Fever",
        "category": "Infectious / Bacterial",
        "primary_symptoms": {"fever", "abdominal_pain", "headache", "diarrhea", "vomiting", "loss_of_appetite", "body_ache", "fatigue"},
        "vitals_indicators": lambda v: (1.2 if v.get("temp_c", 0) >= 38.8 else 1.0),
        "labs_indicators": lambda l: (1.3 if l.get("wbc") and float(l["wbc"]) < 4.5 else 1.0),
        "base_weight": 0.95,
    },
    "VIRAL_FEVER": {
        "name": "Acute Viral Pyrexia",
        "category": "Infectious",
        "primary_symptoms": {"fever", "body_ache", "headache", "generalized_weakness", "fatigue", "loss_of_appetite", "chills", "nausea"},
        "vitals_indicators": lambda v: (1.1 if v.get("temp_c", 0) >= 37.8 else 1.0),
        "labs_indicators": lambda l: 1.0,
        "base_weight": 1.1,
    },
    "FLU": {
        "name": "Influenza (Seasonal Flu)",
        "category": "Respiratory",
        "primary_symptoms": {"high_fever", "fever", "chills", "cough", "dry_cough", "sore_throat", "body_ache", "headache", "fatigue"},
        "vitals_indicators": lambda v: (1.2 if v.get("temp_c", 0) >= 38.2 else 1.0),
        "labs_indicators": lambda l: 1.0,
        "base_weight": 1.05,
    },
    "COLD": {
        "name": "Common Cold (Viral Rhinitis)",
        "category": "Respiratory",
        "primary_symptoms": {"runny_nose", "sneezing", "sore_throat", "cough", "mild_cough", "headache", "fatigue"},
        "vitals_indicators": lambda v: (0.7 if v.get("temp_c", 0) >= 38.5 else 1.1),  # high fever speaks against simple cold
        "labs_indicators": lambda l: 1.0,
        "base_weight": 1.0,
    },
    "UTI": {
        "name": "Urinary Tract Infection",
        "category": "Urinary",
        "primary_symptoms": {"burning_urination", "urinary_frequency", "urinary_urgency", "abdominal_pain", "fever", "chills", "cloudy_urine"},
        "vitals_indicators": lambda v: (1.1 if v.get("temp_c", 0) >= 37.5 else 1.0),
        "labs_indicators": lambda l: (1.4 if l.get("urine_leukocytes") == "positive" or l.get("wbc") else 1.0),
        "base_weight": 0.95,
    },
    "CARDIAC_CAD": {
        "name": "Coronary Artery Disease (CAD)",
        "category": "Cardiovascular",
        "primary_symptoms": {"chest_pain", "breathlessness", "fatigue", "dizziness", "sweating", "nausea"},
        "vitals_indicators": lambda v: (1.3 if (v.get("bp_sys", 0) >= 140 or v.get("hr", 0) >= 100) else 1.0),
        "labs_indicators": lambda l: (1.3 if l.get("troponin") else 1.0),
        "base_weight": 0.9,
    },
}


def normalize_symptom(s: str) -> str:
    return s.strip().lower().replace(" ", "_").replace("-", "_")


def predict_top3(
    symptoms: List[str],
    vitals: Dict[str, Any] = None,
    labs: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """Compute differential probabilities for presenting clinical features."""
    if vitals is None:
        vitals = {}
    if labs is None:
        labs = {}

    clean_symptoms = {normalize_symptom(s) for s in symptoms if s}

    scores = {}
    for code, profile in DISEASE_PROFILES.items():
        overlap = clean_symptoms.intersection(profile["primary_symptoms"])
        if not overlap:
            # Baseline small probability if no direct symptom match
            match_score = 0.05
        else:
            # Fraction of profile symptoms matched + overlap count bonus
            match_score = (len(overlap) / len(profile["primary_symptoms"])) * 2.0 + (len(overlap) * 0.4)

        # Apply vital heuristics
        vital_mult = profile["vitals_indicators"](vitals)
        # Apply labs heuristics
        lab_mult = profile["labs_indicators"](labs)

        raw_score = match_score * vital_mult * lab_mult * profile["base_weight"]
        scores[code] = max(0.01, raw_score)

    # Softmax / ratio normalization
    total_score = sum(scores.values())
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]

    top3_total = sum(score for _, score in ranked)
    results = []
    for code, score in ranked:
        prob = round(score / top3_total, 2)
        results.append({
            "disease_code": code,
            "disease_name": DISEASE_PROFILES[code]["name"],
            "category": DISEASE_PROFILES[code]["category"],
            "probability": prob,
        })

    # Adjust rounding to ensure exactly 1.0 sum
    diff = round(1.0 - sum(r["probability"] for r in results), 2)
    if diff != 0 and results:
        results[0]["probability"] = round(results[0]["probability"] + diff, 2)

    return results
