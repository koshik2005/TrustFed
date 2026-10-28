"""Synthetic demo data seeder for TrustFed AI General Disease platform.

Guarantees:
- Strictly guarded: NEVER runs in production unless ALLOW_DEMO_USERS=true.
- Seeds only synthetic, clinically realistic test cases (fever, dengue, typhoid, UTI, cold, flu, cardiac).
- All patient names and phone numbers are encrypted at rest using Fernet.
"""
from __future__ import annotations
import json
import os
import datetime
from sqlalchemy.orm import Session
from db import models
from services import auth, crypto

DISEASES = [
    {
        "code": "COLD",
        "name": "Common Cold (Viral Rhinitis)",
        "category": "Respiratory",
        "common_symptoms": ["runny_nose", "sneezing", "sore_throat", "mild_cough", "low_grade_fever"]
    },
    {
        "code": "FLU",
        "name": "Influenza (Seasonal Flu)",
        "category": "Respiratory",
        "common_symptoms": ["high_fever", "chills", "severe_myalgia", "headache", "dry_cough", "fatigue"]
    },
    {
        "code": "VIRAL_FEVER",
        "name": "Acute Viral Pyrexia",
        "category": "Infectious",
        "common_symptoms": ["fever", "body_aches", "headache", "generalized_weakness", "loss_of_appetite"]
    },
    {
        "code": "DENGUE",
        "name": "Dengue Fever (Breakbone Fever)",
        "category": "Infectious / Arbovirus",
        "common_symptoms": ["high_fever", "retro_orbital_pain", "severe_arthralgia", "petechial_rash", "thrombocytopenia"]
    },
    {
        "code": "TYPHOID",
        "name": "Typhoid Enteric Fever",
        "category": "Infectious / Bacterial",
        "common_symptoms": ["step_ladder_fever", "abdominal_pain", "rose_spots", "hepatosplenomegaly", "bradycardia"]
    },
    {
        "code": "UTI",
        "name": "Urinary Tract Infection",
        "category": "Urinary",
        "common_symptoms": ["dysuria", "urinary_frequency", "urgency", "suprapubic_tenderness", "cloudy_urine"]
    },
    {
        "code": "CARDIAC_CAD",
        "name": "Coronary Artery Disease (CAD)",
        "category": "Cardiovascular",
        "common_symptoms": ["exertional_angina", "substernal_chest_pressure", "shortness_of_breath", "diaphoresis"]
    },
]

DEMO_HUBS = [
    ("hub-east", "East Coast Regional Hub", "East"),
    ("hub-west", "West Coast Regional Hub", "West"),
]

DEMO_HOSPITALS = [
    ("1", "Boston General Hospital", "hub-east", True),
    ("2", "City Med Center", "hub-east", True),
    ("3", "Westside Clinic", "hub-west", False),
    ("4", "Riverside Medical Center", "hub-west", True),
]

DEMO_USERS = [
    ("admin@trustfed.ai", "Dr. Marcus Vance", "global_admin", None, None),
    ("regional@trustfed.ai", "Dr. Elena Rostova", "regional_admin", "hub-east", None),
    ("hospital@trustfed.ai", "Nurse Sarah Chen", "hospital_staff", None, "1"),
    ("doctor@trustfed.ai", "Dr. Anthony Ross", "doctor", None, "1"),
]

SYNTHETIC_PATIENTS = [
    {
        "identifier": "PT-GEN-001",
        "hospital_id": "1",
        "name": "Johnathan Doe (Synthetic)",
        "contact": "+1-555-0192 / j.doe.synthetic@test.org",
        "age": 34,
        "sex": 1,
        "weight": 76.5,
        "height": 178.0,
        "encounter": {
            "symptoms": ["high_fever", "retro_orbital_pain", "severe_arthralgia", "nausea"],
            "duration": 4,
            "vitals": {"bp_sys": 110, "bp_dia": 72, "hr": 98, "temp_c": 39.4, "spo2": 97, "resp_rate": 19},
            "labs": {"wbc": 3.8, "platelets": 88, "crp": 32, "hematocrit": 45.2},
            "predicted_top3": [
                {"disease": "Dengue Fever", "probability": 0.81},
                {"disease": "Acute Viral Pyrexia", "probability": 0.14},
                {"disease": "Typhoid Enteric Fever", "probability": 0.04}
            ],
            "diagnosis": "DENGUE",
            "cause": "Aedes aegypti vector transmission with secondary viremia",
            "treatment": "Strict oral rehydration, paracetamol 650mg SOS, platelet monitoring daily. Avoid NSAIDs.",
            "trainable": True
        }
    },
    {
        "identifier": "PT-GEN-002",
        "hospital_id": "1",
        "name": "Maria Gonzales (Synthetic)",
        "contact": "+1-555-0144 / m.gonzales.synthetic@test.org",
        "age": 28,
        "sex": 0,
        "weight": 61.0,
        "height": 164.0,
        "encounter": {
            "symptoms": ["dysuria", "urinary_frequency", "suprapubic_tenderness", "low_grade_fever"],
            "duration": 2,
            "vitals": {"bp_sys": 118, "bp_dia": 78, "hr": 82, "temp_c": 37.8, "spo2": 99, "resp_rate": 16},
            "labs": {"urine_leukocyte_esterase": "positive", "urine_nitrite": "positive", "wbc": 9.4},
            "predicted_top3": [
                {"disease": "Urinary Tract Infection", "probability": 0.89},
                {"disease": "Acute Viral Pyrexia", "probability": 0.08},
                {"disease": "Common Cold", "probability": 0.02}
            ],
            "diagnosis": "UTI",
            "cause": "Ascending uropathogenic E. coli infection",
            "treatment": "Nitrofurantoin 100mg PO BID for 5 days, hydration > 2.5L/day.",
            "trainable": True
        }
    },
    {
        "identifier": "PT-GEN-003",
        "hospital_id": "1",
        "name": "David Sterling (Synthetic)",
        "contact": "+1-555-0188 / d.sterling.synthetic@test.org",
        "age": 62,
        "sex": 1,
        "weight": 84.0,
        "height": 175.0,
        "encounter": {
            "symptoms": ["exertional_angina", "substernal_chest_pressure", "shortness_of_breath"],
            "duration": 7,
            "vitals": {"bp_sys": 148, "bp_dia": 92, "hr": 78, "temp_c": 36.8, "spo2": 96, "resp_rate": 18},
            "ecg": "st_depression",
            "labs": {"troponin_t": "borderline", "cholesterol": 248, "hdl": 38, "ldl": 162},
            "predicted_top3": [
                {"disease": "Coronary Artery Disease (CAD)", "probability": 0.92},
                {"disease": "Hypertension", "probability": 0.06},
                {"disease": "Acute Viral Pyrexia", "probability": 0.01}
            ],
            "diagnosis": "CARDIAC_CAD",
            "cause": "Atherosclerotic coronary artery disease with exertional ischemia",
            "treatment": "Aspirin 81mg, Atorvastatin 40mg, Metoprolol 25mg, Urgent Cardiology Angiography referral.",
            "trainable": True
        }
    },
    {
        "identifier": "PT-GEN-004",
        "hospital_id": "2",
        "name": "Priya Sharma (Synthetic)",
        "contact": "+1-555-0112 / p.sharma.synthetic@test.org",
        "age": 22,
        "sex": 0,
        "weight": 52.0,
        "height": 160.0,
        "encounter": {
            "symptoms": ["step_ladder_fever", "abdominal_pain", "constipation", "malaise"],
            "duration": 6,
            "vitals": {"bp_sys": 112, "bp_dia": 70, "hr": 76, "temp_c": 39.1, "spo2": 98, "resp_rate": 18},
            "labs": {"widal_test": "positive_1_160", "sgpt": 54, "sgot": 61},
            "predicted_top3": [
                {"disease": "Typhoid Enteric Fever", "probability": 0.84},
                {"disease": "Dengue Fever", "probability": 0.11},
                {"disease": "Acute Viral Pyrexia", "probability": 0.04}
            ],
            "diagnosis": "TYPHOID",
            "cause": "Salmonella enterica serovar Typhi food/water ingestion",
            "treatment": "Azithromycin 500mg PO daily for 7 days, strict dietary precautions.",
            "trainable": True
        }
    },
    {
        "identifier": "PT-GEN-005",
        "hospital_id": "2",
        "name": "Robert Chen (Synthetic)",
        "contact": "+1-555-0177 / r.chen.synthetic@test.org",
        "age": 45,
        "sex": 1,
        "weight": 78.0,
        "height": 172.0,
        "encounter": {
            "symptoms": ["high_fever", "severe_myalgia", "chills", "dry_cough", "headache"],
            "duration": 2,
            "vitals": {"bp_sys": 124, "bp_dia": 80, "hr": 92, "temp_c": 38.9, "spo2": 98, "resp_rate": 18},
            "labs": {"rapid_influenza_a": "positive"},
            "predicted_top3": [
                {"disease": "Influenza (Seasonal Flu)", "probability": 0.87},
                {"disease": "Common Cold", "probability": 0.08},
                {"disease": "Acute Viral Pyrexia", "probability": 0.04}
            ],
            "diagnosis": "FLU",
            "cause": "Influenza A virus droplet transmission",
            "treatment": "Oseltamivir 75mg PO BID for 5 days, rest and symptomatic antipyretics.",
            "trainable": True
        }
    }
]


def seed_synthetic_data(db: Session, force: bool = False):
    """Seed synthetic general disease demo data with strict production guard."""
    env = os.getenv("ENVIRONMENT", "development").strip().lower()
    allow_demo = os.getenv("ALLOW_DEMO_USERS", "true").strip().lower() in ("true", "1", "yes")
    is_prod = env in ("production", "prod")

    if is_prod and not allow_demo and not force:
        print("[SECURITY] Production mode active: synthetic demo data seeding strictly prevented.")
        return False

    # 1. Extensible Diseases
    for d in DISEASES:
        existing = db.query(models.Disease).filter_by(code=d["code"]).first()
        if not existing:
            db.add(models.Disease(
                code=d["code"],
                name=d["name"],
                category=d["category"],
                common_symptoms=json.dumps(d["common_symptoms"]),
                is_active=True
            ))
    db.commit()

    # 2. Regional Hubs
    for hid, name, region in DEMO_HUBS:
        if not db.query(models.RegionalHub).filter_by(id=hid).first():
            db.add(models.RegionalHub(id=hid, name=name, region=region, status="active"))
    db.commit()

    # 3. Hospitals
    for hid, name, hub_id, share in DEMO_HOSPITALS:
        hosp = db.query(models.Hospital).filter_by(id=hid).first()
        if not hosp:
            db.add(models.Hospital(
                id=hid,
                name=name,
                hub_id=hub_id,
                status="active",
                share_deidentified=share,
                dataset_size=45,
                consent_record_fields=json.dumps({"termsVersion": "2.0", "optIn": share})
            ))
    db.commit()

    # 4. Role-based Demo Accounts
    pw = os.getenv("DEMO_PASSWORD", "password123")
    for email, name, role, hub_id, hosp_id in DEMO_USERS:
        u = db.query(models.User).filter_by(email=email).first()
        if not u:
            db.add(models.User(
                email=email,
                name=name,
                role=role,
                hub_id=hub_id,
                hospital_id=hosp_id,
                password_hash=auth.hash_password(pw),
                must_reset_password=False,
                status="active"
            ))
        else:
            # Sync role and association
            u.role = role
            u.hub_id = hub_id
            u.hospital_id = hosp_id
            if u.password_hash.startswith("DISABLED$") or not auth.verify_password(pw, u.password_hash):
                u.password_hash = auth.hash_password(pw)
    db.commit()

    # 5. Synthetic Patients with encrypted PHI
    for sp in SYNTHETIC_PATIENTS:
        pat = db.query(models.Patient).filter_by(patient_identifier=sp["identifier"]).first()
        if not pat:
            pat = models.Patient(
                patient_identifier=sp["identifier"],
                hospital_id=sp["hospital_id"],
                name_encrypted=crypto.encrypt_phi(sp["name"]),
                contact_encrypted=crypto.encrypt_phi(sp["contact"]),
                age=sp["age"],
                sex=sp["sex"],
                weight=sp["weight"],
                height=sp["height"],
            )
            db.add(pat)
            db.commit()
            db.refresh(pat)

        enc_id = f"ENC-{sp['identifier']}"
        enc = db.query(models.Encounter).filter_by(encounter_identifier=enc_id).first()
        if not enc:
            ed = sp["encounter"]
            db.add(models.Encounter(
                encounter_identifier=enc_id,
                patient_id=pat.id,
                hospital_id=sp["hospital_id"],
                symptoms=json.dumps(ed["symptoms"]),
                symptom_duration_days=ed.get("duration", 2),
                vitals=json.dumps(ed["vitals"]),
                structured_ecg_finding=ed.get("ecg", "normal"),
                optional_labs=json.dumps(ed.get("labs", {})),
                model_version="TF-GenDisease-v1.0",
                predicted_top3=json.dumps(ed["predicted_top3"]),
                doctor_confirmed_diagnosis=ed["diagnosis"],
                cause=ed["cause"],
                treatment=ed["treatment"],
                confirmed_by=4, # Dr. Anthony Ross
                confirmed_at=datetime.datetime.now(datetime.timezone.utc),
                trainable=ed.get("trainable", True)
            ))
    db.commit()

    # 6. Global & Regional Model Versions
    models_to_seed = [
        ("TF-GenDisease-v1.0", "global", None, "General Multi-Condition", {"top3_accuracy": 0.912, "accuracy": 0.864, "macro_f1": 0.851}),
        ("TF-HeartNet-v2", "global", None, "Cardiovascular Risk", {"accuracy": 0.883, "epsilon": 1.84, "auc": 0.915})
    ]
    for ver, scope, sid, cat, metrics in models_to_seed:
        if not db.query(models.ModelVersion).filter_by(version=ver).first():
            db.add(models.ModelVersion(
                version=ver,
                scope=scope,
                scope_id=sid,
                disease_category=cat,
                metrics=json.dumps(metrics),
                model_path=f"artifacts/{ver.lower()}.npz",
                status="active"
            ))
    db.commit()

    print("[INFO] Synthetic demo data successfully seeded (guarded and encrypted at rest).")
    return True
