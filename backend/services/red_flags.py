"""Clinical Red-Flag Safety Rules Engine.

Deterministic safety guardrails that evaluate high-acuity presenting signs and symptoms.
When triggered, red-flag alerts override routine ambulatory models and provide immediate
urgent clinical escalation guidance.

CLINICAL DISCLAIMER & THRESHOLD AUDIT:
--------------------------------------
All numerical thresholds (SpO2 < 92%, HR >= 120 bpm, Systolic BP < 90 mmHg, Temp >= 38.0/38.5 C)
are conservative prototype heuristics labeled "PENDING PHYSICIAN REVIEW".
They have NOT been validated by clinical trials and do NOT substitute for formal triage by
a licensed medical professional. Tachycardia (HR >= 120) is considered in conjunction with
concurrent physiological indicators (e.g. acute fluid loss, diaphoresis, hypotension, or dyspnea).
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


class RedFlagAlert:
    def __init__(self, rule_id: str, severity: str, title: str, description: str, escalation_action: str):
        self.rule_id = rule_id
        self.severity = severity  # "CRITICAL" | "HIGH"
        self.title = title if "[Pending Physician Review]" in title else f"{title} [Pending Physician Review]"
        self.description = description
        self.escalation_action = escalation_action

    def __getitem__(self, key: str):
        d = self.to_dict()
        if key in d:
            return d[key]
        if key == "action":
            return self.escalation_action
        if key == "rule_id":
            return self.rule_id
        raise KeyError(key)

    def to_dict(self) -> Dict[str, str]:
        return {
            "ruleId": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "escalationAction": self.escalation_action,
            "action": self.escalation_action,
            "evidence": self.description,
        }


def normalize_symptom_set(symptoms: List[str]) -> set[str]:
    return {s.strip().lower().replace(" ", "_").replace("-", "_") for s in symptoms if s and isinstance(s, str)}


def evaluate_red_flags(
    age: Optional[int] = None,
    symptoms: Optional[List[str]] = None,
    vitals: Optional[Dict[str, Any]] = None,
    structured_ecg: Optional[str] = None
) -> List[RedFlagAlert]:
    """Evaluates mandatory clinical safety red-flag rules against presenting features."""
    if symptoms is None:
        symptoms = []
    if vitals is None:
        vitals = {}

    clean_symptoms = normalize_symptom_set(symptoms)
    alerts: List[RedFlagAlert] = []

    # Extract vitals safely with aliases
    temp_c = None
    for k in ("temp_c", "temperature", "temp"):
        if k in vitals and vitals[k] not in (None, ""):
            try:
                t = float(vitals[k])
                if t > 50:
                    t = (t - 32) * 5 / 9
                temp_c = t
                break
            except (ValueError, TypeError): pass

    bp_sys = None
    for k in ("bp_sys", "bp_systolic", "systolic", "blood_pressure_systolic"):
        if k in vitals and vitals[k] not in (None, ""):
            try:
                bp_sys = float(vitals[k])
                break
            except (ValueError, TypeError): pass

    hr = None
    for k in ("hr", "heart_rate", "pulse"):
        if k in vitals and vitals[k] not in (None, ""):
            try:
                hr = float(vitals[k])
                break
            except (ValueError, TypeError): pass

    spo2 = None
    for k in ("spo2", "oximeter", "oxygen_saturation"):
        if k in vitals and vitals[k] not in (None, ""):
            try:
                spo2 = float(vitals[k])
                break
            except (ValueError, TypeError): pass

    clean_ecg = str(structured_ecg).lower().strip() if structured_ecg else ""

    # Rule 1: Chest pain with diaphoresis (sweating) or breathlessness or ST change
    # Note: Tachycardia (HR >= 120) requires concurrent chest pain (dual sign requirement)
    has_chest_pain = "chest_pain" in clean_symptoms
    has_cardiac_assoc = (
        "sweating" in clean_symptoms
        or "breathlessness" in clean_symptoms
        or "dyspnea" in clean_symptoms
        or (hr is not None and hr >= 120)  # Tachycardia coupled with presenting chest pain
        or ("st_change" in clean_ecg or "st_depression" in clean_ecg)
    )
    if has_chest_pain and has_cardiac_assoc:
        alerts.append(RedFlagAlert(
            rule_id="CARDIAC_ACUTE_CORONARY_SYNDROME",
            severity="CRITICAL",
            title="Suspected Acute Coronary Syndrome (ACS) / Myocardial Infarction",
            description="Patient presents with acute chest pain accompanied by autonomic signs (sweating, breathlessness, tachycardia, or ST-segment deviation).",
            escalation_action="Immediate 12-lead ECG stat, troponin assay, continuous cardiac monitoring, and emergency transfer to interventional cardiology / ED."
        ))

    # Rule 2: Critical Hypoxemia (SpO2 < 92%)
    if spo2 is not None and spo2 < 92.0:
        alerts.append(RedFlagAlert(
            rule_id="CRITICAL_HYPOXIA",
            severity="CRITICAL",
            title="Severe Hypoxemic Respiratory Failure (SpO2 < 92%)",
            description=f"Measured peripheral oxygen saturation is dangerously low ({spo2}%). Indicates acute alveolar consolidation or ventilation-perfusion mismatch.",
            escalation_action="Initiate supplemental high-flow oxygen immediately. Evaluate for severe pneumonia, acute asthma exacerbation, or pulmonary embolism."
        ))

    # Rule 3: Acute Stroke Signs (FAST criteria: facial droop, arm weakness, speech difficulty)
    has_stroke_sign = (
        "facial_droop" in clean_symptoms
        or "face_droop" in clean_symptoms
        or "arm_weakness" in clean_symptoms
        or "limb_weakness" in clean_symptoms
        or "speech_difficulty" in clean_symptoms
        or "slurred_speech" in clean_symptoms
    )
    if has_stroke_sign:
        alerts.append(RedFlagAlert(
            rule_id="ACUTE_STROKE_FAST",
            severity="CRITICAL",
            title="Acute Focal Neurological Deficit / Suspected Stroke",
            description="Presentation exhibits classical FAST neuro-deficit indicators (facial asymmetry, unilateral arm weakness, or expressive/receptive dysphasia).",
            escalation_action="Activate emergent Stroke Protocol. Stat non-contrast head CT and neurology consult for intravenous thrombolysis / endovascular thrombectomy window."
        ))

    # Rule 4: Suspected Meningitis (Fever + Nuchal Rigidity / Stiff Neck)
    has_fever = (
        "fever" in clean_symptoms
        or "high_fever" in clean_symptoms
        or (temp_c is not None and temp_c >= 38.0)
    )
    has_nuchal = "stiff_neck" in clean_symptoms or "neck_stiffness" in clean_symptoms
    if has_fever and has_nuchal:
        alerts.append(RedFlagAlert(
            rule_id="SUSPECTED_MENINGITIS",
            severity="CRITICAL",
            title="Suspected Bacterial / Viral Meningitis (Fever + Nuchal Rigidity)",
            description="Co-occurrence of pyrexia and neck stiffness strongly suggests central nervous system meningeal inflammation.",
            escalation_action="Immediate emergency lumbar puncture evaluation, blood cultures, and prompt initiation of empiric antimicrobial and dexamethasone therapy."
        ))

    # Rule 5: High Fever in Infants (<= 1 year old with Temp >= 38.5°C)
    if age is not None and age <= 1:
        if (temp_c is not None and temp_c >= 38.5) or "high_fever" in clean_symptoms:
            alerts.append(RedFlagAlert(
                rule_id="INFANT_HIGH_FEVER_SEPSIS_RISK",
                severity="CRITICAL",
                title="High Fever in Infant Under 1 Year",
                description=f"Infant (age {age} yr) presenting with documented high pyrexia ({temp_c or 'high'}°C), conferring elevated risk of serious occult bacterial infection.",
                escalation_action="Immediate pediatric evaluation, full sepsis workup (CBC, blood culture, urinalysis), and inpatient observation."
            ))

    # Rule 6: Severe Dehydration / Hypovolemic Shock Signs
    has_fluid_loss = "vomiting" in clean_symptoms or "diarrhea" in clean_symptoms
    has_shock_signs = (
        (bp_sys is not None and bp_sys < 90.0)
        or (hr is not None and hr >= 120)
        or ("dizziness" in clean_symptoms or "lethargy" in clean_symptoms)
    )
    if has_fluid_loss and has_shock_signs:
        alerts.append(RedFlagAlert(
            rule_id="SEVERE_DEHYDRATION_SHOCK",
            severity="CRITICAL",
            title="Severe Dehydration with Hemodynamic Instability / Hypovolemic Shock",
            description="Acute gastrointestinal fluid losses paired with profound hypotension (Systolic BP < 90 mmHg) or marked tachycardia.",
            escalation_action="Immediate intravenous isotonic fluid resuscitation (Normal Saline or Ringer's Lactate wide open), electrolyte profiling, and continuous BP monitoring."
        ))

    return alerts
