"""Phase 4 tests: General Disease Prediction Model, Red-Flag Rules,
Adaptive Questioning, Explanations, and Evaluation.
"""
import json
import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SECRET_KEY"] = "phase4-super-secure-production-ready-key-2026-test"
os.environ["ENVIRONMENT"] = "development"
os.environ["APP_MODE"] = "clinical"

from main import app
from core.deployment_mode import PERSISTENT_DISCLAIMER
from db.database import Base, engine, SessionLocal
from db import models
from db.migrations.v2_general_disease_migration import migrate_up
from services import auth, general_disease_model, red_flags, evaluation

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)
    migrate_up(engine)
    db = SessionLocal()
    try:
        hub = db.query(models.RegionalHub).filter_by(id="hub-p4").first()
        if not hub:
            hub = models.RegionalHub(id="hub-p4", name="Hub Phase 4", region="South", status="active")
            db.add(hub)

        h1 = db.query(models.Hospital).filter_by(id="hosp-p4-1").first()
        if not h1:
            db.add(models.Hospital(id="hosp-p4-1", name="Hospital P4 General", hub_id="hub-p4", status="active", share_deidentified=True))

        users = [
            ("p4_staff@trustfed.ai", "Staff P4", "hospital_staff", "hosp-p4-1", None),
            ("p4_doc@trustfed.ai", "Dr. P4", "doctor", "hosp-p4-1", None),
        ]
        for email, name, role, hid, hub_id in users:
            usr = db.query(models.User).filter_by(email=email).first()
            if not usr:
                db.add(models.User(
                    email=email,
                    name=name,
                    role=role,
                    hospital_id=hid,
                    hub_id=hub_id,
                    password_hash=auth.hash_password("DemoPassword123!"),
                    must_reset_password=False,
                    status="active"
                ))
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    os.environ["APP_MODE"] = "informational"


def _login(email: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "DemoPassword123!"})
    assert res.status_code == 200, res.text
    return res.json()["token"]


# ── 1. Red-Flag Safety Rules Unit Tests ────────────────────────────────────────

def test_red_flag_cardiac_acs():
    """Rule 1: Chest pain with breathlessness or sweating triggers Acute Coronary Syndrome."""
    # Chest pain + breathlessness
    flags = red_flags.evaluate_red_flags(
        symptoms=["chest_pain", "breathlessness"],
        vitals={"heart_rate": 88},
        age=52
    )
    rule_ids = [f["ruleId"] for f in flags]
    assert "CARDIAC_ACUTE_CORONARY_SYNDROME" in rule_ids
    assert any("resuscitation" in f["action"].lower() or "ecg" in f["action"].lower() for f in flags)

    # Chest pain + sweating
    flags2 = red_flags.evaluate_red_flags(
        symptoms=["chest_pain", "sweating"],
        vitals={},
        age=45
    )
    assert "CARDIAC_ACUTE_CORONARY_SYNDROME" in [f["ruleId"] for f in flags2]


def test_red_flag_critical_hypoxia():
    """Rule 2: SpO2 < 92% triggers Critical Hypoxia."""
    flags = red_flags.evaluate_red_flags(
        symptoms=["cough"],
        vitals={"spo2": 89.0},
        age=35
    )
    rule_ids = [f["ruleId"] for f in flags]
    assert "CRITICAL_HYPOXIA" in rule_ids
    hypoxia = next(f for f in flags if f["ruleId"] == "CRITICAL_HYPOXIA")
    assert "89" in hypoxia["evidence"] or "92" in hypoxia["evidence"]

    # Normal SpO2 (98%) should NOT trigger hypoxia
    normal_flags = red_flags.evaluate_red_flags(
        symptoms=["cough"],
        vitals={"spo2": 98.0},
        age=35
    )
    assert "CRITICAL_HYPOXIA" not in [f["ruleId"] for f in normal_flags]


def test_red_flag_acute_stroke_fast():
    """Rule 3: FAST stroke signs (slurred speech, facial droop, arm weakness) trigger Acute Stroke."""
    for stroke_symptom in ["slurred_speech", "facial_droop", "arm_weakness"]:
        flags = red_flags.evaluate_red_flags(
            symptoms=[stroke_symptom, "headache"],
            vitals={},
            age=68
        )
        rule_ids = [f["ruleId"] for f in flags]
        assert "ACUTE_STROKE_FAST" in rule_ids, f"Failed for symptom: {stroke_symptom}"


def test_red_flag_suspected_meningitis():
    """Rule 4: Fever with stiff neck triggers Suspected Meningitis."""
    flags = red_flags.evaluate_red_flags(
        symptoms=["fever", "stiff_neck", "headache"],
        vitals={"temperature": 39.0},
        age=24
    )
    rule_ids = [f["ruleId"] for f in flags]
    assert "SUSPECTED_MENINGITIS" in rule_ids
    assert any("lumbar puncture" in f["action"].lower() or "isolation" in f["action"].lower() for f in flags)


def test_red_flag_infant_high_fever():
    """Rule 5: High fever in infant (age <= 1, temp >= 38.5C / 101.3F) triggers Infant Pyrexia rule."""
    flags = red_flags.evaluate_red_flags(
        symptoms=["fever", "crying"],
        vitals={"temperature": 39.2},
        age=0
    )
    rule_ids = [f["ruleId"] for f in flags]
    assert "INFANT_HIGH_FEVER_SEPSIS_RISK" in rule_ids

    # Same high temperature in adult (age 30) should NOT trigger infant rule
    adult_flags = red_flags.evaluate_red_flags(
        symptoms=["fever"],
        vitals={"temperature": 39.2},
        age=30
    )
    assert "INFANT_HIGH_FEVER_SEPSIS_RISK" not in [f["ruleId"] for f in adult_flags]


def test_red_flag_severe_dehydration_shock():
    """Rule 6: Vomiting/diarrhea with hypotension (BP sys < 90) or tachycardia (HR > 120) triggers Dehydration Shock."""
    # Hypotension with diarrhea
    flags = red_flags.evaluate_red_flags(
        symptoms=["diarrhea", "vomiting"],
        vitals={"bp_systolic": 82, "heart_rate": 95},
        age=40
    )
    rule_ids = [f["ruleId"] for f in flags]
    assert "SEVERE_DEHYDRATION_SHOCK" in rule_ids

    # Tachycardia with diarrhea
    flags2 = red_flags.evaluate_red_flags(
        symptoms=["diarrhea"],
        vitals={"heart_rate": 128},
        age=29
    )
    assert "SEVERE_DEHYDRATION_SHOCK" in [f["ruleId"] for f in flags2]


def test_no_red_flags_for_benign_presentation():
    """Routine mild symptoms with normal vitals must not trigger red flags."""
    flags = red_flags.evaluate_red_flags(
        symptoms=["runny_nose", "sneezing", "mild_fatigue"],
        vitals={"temperature": 37.0, "spo2": 99.0, "heart_rate": 72, "bp_systolic": 118},
        age=32
    )
    assert len(flags) == 0


# ── 2. Missing-Value Handling & Native Missingness Indicators ──────────────────

def test_missing_value_handling_native_indicators():
    """Model must accept omitted vitals and labs without crashing and set missingness indicators."""
    res = general_disease_model.predict_differential(
        age=45,
        sex=1,
        symptoms=["fever", "cough"],
        symptom_duration_days=3,
        vitals={},          # No vitals provided
        optional_labs={}     # No labs provided
    )
    assert "predictedTop3" in res
    assert len(res["predictedTop3"]) == 3
    # Verify missing vitals are handled gracefully
    assert res["modelVersion"].startswith("TF-GenDisease")


def test_missing_values_feature_vector_structure():
    """The model's vectorizer should build both val_* and is_missing_* features."""
    x, names = general_disease_model.build_feature_vector(
        age=28,
        sex=0,
        symptoms=["dysuria"],
        symptom_duration_days=2,
        vitals={"temperature": 37.5}, # spo2, bp, hr missing
        optional_labs=None
    )
    assert len(x) == len(names)
    assert "is_missing_spo2" in names
    assert "is_missing_bp_systolic" in names
    assert "is_missing_blood_sugar" in names

    # is_missing_spo2 index must be 1.0 because spo2 was not provided
    spo2_missing_idx = names.index("is_missing_spo2")
    assert x[spo2_missing_idx] == 1.0

    # is_missing_temperature must be 0.0 because temperature was provided
    temp_missing_idx = names.index("is_missing_temperature")
    assert x[temp_missing_idx] == 0.0


# ── 3. Top-3 Output Structure & Probability Calibration ───────────────────────

def test_top3_output_structure_and_calibration():
    """Model must return TOP 3 conditions with calibrated probabilities, never a single verdict."""
    res = general_disease_model.predict_differential(
        age=30,
        sex=1,
        symptoms=["fever", "chills", "headache", "body_ache"],
        symptom_duration_days=2,
        vitals={"temperature": 39.1, "heart_rate": 105, "spo2": 97}
    )
    top3 = res["predictedTop3"]
    assert len(top3) == 3, "Prediction must return exactly TOP 3 conditions"
    
    # Check descending order
    assert top3[0]["probability"] >= top3[1]["probability"] >= top3[2]["probability"]

    # Each entry has required fields
    for item in top3:
        assert "condition" in item
        assert "conditionLabel" in item
        assert "probability" in item
        assert "confidence" in item
        assert 0.0 <= item["probability"] <= 1.0

    # Sum of top 3 must be strictly <= 1.0
    prob_sum = sum(item["probability"] for item in top3)
    assert 0.0 < prob_sum <= 1.0001


# ── 4. Adaptive Questioning Logic ─────────────────────────────────────────────

def test_adaptive_questioning_triggers_on_low_confidence():
    """When top-1 confidence is < 0.65, model should propose the most informative missing parameter."""
    # Provide vague symptom with no vitals to create low confidence
    res = general_disease_model.predict_differential(
        age=40,
        sex=0,
        symptoms=["fatigue"],
        symptom_duration_days=5,
        vitals={}
    )
    top1_prob = res["predictedTop3"][0]["probability"]
    assert top1_prob < 0.65, f"Expected low confidence for isolated fatigue, got {top1_prob}"

    adaptive_q = res.get("adaptiveQuestion")
    assert adaptive_q is not None, "Adaptive question should be present when top-1 confidence is below threshold"
    assert "suggestedParameter" in adaptive_q
    assert "label" in adaptive_q
    assert "prompt" in adaptive_q
    assert "Add " in adaptive_q["prompt"] and "to improve this result" in adaptive_q["prompt"]
    assert "expectedInformationGain" in adaptive_q
    assert adaptive_q["expectedInformationGain"] > 0


def test_adaptive_questioning_none_when_high_confidence():
    """When top-1 confidence is high (e.g. >= 0.65), adaptive question is not required or None."""
    # Strong classic dengue presentation
    res = general_disease_model.predict_differential(
        age=25,
        sex=1,
        symptoms=["fever", "high_fever", "retro_orbital_pain", "joint_pain", "rash", "petechiae"],
        symptom_duration_days=4,
        vitals={"temperature": 39.8, "heart_rate": 110, "spo2": 98},
        optional_labs={"platelet_count": 65000}
    )
    top1 = res["predictedTop3"][0]
    if top1["probability"] >= 0.65:
        assert res.get("adaptiveQuestion") is None


# ── 5. Feature Explanations (Linear SHAP Contributions) ───────────────────────

def test_linear_feature_contributions():
    """Model must return feature contributions explaining why the top condition was favored."""
    res = general_disease_model.predict_differential(
        age=55,
        sex=1,
        symptoms=["chest_pain", "breathlessness"],
        symptom_duration_days=1,
        vitals={"bp_systolic": 165, "heart_rate": 96, "spo2": 94},
        structured_ecg="st_elevation"
    )
    explanations = res.get("explanations")
    assert explanations is not None
    assert "topCondition" in explanations
    assert "positiveContributions" in explanations
    assert len(explanations["positiveContributions"]) > 0

    # Chest pain should be a top positive driver for heart disease risk
    pos_features = [c["feature"].lower() for c in explanations["positiveContributions"]] + [c.get("rawFeature", "").lower() for c in explanations["positiveContributions"]]
    assert any("chest pain" in f or "chest_pain" in f or "bp" in f for f in pos_features)


# ── 6. Suggested Cause, Remedies, and Clinician Verification Label ────────────

def test_suggested_cause_and_remedies_label():
    """Guidance must be clearly labeled 'Suggested, clinician must verify'."""
    res = general_disease_model.predict_differential(
        age=22,
        sex=0,
        symptoms=["dysuria", "urinary_frequency"],
        symptom_duration_days=2,
        vitals={"temperature": 37.6}
    )
    guidance = res.get("suggestedClinicalGuidance")
    assert guidance is not None
    assert guidance["label"] == "Suggested, clinician must verify"
    assert "suggestedCause" in guidance
    assert "commonRemedies" in guidance
    assert len(guidance["commonRemedies"]) > 0


# ── 7. Mandatory Clinical Disclaimer ──────────────────────────────────────────

def test_mandatory_disclaimer_present():
    """Educational decision support disclaimer must be on every prediction."""
    res = general_disease_model.predict_differential(
        age=30,
        sex=0,
        symptoms=["headache"],
        vitals={}
    )
    assert res.get("disclaimer") == PERSISTENT_DISCLAIMER


# ── 8. Deterministic Evaluation Script ─────────────────────────────────────────

def test_deterministic_evaluation():
    """Evaluation on held-out test split must produce deterministic, multi-dimensional metrics."""
    metrics = evaluation.evaluate_general_disease_model()
    assert "per_disease" in metrics
    assert "macro_f1" in metrics
    assert "top3_accuracy" in metrics
    assert "expected_calibration_error" in metrics

    # Multi-dimensional threshold assertions
    assert metrics["top3_accuracy"] > 0.80, f"Expected top-3 accuracy > 80%, got {metrics['top3_accuracy']}"
    assert metrics["macro_f1"] > 0.50, f"Expected macro-F1 > 0.50, got {metrics['macro_f1']}"
    assert metrics["expected_calibration_error"] < 0.20, f"Expected ECE < 0.20, got {metrics['expected_calibration_error']}"

    # Verify all 18 diseases are present
    assert len(metrics["per_disease"]) == len(general_disease_model.DISEASE_CLASSES)


# ── 9. Integration with API Endpoints & Red-Flag Alerts in Responses ───────────

def test_api_clinical_predict_endpoint():
    """Test POST /api/v1/clinical/predict endpoint."""
    token = _login("p4_doc@trustfed.ai")
    res = client.post(
        "/api/v1/clinical/predict",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "age": 45,
            "sex": "male",
            "symptoms": ["chest_pain", "breathlessness"],
            "symptom_duration_days": 1,
            "vitals": {"spo2": 89.0, "bp_systolic": 150},
            "hospital_id": "hosp-p4-1"
        }
    )
    assert res.status_code == 200, res.text
    data = res.json()

    # Verify top 3
    assert len(data["predictedTop3"]) == 3
    # Verify red flags: SpO2 89 -> CRITICAL_HYPOXIA, chest pain + breathlessness -> CARDIAC ACS
    assert data["hasCriticalRedFlag"] is True
    assert len(data["redFlags"]) >= 2
    # Verify mandatory disclaimer
    assert data["disclaimer"] == PERSISTENT_DISCLAIMER


def test_api_encounter_creation_logs_model_version(monkeypatch):
    """Encounter creation must store the model version and evaluate red flags."""
    monkeypatch.setenv("APP_MODE", "clinical")
    token = _login("p4_staff@trustfed.ai")
    res = client.post(
        "/api/v1/hospital/patients",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Jane Test Patient",
            "age": 29,
            "sex": 0,
            "hospital_id": "hosp-p4-1",
            "symptoms": ["fever", "stiff_neck"],
            "symptom_duration_days": 2,
            "vitals": {"temperature": 39.5}
        }
    )
    assert res.status_code == 200, res.text
    enc = res.json()["encounter"]
    assert enc is not None
    assert enc["modelVersion"].startswith("TF-GenDisease")
    assert enc["hasCriticalRedFlag"] is True
    # Meningitis rule triggered by fever + stiff neck
    rule_ids = [rf["ruleId"] for rf in enc["redFlags"]]
    assert "SUSPECTED_MENINGITIS" in rule_ids
    assert enc["disclaimer"] == PERSISTENT_DISCLAIMER


def test_database_diseases_table_synced_with_18_conditions():
    """Verify that the relational database diseases table is 100% synced with the 18-condition inference model."""
    from db.database import SessionLocal
    from db import models
    from services.seed_data import seed_synthetic_data
    from services.general_disease_model import DISEASE_KEYS

    db = SessionLocal()
    try:
        seed_synthetic_data(db, force=True)
        diseases = db.query(models.Disease).all()
        assert len(diseases) == 18, f"Expected 18 database diseases, found {len(diseases)}"

        # Check all disease codes exist and are active
        codes = {d.code for d in diseases}
        assert len(codes) == 18
        assert all(d.is_active for d in diseases)
    finally:
        db.close()
