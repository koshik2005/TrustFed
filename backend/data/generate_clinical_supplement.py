"""Deterministic Clinical Benchmark Supplement Generator.

Generates a realistic, calibrated synthetic cohort covering 18 common clinical conditions
with missingness masks, physiological vitals distributions, and clinical symptoms.
Kept in backend/data/synthetic_clinical_supplement.json.
"""
from __future__ import annotations
import json
import os
import random
import numpy as np

DISEASE_TAXONOMY = [
    "common_cold", "influenza", "viral_fever", "dengue", "typhoid", "malaria",
    "covid19", "gastroenteritis", "uti", "pneumonia", "bronchitis", "asthma",
    "hypertension", "type2_diabetes", "anemia", "migraine", "allergic_rhinitis", "heart_disease"
]

SYMPTOM_LEXICON = [
    "fever", "high_fever", "cough", "dry_cough", "productive_cough", "sore_throat",
    "runny_nose", "sneezing", "headache", "retro_orbital_pain", "vomiting", "diarrhea",
    "chest_pain", "breathlessness", "wheezing", "rash", "petechiae", "joint_pain",
    "muscle_ache", "fatigue", "loss_of_taste_smell", "abdominal_pain", "burning_urination",
    "urinary_frequency", "chills", "dizziness", "sweating", "stiff_neck", "facial_droop",
    "arm_weakness", "speech_difficulty", "excessive_thirst", "frequent_urination", "pale_skin",
    "throbbing_headache"
]

# Clinical phenotype distributions: (common_symptoms, typical_vitals_mean_std, typical_labs)
PHENOTYPES = {
    "common_cold": {
        "symptoms": ["runny_nose", "sneezing", "sore_throat", "cough", "fatigue"],
        "temp": (37.1, 0.4), "hr": (74, 8), "spo2": (98.5, 0.8), "bp_sys": (118, 10),
        "platelets": (240, 40), "wbc": (6.5, 1.5)
    },
    "influenza": {
        "symptoms": ["high_fever", "cough", "dry_cough", "muscle_ache", "headache", "chills", "fatigue", "sore_throat"],
        "temp": (38.8, 0.6), "hr": (96, 12), "spo2": (97.0, 1.2), "bp_sys": (115, 12),
        "platelets": (210, 45), "wbc": (5.5, 1.8)
    },
    "viral_fever": {
        "symptoms": ["fever", "muscle_ache", "headache", "fatigue", "chills"],
        "temp": (38.4, 0.5), "hr": (88, 10), "spo2": (98.0, 1.0), "bp_sys": (116, 10),
        "platelets": (190, 40), "wbc": (5.8, 1.5)
    },
    "dengue": {
        "symptoms": ["high_fever", "retro_orbital_pain", "joint_pain", "petechiae", "rash", "vomiting", "headache"],
        "temp": (39.2, 0.6), "hr": (98, 14), "spo2": (97.5, 1.1), "bp_sys": (108, 12),
        "platelets": (75, 28), "wbc": (3.6, 1.2)  # Characteristic thrombocytopenia & leukopenia
    },
    "typhoid": {
        "symptoms": ["fever", "abdominal_pain", "headache", "diarrhea", "vomiting", "fatigue", "loss_of_appetite"],
        "temp": (39.0, 0.5), "hr": (78, 8), "spo2": (98.0, 0.8), "bp_sys": (110, 10),  # Relative bradycardia
        "platelets": (170, 40), "wbc": (4.2, 1.4)
    },
    "malaria": {
        "symptoms": ["high_fever", "chills", "sweating", "headache", "vomiting", "fatigue"],
        "temp": (39.4, 0.7), "hr": (102, 15), "spo2": (97.0, 1.2), "bp_sys": (112, 12),
        "platelets": (110, 35), "wbc": (5.2, 1.6)
    },
    "covid19": {
        "symptoms": ["fever", "dry_cough", "loss_of_taste_smell", "breathlessness", "fatigue", "sore_throat"],
        "temp": (38.3, 0.6), "hr": (86, 10), "spo2": (95.5, 2.2), "bp_sys": (120, 12),
        "platelets": (220, 50), "wbc": (5.0, 1.8)
    },
    "gastroenteritis": {
        "symptoms": ["vomiting", "diarrhea", "abdominal_pain", "nausea", "fever", "fatigue", "dizziness"],
        "temp": (37.8, 0.5), "hr": (95, 12), "spo2": (98.5, 0.8), "bp_sys": (105, 14),
        "platelets": (250, 45), "wbc": (9.5, 2.5)
    },
    "uti": {
        "symptoms": ["burning_urination", "urinary_frequency", "abdominal_pain", "fever", "chills"],
        "temp": (37.7, 0.5), "hr": (80, 8), "spo2": (98.5, 0.7), "bp_sys": (122, 10),
        "platelets": (240, 40), "wbc": (11.0, 2.8)  # Leukocytosis
    },
    "pneumonia": {
        "symptoms": ["high_fever", "cough", "productive_cough", "breathlessness", "chest_pain", "chills", "fatigue"],
        "temp": (38.9, 0.7), "hr": (104, 14), "spo2": (92.5, 2.5), "bp_sys": (118, 14),  # Hypoxemia
        "platelets": (280, 60), "wbc": (14.5, 3.5)
    },
    "bronchitis": {
        "symptoms": ["cough", "productive_cough", "wheezing", "sore_throat", "fatigue", "fever"],
        "temp": (37.6, 0.4), "hr": (82, 9), "spo2": (96.5, 1.5), "bp_sys": (122, 10),
        "platelets": (230, 40), "wbc": (8.0, 2.0)
    },
    "asthma": {
        "symptoms": ["breathlessness", "wheezing", "cough", "dry_cough", "chest_pain"],
        "temp": (36.8, 0.3), "hr": (92, 12), "spo2": (94.0, 2.0), "bp_sys": (126, 12),
        "platelets": (240, 40), "wbc": (7.2, 1.8)
    },
    "hypertension": {
        "symptoms": ["headache", "dizziness", "fatigue"],
        "temp": (36.7, 0.3), "hr": (78, 10), "spo2": (98.5, 0.6), "bp_sys": (158, 15),  # Elevated BP
        "platelets": (240, 40), "wbc": (6.5, 1.5)
    },
    "type2_diabetes": {
        "symptoms": ["excessive_thirst", "frequent_urination", "fatigue", "dizziness"],
        "temp": (36.7, 0.3), "hr": (76, 8), "spo2": (98.2, 0.7), "bp_sys": (132, 12),
        "platelets": (250, 45), "wbc": (6.8, 1.5), "blood_sugar": (185, 45)  # Hyperglycemia
    },
    "anemia": {
        "symptoms": ["pale_skin", "fatigue", "breathlessness", "dizziness", "headache"],
        "temp": (36.6, 0.3), "hr": (88, 10), "spo2": (97.8, 1.0), "bp_sys": (110, 10),
        "platelets": (260, 50), "wbc": (6.0, 1.4)
    },
    "migraine": {
        "symptoms": ["throbbing_headache", "headache", "vomiting", "dizziness"],
        "temp": (36.7, 0.3), "hr": (75, 8), "spo2": (98.8, 0.5), "bp_sys": (120, 10),
        "platelets": (230, 40), "wbc": (6.2, 1.2)
    },
    "allergic_rhinitis": {
        "symptoms": ["sneezing", "runny_nose", "cough", "fatigue"],
        "temp": (36.7, 0.2), "hr": (72, 6), "spo2": (99.0, 0.4), "bp_sys": (118, 8),
        "platelets": (240, 35), "wbc": (6.0, 1.2)
    },
    "heart_disease": {
        "symptoms": ["chest_pain", "breathlessness", "sweating", "dizziness", "fatigue"],
        "temp": (36.8, 0.3), "hr": (90, 15), "spo2": (96.5, 1.8), "bp_sys": (145, 18),
        "platelets": (220, 45), "wbc": (7.5, 1.8)
    }
}


def generate_cohort(n_samples_per_class: int = 50, seed: int = 42) -> list[dict]:
    random.seed(seed)
    np.random.seed(seed)
    cohort = []

    sample_id = 1
    for disease_code in DISEASE_TAXONOMY:
        p = PHENOTYPES[disease_code]
        core_symptoms = p["symptoms"]

        for _ in range(n_samples_per_class):
            # Age distribution
            if disease_code in ("heart_disease", "type2_diabetes", "hypertension"):
                age = int(np.clip(np.random.normal(58, 10), 30, 92))
            elif disease_code == "anemia":
                age = int(np.clip(np.random.normal(34, 14), 14, 80))
            else:
                age = int(np.clip(np.random.normal(38, 16), 1, 88))

            sex = random.choice([0, 1, 2])
            weight = float(np.clip(np.random.normal(70, 14), 42, 130))
            height = float(np.clip(np.random.normal(168, 10), 140, 195))

            # Select symptoms: pick 2 to 4 core symptoms + 0 to 1 random background symptoms
            k_core = random.randint(min(2, len(core_symptoms)), min(4, len(core_symptoms)))
            chosen_symptoms = set(random.sample(core_symptoms, k_core))
            if random.random() < 0.25:
                chosen_symptoms.add(random.choice(SYMPTOM_LEXICON))

            duration = random.randint(1, 10) if "fever" in chosen_symptoms else random.randint(1, 30)

            # Continuous vitals with realistic clinical noise
            t_mean, t_std = p["temp"]
            temp_c = round(float(np.clip(np.random.normal(t_mean, t_std), 35.5, 41.5)), 1)

            hr_mean, hr_std = p["hr"]
            hr = int(np.clip(np.random.normal(hr_mean, hr_std), 45, 160))

            spo2_mean, spo2_std = p["spo2"]
            spo2 = round(float(np.clip(np.random.normal(spo2_mean, spo2_std), 85.0, 100.0)), 1)

            sys_mean, sys_std = p["bp_sys"]
            bp_sys = int(np.clip(np.random.normal(sys_mean, sys_std), 85, 210))
            bp_dia = int(bp_sys * random.uniform(0.62, 0.70))

            resp_rate = int(np.clip(16 + (hr - 75) * 0.1 + (100 - spo2) * 0.4 + random.gauss(0, 2), 12, 45))

            sugar_mean, sugar_std = p.get("blood_sugar", (95, 15))
            blood_sugar = round(float(np.clip(np.random.normal(sugar_mean, sugar_std), 60, 450)), 1)

            # Labs
            plt_mean, plt_std = p["platelets"]
            platelets = round(float(np.clip(np.random.normal(plt_mean, plt_std), 15, 600)), 1)

            wbc_mean, wbc_std = p["wbc"]
            wbc = round(float(np.clip(np.random.normal(wbc_mean, wbc_std), 1.8, 30.0)), 1)

            # Apply realistic missingness mask (vitals missing in outpatient visits)
            vitals = {}
            if random.random() > 0.10: vitals["temp_c"] = temp_c
            if random.random() > 0.15: vitals["bp_sys"] = bp_sys; vitals["bp_dia"] = bp_dia
            if random.random() > 0.15: vitals["hr"] = hr
            if random.random() > 0.25: vitals["spo2"] = spo2
            if random.random() > 0.35: vitals["resp_rate"] = resp_rate
            if random.random() > 0.40: vitals["blood_sugar"] = blood_sugar

            labs = {}
            # Labs only ordered in 35-45% of outpatient cases
            if random.random() > 0.60: labs["platelets"] = platelets
            if random.random() > 0.60: labs["wbc"] = wbc

            cohort.append({
                "sample_id": f"SYN-{sample_id:05d}",
                "patient": {
                    "age": age,
                    "sex": sex,
                    "weight": round(weight, 1),
                    "height": round(height, 1)
                },
                "encounter": {
                    "symptoms": sorted(list(chosen_symptoms)),
                    "symptom_duration_days": duration,
                    "vitals": vitals,
                    "optional_labs": labs
                },
                "ground_truth_diagnosis": disease_code
            })
            sample_id += 1

    return cohort


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "synthetic_clinical_supplement.json")
    data = generate_cohort(n_samples_per_class=60, seed=42)  # 18 * 60 = 1080 samples
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "version": "1.0",
            "description": "TrustFed AI Synthetic Benchmark Supplement for 18-disease differential inference",
            "count": len(data),
            "diseases": DISEASE_TAXONOMY,
            "data": data
        }, f, indent=2)
    print(f"Generated {len(data)} synthetic clinical samples saved to {out_path}")
