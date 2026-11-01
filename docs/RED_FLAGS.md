# Clinical Safety Red-Flag Guardrails & Threshold Specification

> [!CAUTION]
> **Clinical Status: Pending Physician Review**  
> All clinical red-flag rules, triggers, and numerical thresholds documented herein are conservative prototype heuristics developed for educational and clinical decision-support purposes.  
> **Status**: `pending physician review`.  
> They have NOT been validated by clinical trials and do NOT substitute for formal triage by a licensed medical practitioner. In an emergency, emergency medical services must be contacted immediately.

---

## 1. Single Source of Truth Canonical Red-Flag Rules Table

All rules are centrally maintained in [`backend/core/red_flag_constants.py`](file:///d:/projects/TrustFed/backend/core/red_flag_constants.py) and executed deterministically in [`backend/services/red_flags.py`](file:///d:/projects/TrustFed/backend/services/red_flags.py).

| Rule ID | Clinical Severity | Condition / Presentation | Exact Trigger Criteria & Thresholds | Status | Mandatory Escalation Action |
| :--- | :---: | :--- | :--- | :---: | :--- |
| `CARDIAC_ACUTE_CORONARY_SYNDROME` | **CRITICAL** | Suspected Acute Coronary Syndrome (ACS) / Myocardial Infarction | **Chest pain** (`chest_pain`) presenting with at least one autonomic/cardiac sign: <br>• Sweating (`sweating`)<br>• Breathlessness (`breathlessness` or `dyspnea`)<br>• Tachycardia ($\text{HR} \ge 120\text{ bpm}$)<br>• ST segment alteration on ECG (`st_change` / `st_depression`) | *Pending Physician Review* | Immediate 12-lead ECG stat, troponin assay, continuous cardiac monitoring, and emergency transfer to interventional cardiology / ED. |
| `CRITICAL_HYPOXIA` | **CRITICAL** | Severe Hypoxemic Respiratory Failure | Peripheral oxygen saturation **$\text{SpO}_2 < 92.0\%$** (measured via pulse oximetry). | *Pending Physician Review* | Initiate supplemental high-flow oxygen immediately. Evaluate for severe pneumonia, acute asthma exacerbation, or pulmonary embolism. |
| `ACUTE_STROKE_FAST` | **CRITICAL** | Acute Focal Neurological Deficit / Suspected Stroke | Presence of any FAST neurological deficit indicators:<br>• Facial asymmetry / droop (`facial_droop` / `face_droop`)<br>• Arm / limb weakness (`arm_weakness` / `limb_weakness`)<br>• Speech difficulty or slurring (`speech_difficulty` / `slurred_speech`) | *Pending Physician Review* | Activate emergent Stroke Protocol. Stat non-contrast head CT and neurology consult for intravenous thrombolysis / endovascular thrombectomy window. |
| `SUSPECTED_MENINGITIS` | **CRITICAL** | Suspected Bacterial / Viral Meningitis | Pyrexia (core temperature $\ge 38.0^\circ\text{C}$ or symptom `fever`/`high_fever`) combined with nuchal rigidity (`stiff_neck` / `neck_stiffness`). | *Pending Physician Review* | Immediate emergency lumbar puncture evaluation, blood cultures, and prompt initiation of empiric antimicrobial and dexamethasone therapy. |
| `INFANT_HIGH_FEVER_SEPSIS_RISK` | **CRITICAL** | High Fever in Infant Under 1 Year | Infant (age $\le 1\text{ year}$) presenting with core body temperature $\ge 38.5^\circ\text{C}$ or reported `high_fever`. | *Pending Physician Review* | Immediate pediatric evaluation, full sepsis workup (CBC, blood culture, urinalysis), and inpatient observation. |
| `SEVERE_DEHYDRATION_SHOCK` | **CRITICAL** | Severe Dehydration with Hemodynamic Instability / Hypovolemic Shock | Acute GI fluid loss (`vomiting` or `diarrhea`) paired with:<br>• Hypotension ($\text{Systolic BP} < 90.0\text{ mmHg}$), OR<br>• Tachycardia ($\text{HR} \ge 120.0\text{ bpm}$), OR<br>• Marked neuro-fatigue (`dizziness` or `lethargy`) | *Pending Physician Review* | Immediate intravenous isotonic fluid resuscitation (Normal Saline or Ringer's Lactate wide open), electrolyte profiling, and continuous BP monitoring. |
| `HYPERTENSIVE_CRISIS` | **CRITICAL** | Hypertensive Crisis / Acute Blood Pressure Spike | Measured systolic arterial blood pressure **$\text{Systolic BP} \ge 180.0\text{ mmHg}$** OR diastolic arterial blood pressure **$\text{Diastolic BP} \ge 120.0\text{ mmHg}$**. | *Pending Physician Review* | Immediate emergency care. Stat evaluation for target organ damage (papilledema, stroke, aortic dissection, pulmonary edema). IV antihypertensive titration and ICU admission. |
| `CRITICAL_BRADYCARDIA_SHOCK` | **CRITICAL** | Critical Bradycardia / Hemodynamic Collapse Risk | Resting heart rate **$\text{HR} < 40.0\text{ bpm}$**. | *Pending Physician Review* | Immediate 12-lead ECG stat, transcutaneous pacing standby, prepare intravenous atropine/epinephrine, and stat cardiology evaluation. |

---

## 2. Threshold Numerical Summary

The following constants are strictly codified in `backend/core/red_flag_constants.py`:

```python
STATUS_LABEL = "pending physician review"
HYPOXIA_SPO2_THRESHOLD = 92.0            # SpO2 < 92.0%
TACHYCARDIA_HR_THRESHOLD = 120.0        # HR >= 120.0 bpm
BRADYCARDIA_HR_THRESHOLD = 40.0         # HR < 40.0 bpm
HYPOTENSION_SYSTOLIC_BP_THRESHOLD = 90.0 # Systolic BP < 90.0 mmHg
HYPERTENSIVE_CRISIS_SYSTOLIC_BP = 180.0 # Systolic BP >= 180.0 mmHg
HYPERTENSIVE_CRISIS_DIASTOLIC_BP = 120.0# Diastolic BP >= 120.0 mmHg
ADULT_FEVER_TEMP_C = 38.0               # Body temp >= 38.0 C
INFANT_FEVER_TEMP_C = 38.5              # Body temp >= 38.5 C
INFANT_MAX_AGE_YEARS = 1                # Age <= 1 year
```

---

## 3. Priority and Override Semantics

1. **Pre-Emptive Execution**: The safety rules engine runs *prior* to any multi-class model inference and also attaches alerts to the final differential prediction payload.
2. **Immutable Flagging**: If any rule triggers, `hasCriticalRedFlag` is set to `True` on the response payload. The user interface prominently renders a high-visibility emergency banner above any algorithmic differential suggestions.
3. **No Model Suppression**: Algorithmic differential probabilities are not permitted to suppress or mask clinical red-flag alerts. Even if an ambulatory disease (e.g. `common_cold`) scores high probability, the presence of any trigger condition surfaces the emergency escalation protocol immediately.

