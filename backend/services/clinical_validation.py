"""Clinical input validation service with physiological boundary checking.

Enforces sensible biological ranges and structural invariants for patients,
vitals, symptoms, and laboratory findings.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


# Valid symptom dictionary for standard normalization
STANDARD_SYMPTOMS = {
    "fever": "Fever / Pyrexia",
    "high_fever": "High-Grade Fever (>39°C)",
    "cough": "Cough",
    "dry_cough": "Dry Hacking Cough",
    "sore_throat": "Sore Throat / Pharyngitis",
    "runny_nose": "Rhinorrhea / Runny Nose",
    "sneezing": "Frequent Sneezing",
    "headache": "Frontal / Generalized Headache",
    "retro_orbital_pain": "Pain Behind the Eyes",
    "vomiting": "Nausea & Vomiting",
    "diarrhea": "Watery / Loose Diarrhea",
    "chest_pain": "Substernal / Precordial Chest Pain",
    "breathlessness": "Dyspnea / Shortness of Breath",
    "rash": "Cutaneous Rash / Petechiae",
    "petechial_rash": "Petechial Rash / Purpura",
    "joint_pain": "Arthralgia / Joint Pain",
    "severe_joint_pain": "Severe Breakbone Joint Pain",
    "fatigue": "Generalized Malaise & Fatigue",
    "body_ache": "Myalgia / Severe Body Ache",
    "loss_of_taste_smell": "Anosmia / Loss of Taste & Smell",
    "abdominal_pain": "Epigastric / Abdominal Pain",
    "burning_urination": "Dysuria / Burning Urination",
    "urinary_frequency": "Increased Urinary Frequency",
    "urinary_urgency": "Urinary Urgency",
    "cloudy_urine": "Turbid / Cloudy Urine",
    "chills": "Rigors & Shivering Chills",
    "dizziness": "Orthostatic Dizziness / Syncope",
    "sweating": "Diaphoresis / Cold Sweats",
    "loss_of_appetite": "Anorexia / Loss of Appetite",
}

VALID_ECG_FINDINGS = {"normal", "st_change", "st_depression", "arrhythmia", "tachycardia", "other"}


def validate_patient_payload(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
    """Validate core patient demographics.
    
    Required: age, sex.
    Optional: name, contact, weight, height.
    """
    errors: Dict[str, str] = {}

    # Age: Required, range 0 to 125
    age = data.get("age")
    if age is None or age == "":
        errors["age"] = "Patient age is required."
    else:
        try:
            age_int = int(age)
            if age_int < 0 or age_int > 125:
                errors["age"] = "Age must be a biologically plausible value between 0 and 125 years."
        except (ValueError, TypeError):
            errors["age"] = "Age must be a valid integer."

    # Sex: Required (0=Female, 1=Male, 2=Other)
    sex = data.get("sex")
    if sex is None or sex == "":
        errors["sex"] = "Biological sex is required (Female, Male, or Other)."
    else:
        try:
            sex_int = int(sex)
            if sex_int not in (0, 1, 2):
                errors["sex"] = "Biological sex must be 0 (Female), 1 (Male), or 2 (Other)."
        except (ValueError, TypeError):
            if str(sex).lower() in ("female", "f"):
                data["sex"] = 0
            elif str(sex).lower() in ("male", "m"):
                data["sex"] = 1
            elif str(sex).lower() in ("other", "o"):
                data["sex"] = 2
            else:
                errors["sex"] = "Invalid sex value. Accepted values are Female, Male, or Other."

    # Name: Optional, but if provided, sensible length
    name = data.get("name")
    if name is not None and len(str(name).strip()) > 150:
        errors["name"] = "Patient name cannot exceed 150 characters."

    # Contact: Optional, but if provided, sensible length
    contact = data.get("contact")
    if contact is not None and len(str(contact).strip()) > 80:
        errors["contact"] = "Contact details cannot exceed 80 characters."

    # Weight: Optional, range 0.5 to 450.0 kg
    weight = data.get("weight")
    if weight is not None and weight != "":
        try:
            w_float = float(weight)
            if w_float < 0.5 or w_float > 450.0:
                errors["weight"] = "Weight must be between 0.5 kg and 450.0 kg."
        except (ValueError, TypeError):
            errors["weight"] = "Weight must be a valid number in kilograms."

    # Height: Optional, range 30.0 to 260.0 cm
    height = data.get("height")
    if height is not None and height != "":
        try:
            h_float = float(height)
            if h_float < 30.0 or h_float > 260.0:
                errors["height"] = "Height must be between 30.0 cm and 260.0 cm."
        except (ValueError, TypeError):
            errors["height"] = "Height must be a valid number in centimeters."

    return (len(errors) == 0, errors)


def validate_encounter_payload(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
    """Validate symptoms, vitals, duration, ECG, and labs.
    
    Required: at least one symptom.
    Optional: duration, vitals, ecg, labs.
    """
    errors: Dict[str, str] = {}

    # Symptoms: Required, at least one non-empty string
    symptoms = data.get("symptoms")
    if not symptoms or not isinstance(symptoms, list) or len(symptoms) == 0:
        errors["symptoms"] = "At least one presenting symptom is required."
    else:
        valid_items = [s for s in symptoms if isinstance(s, str) and s.strip()]
        if len(valid_items) == 0:
            errors["symptoms"] = "At least one valid symptom must be specified."

    # Duration: Optional, 1 to 365 days
    duration = data.get("symptom_duration_days")
    if duration is not None and duration != "":
        try:
            d_int = int(duration)
            if d_int < 1 or d_int > 365:
                errors["symptom_duration_days"] = "Symptom duration must be between 1 and 365 days."
        except (ValueError, TypeError):
            errors["symptom_duration_days"] = "Symptom duration must be an integer number of days."

    # Vitals: Optional object
    vitals = data.get("vitals") or {}
    if not isinstance(vitals, dict):
        errors["vitals"] = "Vitals must be provided as a structured JSON object."
    else:
        # Body Temperature: 30.0°C to 45.0°C or 86.0°F to 113.0°F
        temp = vitals.get("temp_c")
        if temp is not None and temp != "":
            try:
                t_float = float(temp)
                # If entered in Fahrenheit (> 60), check F range and convert or flag
                if t_float > 70.0:
                    if t_float < 86.0 or t_float > 113.0:
                        errors["vitals.temp"] = "Temperature in Fahrenheit must be between 86.0°F and 113.0°F."
                else:
                    if t_float < 30.0 or t_float > 45.0:
                        errors["vitals.temp"] = "Body temperature must be between 30.0°C and 45.0°C."
            except (ValueError, TypeError):
                errors["vitals.temp"] = "Temperature must be a valid numeric value."

        # Blood Pressure: Systolic & Diastolic
        bp_sys = vitals.get("bp_sys")
        bp_dia = vitals.get("bp_dia")
        bp_sys_val = None
        bp_dia_val = None

        if bp_sys is not None and bp_sys != "":
            try:
                bp_sys_val = int(bp_sys)
                if bp_sys_val < 50 or bp_sys_val > 260:
                    errors["vitals.bp_sys"] = "Systolic BP must be between 50 and 260 mmHg."
            except (ValueError, TypeError):
                errors["vitals.bp_sys"] = "Systolic BP must be an integer."

        if bp_dia is not None and bp_dia != "":
            try:
                bp_dia_val = int(bp_dia)
                if bp_dia_val < 30 or bp_dia_val > 160:
                    errors["vitals.bp_dia"] = "Diastolic BP must be between 30 and 160 mmHg."
            except (ValueError, TypeError):
                errors["vitals.bp_dia"] = "Diastolic BP must be an integer."

        if bp_sys_val is not None and bp_dia_val is not None:
            if bp_sys_val <= bp_dia_val:
                errors["vitals.bp"] = f"Systolic pressure ({bp_sys_val}) must exceed diastolic pressure ({bp_dia_val})."

        # Heart Rate: 30 to 260 bpm
        hr = vitals.get("hr")
        if hr is not None and hr != "":
            try:
                hr_val = int(hr)
                if hr_val < 30 or hr_val > 260:
                    errors["vitals.hr"] = "Heart rate must be between 30 and 260 beats per minute."
            except (ValueError, TypeError):
                errors["vitals.hr"] = "Heart rate must be an integer."

        # SpO2: 50% to 100%
        spo2 = vitals.get("spo2")
        if spo2 is not None and spo2 != "":
            try:
                spo2_val = float(spo2)
                if spo2_val < 50.0 or spo2_val > 100.0:
                    errors["vitals.spo2"] = "Oxygen saturation (SpO2) must be between 50% and 100%."
            except (ValueError, TypeError):
                errors["vitals.spo2"] = "Oxygen saturation must be a percentage between 50 and 100."

        # Respiratory Rate: 5 to 70 breaths/min
        rr = vitals.get("resp_rate")
        if rr is not None and rr != "":
            try:
                rr_val = int(rr)
                if rr_val < 5 or rr_val > 70:
                    errors["vitals.resp_rate"] = "Respiratory rate must be between 5 and 70 breaths per minute."
            except (ValueError, TypeError):
                errors["vitals.resp_rate"] = "Respiratory rate must be an integer."

        # Blood Sugar / Glucose: 20 to 700 mg/dL
        bs = vitals.get("blood_sugar")
        if bs is not None and bs != "":
            try:
                bs_val = float(bs)
                if bs_val < 20.0 or bs_val > 700.0:
                    errors["vitals.blood_sugar"] = "Blood sugar must be between 20 and 700 mg/dL."
            except (ValueError, TypeError):
                errors["vitals.blood_sugar"] = "Blood sugar must be a valid number."

    # ECG finding: Optional string
    ecg = data.get("structured_ecg_finding")
    if ecg is not None and ecg != "":
        clean_ecg = str(ecg).strip().lower()
        if clean_ecg not in VALID_ECG_FINDINGS:
            errors["structured_ecg_finding"] = f"ECG finding must be one of: {', '.join(sorted(VALID_ECG_FINDINGS))}."

    # Optional Labs: Optional object with sensible limits
    labs = data.get("optional_labs") or {}
    if labs and isinstance(labs, dict):
        if "wbc" in labs and labs["wbc"] not in (None, ""):
            try:
                wbc = float(labs["wbc"])
                if wbc < 0.2 or wbc > 150.0:
                    errors["optional_labs.wbc"] = "WBC count must be between 0.2 and 150.0 x10^3/uL."
            except (ValueError, TypeError):
                errors["optional_labs.wbc"] = "WBC must be a valid number."

        if "platelets" in labs and labs["platelets"] not in (None, ""):
            try:
                plt = float(labs["platelets"])
                if plt < 5.0 or plt > 2000.0:
                    errors["optional_labs.platelets"] = "Platelet count must be between 5.0 and 2000.0 x10^3/uL."
            except (ValueError, TypeError):
                errors["optional_labs.platelets"] = "Platelets must be a valid number."

    return (len(errors) == 0, errors)
