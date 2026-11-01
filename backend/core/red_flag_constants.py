"""Single Source of Truth for Clinical Red-Flag Safety Thresholds and Rule Definitions.

All thresholds and rules are conservative prototype heuristics.
STATUS LABEL: "pending physician review"
"""
from __future__ import annotations
from typing import Any, Dict, List

STATUS_LABEL: str = "pending physician review"

# Numerical Clinical Thresholds (Conservative Prototype Heuristics)
HYPOXIA_SPO2_THRESHOLD: float = 92.0            # SpO2 < 92% indicates severe hypoxemia
TACHYCARDIA_HR_THRESHOLD: float = 120.0        # HR >= 120 bpm (evaluated with concurrent signs)
BRADYCARDIA_HR_THRESHOLD: float = 40.0         # HR < 40 bpm indicates severe bradycardia / shock
HYPOTENSION_SYSTOLIC_BP_THRESHOLD: float = 90.0 # Systolic BP < 90 mmHg indicates hemodynamic shock
HYPERTENSIVE_CRISIS_SYSTOLIC_BP: float = 180.0 # Systolic BP >= 180 mmHg indicates hypertensive emergency
HYPERTENSIVE_CRISIS_DIASTOLIC_BP: float = 120.0# Diastolic BP >= 120 mmHg indicates hypertensive emergency
ADULT_FEVER_TEMP_C: float = 38.0               # Core body temp >= 38.0 C
INFANT_FEVER_TEMP_C: float = 38.5              # Core body temp >= 38.5 C in infants <= 1 year
INFANT_MAX_AGE_YEARS: int = 1                  # Age threshold for infant pyrexia protocol

# Canonical Definitions of All Red-Flag Rules
RED_FLAG_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "rule_id": "CARDIAC_ACUTE_CORONARY_SYNDROME",
        "severity": "CRITICAL",
        "condition_name": "Acute Coronary Syndrome (ACS) / Myocardial Infarction",
        "trigger_criteria": "Chest pain accompanied by autonomic signs (sweating, breathlessness/dyspnea, tachycardia HR >= 120, or ST segment alteration).",
        "thresholds": {
            "symptoms": ["chest_pain"],
            "concurrent_signs": ["sweating", "breathlessness", "dyspnea", f"hr >= {TACHYCARDIA_HR_THRESHOLD}", "st_change"],
        },
        "status": STATUS_LABEL,
        "escalation_action": "Immediate 12-lead ECG stat, troponin assay, continuous cardiac monitoring, and emergency transfer to interventional cardiology / ED."
    },
    {
        "rule_id": "CRITICAL_HYPOXIA",
        "severity": "CRITICAL",
        "condition_name": "Severe Hypoxemic Respiratory Failure",
        "trigger_criteria": f"Peripheral oxygen saturation SpO2 < {HYPOXIA_SPO2_THRESHOLD}%.",
        "thresholds": {
            "spo2": f"< {HYPOXIA_SPO2_THRESHOLD}%",
        },
        "status": STATUS_LABEL,
        "escalation_action": "Initiate supplemental high-flow oxygen immediately. Evaluate for severe pneumonia, acute asthma exacerbation, or pulmonary embolism."
    },
    {
        "rule_id": "ACUTE_STROKE_FAST",
        "severity": "CRITICAL",
        "condition_name": "Acute Focal Neurological Deficit / Suspected Stroke",
        "trigger_criteria": "Presentation exhibits classical FAST indicators: facial droop, unilateral arm/limb weakness, or speech difficulty / slurred speech.",
        "thresholds": {
            "symptoms": ["facial_droop", "arm_weakness", "limb_weakness", "speech_difficulty", "slurred_speech"],
        },
        "status": STATUS_LABEL,
        "escalation_action": "Activate emergent Stroke Protocol. Stat non-contrast head CT and neurology consult for intravenous thrombolysis / endovascular thrombectomy window."
    },
    {
        "rule_id": "SUSPECTED_MENINGITIS",
        "severity": "CRITICAL",
        "condition_name": "Suspected Bacterial / Viral Meningitis",
        "trigger_criteria": f"Pyrexia (Temp >= {ADULT_FEVER_TEMP_C} C or fever symptom) combined with nuchal rigidity / stiff neck.",
        "thresholds": {
            "temp_c": f">= {ADULT_FEVER_TEMP_C} C",
            "symptoms": ["stiff_neck", "neck_stiffness"],
        },
        "status": STATUS_LABEL,
        "escalation_action": "Immediate emergency lumbar puncture evaluation, blood cultures, and prompt initiation of empiric antimicrobial and dexamethasone therapy."
    },
    {
        "rule_id": "INFANT_HIGH_FEVER_SEPSIS_RISK",
        "severity": "CRITICAL",
        "condition_name": "High Fever in Infant Under 1 Year",
        "trigger_criteria": f"Infant (age <= {INFANT_MAX_AGE_YEARS} year) with core temperature >= {INFANT_FEVER_TEMP_C} C or high_fever.",
        "thresholds": {
            "age": f"<= {INFANT_MAX_AGE_YEARS} year",
            "temp_c": f">= {INFANT_FEVER_TEMP_C} C",
        },
        "status": STATUS_LABEL,
        "escalation_action": "Immediate pediatric evaluation, full sepsis workup (CBC, blood culture, urinalysis), and inpatient observation."
    },
    {
        "rule_id": "SEVERE_DEHYDRATION_SHOCK",
        "severity": "CRITICAL",
        "condition_name": "Severe Dehydration with Hemodynamic Instability / Hypovolemic Shock",
        "trigger_criteria": f"Acute gastrointestinal fluid loss (vomiting or diarrhea) paired with hypotension (Systolic BP < {HYPOTENSION_SYSTOLIC_BP_THRESHOLD} mmHg), tachycardia (HR >= {TACHYCARDIA_HR_THRESHOLD} bpm), or marked lethargy/dizziness.",
        "thresholds": {
            "fluid_loss": ["vomiting", "diarrhea"],
            "bp_sys": f"< {HYPOTENSION_SYSTOLIC_BP_THRESHOLD} mmHg",
            "hr": f">= {TACHYCARDIA_HR_THRESHOLD} bpm",
            "signs": ["dizziness", "lethargy"]
        },
        "status": STATUS_LABEL,
        "escalation_action": "Immediate intravenous isotonic fluid resuscitation (Normal Saline or Ringer's Lactate wide open), electrolyte profiling, and continuous BP monitoring."
    },
    {
        "rule_id": "HYPERTENSIVE_CRISIS",
        "severity": "CRITICAL",
        "condition_name": "Hypertensive Crisis / Acute Blood Pressure Spike",
        "trigger_criteria": f"Systolic blood pressure >= {HYPERTENSIVE_CRISIS_SYSTOLIC_BP} mmHg or Diastolic blood pressure >= {HYPERTENSIVE_CRISIS_DIASTOLIC_BP} mmHg.",
        "thresholds": {
            "bp_sys": f">= {HYPERTENSIVE_CRISIS_SYSTOLIC_BP} mmHg",
            "bp_dia": f">= {HYPERTENSIVE_CRISIS_DIASTOLIC_BP} mmHg",
        },
        "status": STATUS_LABEL,
        "escalation_action": "Stat assessment for acute end-organ damage (chest pain, headache, papilledema, dyspnea). Administer IV/oral antihypertensives per emergency protocol and transfer to acute care."
    },
    {
        "rule_id": "CRITICAL_BRADYCARDIA_SHOCK",
        "severity": "CRITICAL",
        "condition_name": "Critical Bradycardia / Hemodynamic Collapse Risk",
        "trigger_criteria": f"Resting heart rate < {BRADYCARDIA_HR_THRESHOLD} bpm.",
        "thresholds": {
            "hr": f"< {BRADYCARDIA_HR_THRESHOLD} bpm",
        },
        "status": STATUS_LABEL,
        "escalation_action": "Immediate 12-lead ECG stat, prepare transcutaneous pacing and IV atropine. Assess for AV block, severe electrolyte disturbance, or drug toxicity."
    }
]

