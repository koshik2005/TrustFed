"""Phase E Test Suite: Model Honesty, Statistics, Promotion Gate, and 33-Scenario Safety Suite.

Tests:
1. Bootstrap 95% Confidence Intervals for Top-1, Top-3, Macro-F1, Precision, Recall, ECE.
2. Per-disease sample counts and explicit 'low confidence' flag (< 20 samples).
3. Promotion Gate:
   - Tiny gains with CI_lower <= 0 are REJECTED.
   - Per-disease regressions beyond tolerance are REJECTED.
   - Fairness degradation is REJECTED.
   - Clear statistically significant gain is ACCEPTED.
4. Single Source of Truth Red-Flag Constants & 'pending physician review' labels.
5. 33 Clinically Common Scenarios (emergencies: ACS, Hypoxia, Stroke, Meningitis, Infant Fever,
   Dehydration Shock, Hypertensive Crisis, Bradycardia) that MUST ALWAYS trigger red flags.
6. API endpoint verification for /api/v1/model/info and /api/v1/clinical/predict.
"""
from __future__ import annotations
import os
import sys
import numpy as np
import pytest
from fastapi.testclient import TestClient

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from db.database import engine, SessionLocal, Base
from db import models
from services import auth, crypto
from core.red_flag_constants import (
    STATUS_LABEL,
    HYPOXIA_SPO2_THRESHOLD,
    TACHYCARDIA_HR_THRESHOLD,
    BRADYCARDIA_HR_THRESHOLD,
    HYPOTENSION_SYSTOLIC_BP_THRESHOLD,
    HYPERTENSIVE_CRISIS_SYSTOLIC_BP,
    HYPERTENSIVE_CRISIS_DIASTOLIC_BP,
    ADULT_FEVER_TEMP_C,
    INFANT_FEVER_TEMP_C,
    INFANT_MAX_AGE_YEARS,
    RED_FLAG_DEFINITIONS
)
from services.red_flags import evaluate_red_flags
from services.general_disease_model import (
    GeneralDiseaseModel,
    predict_differential,
    DISEASE_KEYS,
    MODEL_VERSION,
)
from services.evaluation import run_evaluation
from services.promotion_gate import evaluate_promotion_gate


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        hub = db.query(models.RegionalHub).filter_by(id="hub-phase-e").first()
        if not hub:
            hub = models.RegionalHub(id="hub-phase-e", name="Hub Phase E", region="Central", status="active")
            db.add(hub)

        hosp = db.query(models.Hospital).filter_by(id="hosp-phase-e").first()
        if not hosp:
            hosp = models.Hospital(id="hosp-phase-e", name="Hospital Phase E", hub_id="hub-phase-e", status="active", share_deidentified=True)
            db.add(hosp)

        user = db.query(models.User).filter_by(email="phase_e_doc@trustfed.ai").first()
        if not user:
            db.add(models.User(
                email="phase_e_doc@trustfed.ai",
                name="Dr. Phase E",
                role="doctor",
                hospital_id="hosp-phase-e",
                hub_id=None,
                password_hash=auth.hash_password("DemoPassword123!"),
                must_reset_password=False,
                status="active"
            ))
        db.commit()
    finally:
        db.close()


# ==============================================================================
# 1. BOOTSTRAP 95% CONFIDENCE INTERVALS & SAMPLE AUDIT
# ==============================================================================

class TestModelStatisticsAndBootstrapCI:
    """Verifies bootstrap 95% confidence intervals and sample support audit."""

    @classmethod
    def setup_class(cls):
        # Run evaluation with B=200 for fast test suite execution
        cls.report = run_evaluation(seed=42, n_bootstrap=200)

    def test_bootstrap_intervals_present_and_ordered(self):
        r = self.report
        assert "top1Accuracy_ci_95" in r
        assert "top3Accuracy_ci_95" in r
        assert "macroF1_ci_95" in r
        assert "expectedCalibrationError_ci_95" in r

        # CI bounds must be ordered: lower <= upper
        assert r["top1Accuracy_ci_95"][0] <= r["top1Accuracy_ci_95"][1]
        assert r["top3Accuracy_ci_95"][0] <= r["top3Accuracy_ci_95"][1]
        assert r["macroF1_ci_95"][0] <= r["macroF1_ci_95"][1]
        assert r["expectedCalibrationError_ci_95"][0] <= r["expectedCalibrationError_ci_95"][1]

        # Point estimates must fall inside or at boundaries of their 95% CIs
        assert r["top1Accuracy_ci_95"][0] <= r["top1Accuracy"] <= r["top1Accuracy_ci_95"][1]
        assert r["top3Accuracy_ci_95"][0] <= r["top3Accuracy"] <= r["top3Accuracy_ci_95"][1]

    def test_all_diseases_with_under_20_samples_flagged_low_confidence(self):
        """Phase E rule: flag any disease with < 20 test samples as 'low confidence'."""
        r = self.report
        per_disease = r["perDisease"]
        assert len(per_disease) == 18

        for code, info in per_disease.items():
            support = info["support"]
            assert support == info["sample_count"]
            if support < 20:
                assert info["low_confidence"] is True
                assert "low confidence" in info["confidence_tier"]
            else:
                assert info["low_confidence"] is False

    def test_calibration_bins_and_ece(self):
        r = self.report
        assert r["expectedCalibrationError"] > 0.0
        assert len(r["calibrationBins"]) > 0
        for b in r["calibrationBins"]:
            assert "bin" in b
            assert "count" in b
            assert "confidence" in b
            assert "accuracy" in b
            assert "calibrationGap" in b


# ==============================================================================
# 2. PROMOTION GATE: STATISTICAL CI, REGRESSION, FAIRNESS GATING
# ==============================================================================

class TestPromotionGate:
    """Verifies promotion gate logic."""

    def setup_method(self):
        np.random.seed(42)
        self.n = 200
        self.k = 5
        self.y_true = np.random.randint(0, self.k, size=self.n)
        self.base_preds = self.y_true.copy()
        # Baseline has 70% accuracy
        corrupt_idx = np.random.choice(self.n, size=int(0.30 * self.n), replace=False)
        self.base_preds[corrupt_idx] = (self.base_preds[corrupt_idx] + 1) % self.k

    def test_tiny_gain_ci_lower_crosses_zero_is_rejected(self):
        """When candidate only improves 1-2 samples, CI_lower <= 0, promotion MUST be rejected."""
        cand_preds = self.base_preds.copy()
        # Improve just 1 sample
        wrong_idx = np.where(self.base_preds != self.y_true)[0]
        cand_preds[wrong_idx[0]] = self.y_true[wrong_idx[0]]

        gate = evaluate_promotion_gate(
            candidate_preds=cand_preds,
            baseline_preds=self.base_preds,
            ground_truth=self.y_true,
            n_bootstrap=500,
            random_seed=42
        )

        assert gate["promoted"] is False
        assert gate["status"] == "REJECTED_BY_PROMOTION_GATE"
        assert gate["macro_f1"]["ci_lower"] <= 0.0
        assert gate["macro_f1"]["passed"] is False

    def test_clear_statistically_significant_gain_is_accepted(self):
        """When candidate has a clear large gain across all classes, CI_lower > 0, it is promoted."""
        cand_preds = self.base_preds.copy()
        # Fix 80% of errors
        wrong_idx = np.where(self.base_preds != self.y_true)[0]
        to_fix = wrong_idx[:int(0.80 * len(wrong_idx))]
        cand_preds[to_fix] = self.y_true[to_fix]

        gate = evaluate_promotion_gate(
            candidate_preds=cand_preds,
            baseline_preds=self.base_preds,
            ground_truth=self.y_true,
            n_bootstrap=500,
            random_seed=42
        )

        assert gate["promoted"] is True
        assert gate["status"] == "APPROVED_FOR_PROMOTION"
        assert gate["macro_f1"]["ci_lower"] > 0.0
        assert gate["macro_f1"]["passed"] is True
        assert gate["per_disease"]["passed"] is True

    def test_per_disease_regression_beyond_tolerance_is_rejected(self):
        """Even if overall macro-F1 is higher, severe regression in any single class causes rejection."""
        cand_preds = self.base_preds.copy()
        # Fix many errors in class 0 and 1
        wrong_idx = np.where(self.base_preds != self.y_true)[0]
        cand_preds[wrong_idx[:30]] = self.y_true[wrong_idx[:30]]
        # But artificially ruin class 2 completely
        class2_idx = np.where(self.y_true == 2)[0]
        cand_preds[class2_idx] = 0  # Corrupt all class 2 samples

        gate = evaluate_promotion_gate(
            candidate_preds=cand_preds,
            baseline_preds=self.base_preds,
            ground_truth=self.y_true,
            n_bootstrap=500,
            per_disease_tolerance=0.02,
            random_seed=42
        )

        assert gate["promoted"] is False
        assert gate["per_disease"]["passed"] is False
        assert gate["per_disease"]["regressed_classes_count"] > 0

    def test_fairness_degradation_is_rejected(self):
        """Candidate that degrades demographic parity beyond tolerance is rejected."""
        # Balanced baseline: equal errors in both groups -> disparity = 0.0
        sensitive = np.array([0] * (self.n // 2) + [1] * (self.n // 2))
        base_preds = self.y_true.copy()
        g0 = np.where(sensitive == 0)[0]
        g1 = np.where(sensitive == 1)[0]
        base_preds[g0[:20]] = (self.y_true[g0[:20]] + 1) % self.k
        base_preds[g1[:20]] = (self.y_true[g1[:20]] + 1) % self.k

        cand_preds = base_preds.copy()
        # Corrupt 20 more samples exclusively in group 1
        cand_preds[g1[20:40]] = (self.y_true[g1[20:40]] + 1) % self.k

        gate = evaluate_promotion_gate(
            candidate_preds=cand_preds,
            baseline_preds=base_preds,
            ground_truth=self.y_true,
            sensitive_attr=sensitive,
            n_bootstrap=500,
            fairness_tolerance=0.01,
            random_seed=42
        )

        assert gate["promoted"] is False
        assert gate["fairness"]["passed"] is False
        assert gate["fairness"]["delta_disparity"] > 0.01


# ==============================================================================
# 3. RED-FLAG CONSTANTS & CANONICAL AUDIT
# ==============================================================================

class TestRedFlagConstantsAndLabels:
    """Verifies single source of truth for red flags and consistent labeling."""

    def test_constants_defined_and_status_label(self):
        assert STATUS_LABEL == "pending physician review"
        assert HYPOXIA_SPO2_THRESHOLD == 92.0
        assert TACHYCARDIA_HR_THRESHOLD == 120.0
        assert BRADYCARDIA_HR_THRESHOLD == 40.0
        assert HYPOTENSION_SYSTOLIC_BP_THRESHOLD == 90.0
        assert HYPERTENSIVE_CRISIS_SYSTOLIC_BP == 180.0
        assert HYPERTENSIVE_CRISIS_DIASTOLIC_BP == 120.0
        assert ADULT_FEVER_TEMP_C == 38.0
        assert INFANT_FEVER_TEMP_C == 38.5
        assert INFANT_MAX_AGE_YEARS == 1

    def test_all_rule_definitions_contain_pending_physician_review(self):
        assert len(RED_FLAG_DEFINITIONS) >= 8
        for r in RED_FLAG_DEFINITIONS:
            assert r["status"] == STATUS_LABEL
            assert r["severity"] == "CRITICAL"
            assert "escalation_action" in r


# ==============================================================================
# 4. SAFETY SUITE: 33 CLINICALLY COMMON SCENARIOS
# ==============================================================================

class TestClinicalSafetySuite33Scenarios:
    """At least 30 clinically common emergency scenarios that must ALWAYS trigger red flags."""

    # 1. ACS: chest pain + diaphoresis
    def test_scenario_01_acs_chest_pain_sweating(self):
        alerts = evaluate_red_flags(symptoms=["chest_pain", "sweating"])
        assert any(a.rule_id == "CARDIAC_ACUTE_CORONARY_SYNDROME" for a in alerts)
        assert "Pending Physician Review" in alerts[0].title

    # 2. ACS: chest pain + dyspnea / breathlessness
    def test_scenario_02_acs_chest_pain_dyspnea(self):
        alerts = evaluate_red_flags(symptoms=["chest_pain", "dyspnea"])
        assert any(a.rule_id == "CARDIAC_ACUTE_CORONARY_SYNDROME" for a in alerts)

    # 3. ACS: chest pain + tachycardia (HR 125)
    def test_scenario_03_acs_chest_pain_tachycardia(self):
        alerts = evaluate_red_flags(symptoms=["chest_pain"], vitals={"hr": 125})
        assert any(a.rule_id == "CARDIAC_ACUTE_CORONARY_SYNDROME" for a in alerts)

    # 4. ACS: chest pain + ST elevation on ECG
    def test_scenario_04_acs_chest_pain_st_change(self):
        alerts = evaluate_red_flags(symptoms=["chest_pain"], structured_ecg="st_change")
        assert any(a.rule_id == "CARDIAC_ACUTE_CORONARY_SYNDROME" for a in alerts)

    # 5. ACS: chest pain + breathlessness (synonym)
    def test_scenario_05_acs_chest_pain_breathlessness(self):
        alerts = evaluate_red_flags(symptoms=["chest_pain", "breathlessness"])
        assert any(a.rule_id == "CARDIAC_ACUTE_CORONARY_SYNDROME" for a in alerts)

    # 6. Hypoxia: SpO2 = 88%
    def test_scenario_06_hypoxia_severe(self):
        alerts = evaluate_red_flags(vitals={"spo2": 88})
        assert any(a.rule_id == "CRITICAL_HYPOXIA" for a in alerts)

    # 7. Hypoxia: SpO2 = 91% (borderline critical)
    def test_scenario_07_hypoxia_borderline(self):
        alerts = evaluate_red_flags(vitals={"spo2": 91})
        assert any(a.rule_id == "CRITICAL_HYPOXIA" for a in alerts)

    # 8. Hypoxia: Cough + fever + SpO2 = 86%
    def test_scenario_08_hypoxia_with_respiratory_symptoms(self):
        alerts = evaluate_red_flags(symptoms=["cough", "fever"], vitals={"spo2": 86})
        assert any(a.rule_id == "CRITICAL_HYPOXIA" for a in alerts)

    # 9. Hypoxia: SpO2 via oximeter alias = 89%
    def test_scenario_09_hypoxia_alias_oximeter(self):
        alerts = evaluate_red_flags(vitals={"oxygen_saturation": 89})
        assert any(a.rule_id == "CRITICAL_HYPOXIA" for a in alerts)

    # 10. Stroke FAST: Facial droop
    def test_scenario_10_stroke_facial_droop(self):
        alerts = evaluate_red_flags(symptoms=["facial_droop"])
        assert any(a.rule_id == "ACUTE_STROKE_FAST" for a in alerts)

    # 11. Stroke FAST: Arm weakness
    def test_scenario_11_stroke_arm_weakness(self):
        alerts = evaluate_red_flags(symptoms=["arm_weakness"])
        assert any(a.rule_id == "ACUTE_STROKE_FAST" for a in alerts)

    # 12. Stroke FAST: Slurred speech
    def test_scenario_12_stroke_slurred_speech(self):
        alerts = evaluate_red_flags(symptoms=["slurred_speech"])
        assert any(a.rule_id == "ACUTE_STROKE_FAST" for a in alerts)

    # 13. Stroke FAST: Speech difficulty alias
    def test_scenario_13_stroke_speech_difficulty(self):
        alerts = evaluate_red_flags(symptoms=["speech_difficulty"])
        assert any(a.rule_id == "ACUTE_STROKE_FAST" for a in alerts)

    # 14. Stroke FAST: Limb weakness
    def test_scenario_14_stroke_limb_weakness(self):
        alerts = evaluate_red_flags(symptoms=["limb_weakness"])
        assert any(a.rule_id == "ACUTE_STROKE_FAST" for a in alerts)

    # 15. Meningitis: Fever + stiff neck
    def test_scenario_15_meningitis_fever_stiff_neck(self):
        alerts = evaluate_red_flags(symptoms=["fever", "stiff_neck"])
        assert any(a.rule_id == "SUSPECTED_MENINGITIS" for a in alerts)

    # 16. Meningitis: Neck stiffness + Temp >= 38.0 C
    def test_scenario_16_meningitis_pyrexia_neck_stiffness(self):
        alerts = evaluate_red_flags(symptoms=["neck_stiffness"], vitals={"temp_c": 38.8})
        assert any(a.rule_id == "SUSPECTED_MENINGITIS" for a in alerts)

    # 17. Meningitis: High fever symptom + stiff neck
    def test_scenario_17_meningitis_high_fever_stiff_neck(self):
        alerts = evaluate_red_flags(symptoms=["high_fever", "stiff_neck"])
        assert any(a.rule_id == "SUSPECTED_MENINGITIS" for a in alerts)

    # 18. Infant Fever: Age 0 (6 months), Temp = 39.0 C
    def test_scenario_18_infant_fever_6_months(self):
        alerts = evaluate_red_flags(age=0, vitals={"temp_c": 39.0})
        assert any(a.rule_id == "INFANT_HIGH_FEVER_SEPSIS_RISK" for a in alerts)

    # 19. Infant Fever: Age 1 (12 months), Temp = 38.6 C
    def test_scenario_19_infant_fever_12_months(self):
        alerts = evaluate_red_flags(age=1, vitals={"temp_c": 38.6})
        assert any(a.rule_id == "INFANT_HIGH_FEVER_SEPSIS_RISK" for a in alerts)

    # 20. Infant Fever: Age 0, symptom high_fever
    def test_scenario_20_infant_high_fever_symptom(self):
        alerts = evaluate_red_flags(age=0, symptoms=["high_fever"])
        assert any(a.rule_id == "INFANT_HIGH_FEVER_SEPSIS_RISK" for a in alerts)

    # 21. Infant Fever: Age 1, Fahrenheit temperature 103.1 F (= 39.5 C)
    def test_scenario_21_infant_fever_fahrenheit_conversion(self):
        alerts = evaluate_red_flags(age=1, vitals={"temperature": 103.1})
        assert any(a.rule_id == "INFANT_HIGH_FEVER_SEPSIS_RISK" for a in alerts)

    # 22. Dehydration Shock: Vomiting + systolic BP 84 mmHg
    def test_scenario_22_dehydration_vomiting_hypotension(self):
        alerts = evaluate_red_flags(symptoms=["vomiting"], vitals={"bp_sys": 84})
        assert any(a.rule_id == "SEVERE_DEHYDRATION_SHOCK" for a in alerts)

    # 23. Dehydration Shock: Diarrhea + tachycardia (HR 130)
    def test_scenario_23_dehydration_diarrhea_tachycardia(self):
        alerts = evaluate_red_flags(symptoms=["diarrhea"], vitals={"hr": 130})
        assert any(a.rule_id == "SEVERE_DEHYDRATION_SHOCK" for a in alerts)

    # 24. Dehydration Shock: Vomiting + dizziness
    def test_scenario_24_dehydration_vomiting_dizziness(self):
        alerts = evaluate_red_flags(symptoms=["vomiting", "dizziness"])
        assert any(a.rule_id == "SEVERE_DEHYDRATION_SHOCK" for a in alerts)

    # 25. Dehydration Shock: Diarrhea + lethargy
    def test_scenario_25_dehydration_diarrhea_lethargy(self):
        alerts = evaluate_red_flags(symptoms=["diarrhea", "lethargy"])
        assert any(a.rule_id == "SEVERE_DEHYDRATION_SHOCK" for a in alerts)

    # 26. Hypertensive Crisis: Systolic BP 190 mmHg
    def test_scenario_26_hypertensive_crisis_systolic(self):
        alerts = evaluate_red_flags(vitals={"bp_sys": 190})
        assert any(a.rule_id == "HYPERTENSIVE_CRISIS" for a in alerts)

    # 27. Hypertensive Crisis: Diastolic BP 125 mmHg
    def test_scenario_27_hypertensive_crisis_diastolic(self):
        alerts = evaluate_red_flags(vitals={"bp_dia": 125})
        assert any(a.rule_id == "HYPERTENSIVE_CRISIS" for a in alerts)

    # 28. Hypertensive Crisis: BP 200/130 mmHg + severe headache
    def test_scenario_28_hypertensive_crisis_dual(self):
        alerts = evaluate_red_flags(symptoms=["headache"], vitals={"bp_sys": 200, "bp_dia": 130})
        assert any(a.rule_id == "HYPERTENSIVE_CRISIS" for a in alerts)

    # 29. Critical Bradycardia: HR 36 bpm
    def test_scenario_29_critical_bradycardia(self):
        alerts = evaluate_red_flags(vitals={"hr": 36})
        assert any(a.rule_id == "CRITICAL_BRADYCARDIA_SHOCK" for a in alerts)

    # 30. Critical Bradycardia: HR 32 bpm + dizziness
    def test_scenario_30_bradycardia_with_dizziness(self):
        alerts = evaluate_red_flags(symptoms=["dizziness"], vitals={"hr": 32})
        assert any(a.rule_id == "CRITICAL_BRADYCARDIA_SHOCK" for a in alerts)

    # 31. Dual Emergency: ACS + Hypoxemia
    def test_scenario_31_dual_acs_and_hypoxia(self):
        alerts = evaluate_red_flags(symptoms=["chest_pain", "sweating"], vitals={"spo2": 89})
        rule_ids = {a.rule_id for a in alerts}
        assert "CARDIAC_ACUTE_CORONARY_SYNDROME" in rule_ids
        assert "CRITICAL_HYPOXIA" in rule_ids

    # 32. Dual Emergency: Stroke Signs + Hypertensive Crisis
    def test_scenario_32_dual_stroke_and_hypertensive_crisis(self):
        alerts = evaluate_red_flags(symptoms=["facial_droop"], vitals={"bp_sys": 195, "bp_dia": 122})
        rule_ids = {a.rule_id for a in alerts}
        assert "ACUTE_STROKE_FAST" in rule_ids
        assert "HYPERTENSIVE_CRISIS" in rule_ids

    # 33. Model Masking Resistance: Ambulatory Cold presentation with masked hypoxia (SpO2 88%)
    def test_scenario_33_model_masking_resistance(self):
        """Even if ambulatory symptoms predict common_cold, red flags must trigger and dominate."""
        res = predict_differential(
            age=32,
            sex=1,
            symptoms=["runny_nose", "cough", "sneezing"],
            vitals={"spo2": 88}
        )
        assert res["hasCriticalRedFlag"] is True
        assert len(res["redFlags"]) >= 1
        assert res["redFlags"][0]["ruleId"] == "CRITICAL_HYPOXIA"


# ==============================================================================
# 5. ENDPOINT VERIFICATION: /model/info & /clinical/predict
# ==============================================================================

class TestModelEndpoints:
    """Verifies Phase E contract on HTTP endpoints."""

    def test_model_info_endpoint(self, client):
        resp = client.get("/api/v1/model/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "evaluation" in data
        eval_data = data["evaluation"]
        assert eval_data["modelVersion"] == MODEL_VERSION
        assert "macroF1_ci_95" in eval_data
        assert "top1Accuracy_ci_95" in eval_data
        assert "top3Accuracy_ci_95" in eval_data
        assert "expectedCalibrationError_ci_95" in eval_data
        assert "perDisease" in eval_data
        assert "Educational decision support" in data["disclaimer"]

    def test_clinical_predict_result_contract(self, client):
        token = auth.create_token({
            "sub": "phase_e_doc@trustfed.ai",
            "role": "doctor",
            "hospital_id": "hosp-phase-e"
        })
        payload = {
            "age": 45,
            "sex": 1,
            "symptoms": ["cough", "fever", "breathlessness"],
            "vitals": {"spo2": 95, "temperature": 99.4}
        }
        resp = client.post(
            "/api/v1/clinical/predict",
            headers={"Authorization": f"Bearer {token}"},
            json=payload
        )
        assert resp.status_code == 200
        res = resp.json()

        # Phase E required fields on result
        assert res["modelVersion"] == MODEL_VERSION
        assert "datasetOrigin" in res
        assert "prototypeBenchmarkLabel" in res
        assert "predictedTop3" in res
        assert len(res["predictedTop3"]) == 3
        assert "disclaimer" in res
        assert "Educational decision support" in res["disclaimer"]
        assert "adaptiveHint" in res or "adaptiveQuestion" in res
