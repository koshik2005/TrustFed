"""Phase 3 tests: Hospital patient entry, clinical validation, doctor confirmation,
and cross-tier de-identification.

Covers all Phase 3 acceptance criteria:
1. Cross-hospital access returns 403/404.
2. Staff cannot confirm encounters (returns 403).
3. Unconfirmed records are never trainable (trainable == False).
4. Doctor confirmation workflow sets trainable = True and records etiology & remedy.
5. Patient names and contacts are encrypted at rest and NEVER appear in regional or global API responses.
6. Server-side validation rejects impossible clinical demographics, vitals, and symptoms.
"""
import json
import os
import sys
import uuid
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SECRET_KEY"] = "phase3-super-secure-production-ready-key-2026-test"
os.environ["ENVIRONMENT"] = "development"

from main import app
from db.database import Base, engine, SessionLocal
from db import models
from db.migrations.v2_general_disease_migration import migrate_up
from services import auth, crypto, store

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)
    migrate_up(engine)
    db = SessionLocal()
    try:
        # Create hubs and hospitals for cross-tenancy tests
        hub = db.query(models.RegionalHub).filter_by(id="hub-p3").first()
        if not hub:
            hub = models.RegionalHub(id="hub-p3", name="Hub Phase 3", region="Central", status="active")
            db.add(hub)

        h1 = db.query(models.Hospital).filter_by(id="hosp-p3-1").first()
        if not h1:
            db.add(models.Hospital(id="hosp-p3-1", name="Hospital P3 Alpha", hub_id="hub-p3", status="active", share_deidentified=True))
        h2 = db.query(models.Hospital).filter_by(id="hosp-p3-2").first()
        if not h2:
            db.add(models.Hospital(id="hosp-p3-2", name="Hospital P3 Beta", hub_id="hub-p3", status="active", share_deidentified=True))

        # Users: H1 staff, H1 doctor, H2 staff, H2 doctor, Regional Admin, Global Admin
        users_to_seed = [
            ("p3_staff1@trustfed.ai", "Staff Alpha", "hospital_staff", "hosp-p3-1", None),
            ("p3_doc1@trustfed.ai", "Dr. Alpha", "doctor", "hosp-p3-1", None),
            ("p3_staff2@trustfed.ai", "Staff Beta", "hospital_staff", "hosp-p3-2", None),
            ("p3_doc2@trustfed.ai", "Dr. Beta", "doctor", "hosp-p3-2", None),
            ("p3_reg@trustfed.ai", "Regional Admin P3", "regional_admin", None, "hub-p3"),
            ("p3_global@trustfed.ai", "Global Admin P3", "global_admin", None, None),
        ]
        for email, name, role, hid, hub_id in users_to_seed:
            u = db.query(models.User).filter_by(email=email).first()
            if not u:
                db.add(models.User(
                    email=email,
                    name=name,
                    role=role,
                    hospital_id=hid,
                    hub_id=hub_id,
                    must_reset_password=False,
                    status="active",
                    password_hash=auth.hash_password("Pass123!SecureClinical")
                ))
        db.commit()
    finally:
        db.close()


def _login(email: str, password: str = "Pass123!SecureClinical") -> str:
    # Use distinct IP per call to avoid rate limits
    ip = f"10.77.{(hash(email) % 200) + 1}.{(uuid.uuid4().int % 250) + 1}"
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers={"X-Forwarded-For": ip}
    )
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["token"]


def test_clinical_validation_rejects_impossible_demographics():
    token = _login("p3_staff1@trustfed.ai")
    headers = {"Authorization": f"Bearer {token}"}

    # Negative age
    res = client.post("/api/v1/hospital/patients", json={
        "name": "Invalid Age", "age": -5, "sex": 1
    }, headers=headers)
    assert res.status_code == 422
    assert "age" in res.json()["detail"]["errors"]

    # Impossibly high age (>125)
    res = client.post("/api/v1/hospital/patients", json={
        "name": "Invalid Age", "age": 145, "sex": 1
    }, headers=headers)
    assert res.status_code == 422
    assert "age" in res.json()["detail"]["errors"]

    # Missing sex
    res = client.post("/api/v1/hospital/patients", json={
        "name": "Missing Sex", "age": 30, "sex": ""
    }, headers=headers)
    assert res.status_code == 422
    assert "sex" in res.json()["detail"]["errors"]

    # Impossible weight (< 0.5 kg or > 450 kg)
    res = client.post("/api/v1/hospital/patients", json={
        "name": "Invalid Weight", "age": 30, "sex": 1, "weight": 600.0
    }, headers=headers)
    assert res.status_code == 422
    assert "weight" in res.json()["detail"]["errors"]

    # Impossible height (< 30 cm or > 260 cm)
    res = client.post("/api/v1/hospital/patients", json={
        "name": "Invalid Height", "age": 30, "sex": 1, "height": 12.0
    }, headers=headers)
    assert res.status_code == 422
    assert "height" in res.json()["detail"]["errors"]


def test_clinical_validation_rejects_impossible_vitals_and_symptoms():
    token = _login("p3_staff1@trustfed.ai")
    headers = {"Authorization": f"Bearer {token}"}

    # Empty symptoms array when initial encounter attempted
    res = client.post("/api/v1/hospital/patients", json={
        "name": "No Symptoms", "age": 40, "sex": 0, "symptoms": []
    }, headers=headers)
    assert res.status_code == 422
    assert "symptoms" in res.json()["detail"]["errors"]

    # Impossible temperature (< 30°C or > 45°C)
    res = client.post("/api/v1/hospital/patients", json={
        "name": "Extreme Temp", "age": 40, "sex": 0, "symptoms": ["fever"],
        "vitals": {"temp_c": 52.0}
    }, headers=headers)
    assert res.status_code == 422
    assert "vitals.temp" in res.json()["detail"]["errors"]

    # Systolic <= Diastolic pressure violation
    res = client.post("/api/v1/hospital/patients", json={
        "name": "Inverted BP", "age": 40, "sex": 0, "symptoms": ["chest_pain"],
        "vitals": {"bp_sys": 80, "bp_dia": 110}
    }, headers=headers)
    assert res.status_code == 422
    assert "vitals.bp" in res.json()["detail"]["errors"]

    # Impossible SpO2 (> 100% or < 50%)
    res = client.post("/api/v1/hospital/patients", json={
        "name": "Super SpO2", "age": 40, "sex": 0, "symptoms": ["cough"],
        "vitals": {"spo2": 115.0}
    }, headers=headers)
    assert res.status_code == 422
    assert "vitals.spo2" in res.json()["detail"]["errors"]

    # Invalid structured ECG finding
    res = client.post("/api/v1/hospital/patients", json={
        "name": "Bad ECG", "age": 40, "sex": 0, "symptoms": ["chest_pain"],
        "structured_ecg_finding": "extraterrestrial_wave"
    }, headers=headers)
    assert res.status_code == 422
    assert "structured_ecg_finding" in res.json()["detail"]["errors"]


def test_patient_registration_encrypts_name_and_contact_at_rest():
    token = _login("p3_staff1@trustfed.ai")
    headers = {"Authorization": f"Bearer {token}"}

    unique_name = f"Alice P3 Encrypted {uuid.uuid4().hex[:6]}"
    unique_contact = f"+1-555-{uuid.uuid4().int % 9000 + 1000}"

    res = client.post("/api/v1/hospital/patients", json={
        "name": unique_name,
        "contact": unique_contact,
        "age": 42,
        "sex": 0,
        "weight": 68.0,
        "height": 165.0,
        "symptoms": ["fever", "headache", "body_ache"],
        "symptom_duration_days": 3,
        "vitals": {"temp_c": 38.8, "bp_sys": 120, "bp_dia": 80, "hr": 92, "spo2": 98, "resp_rate": 18},
        "structured_ecg_finding": "normal"
    }, headers=headers)

    assert res.status_code == 200, res.text
    data = res.json()
    pt = data["patient"]
    enc = data["encounter"]

    # Verified in API response for hospital staff
    assert pt["name"] == unique_name
    assert pt["contact"] == unique_contact
    assert pt["age"] == 42
    assert enc is not None
    assert enc["trainable"] is False  # UNCONFIRMED RECORD MUST NEVER BE TRAINABLE
    assert enc["status"] == "pending"
    assert len(enc["predictedTop3"]) == 3

    # Direct DB inspection: ensure ciphertext is stored, NOT plaintext
    db = SessionLocal()
    try:
        db_patient = db.query(models.Patient).filter_by(id=pt["id"]).first()
        assert db_patient is not None
        assert db_patient.name_encrypted != unique_name
        assert db_patient.contact_encrypted != unique_contact
        # Decrypting matches original
        assert crypto.decrypt_phi(db_patient.name_encrypted) == unique_name
        assert crypto.decrypt_phi(db_patient.contact_encrypted) == unique_contact
    finally:
        db.close()


def test_cross_hospital_access_returns_403():
    token1 = _login("p3_staff1@trustfed.ai")  # Hospital 1
    token2_staff = _login("p3_staff2@trustfed.ai")  # Hospital 2 Staff
    token2_doc = _login("p3_doc2@trustfed.ai")  # Hospital 2 Doctor

    # Create patient at Hospital 1
    res = client.post("/api/v1/hospital/patients", json={
        "name": "Secret H1 Patient",
        "contact": "+1-555-0001",
        "age": 29,
        "sex": 1,
        "symptoms": ["cough", "runny_nose"],
    }, headers={"Authorization": f"Bearer {token1}"})
    assert res.status_code == 200
    pt1_id = res.json()["patient"]["id"]
    enc1_id = res.json()["encounter"]["id"]

    # Hospital 2 staff attempts to read Hospital 1 patient
    res_cross_pt = client.get(
        f"/api/v1/hospital/patients/{pt1_id}",
        headers={"Authorization": f"Bearer {token2_staff}"}
    )
    assert res_cross_pt.status_code == 403
    assert "belongs to another hospital" in res_cross_pt.json()["detail"]

    # Hospital 2 staff attempts to create encounter for Hospital 1 patient
    res_cross_add_enc = client.post(
        f"/api/v1/hospital/patients/{pt1_id}/encounters",
        json={"symptoms": ["fever"]},
        headers={"Authorization": f"Bearer {token2_staff}"}
    )
    assert res_cross_add_enc.status_code == 403

    # Hospital 2 staff attempts to view Hospital 1 encounter
    res_cross_enc = client.get(
        f"/api/v1/hospital/encounters/{enc1_id}",
        headers={"Authorization": f"Bearer {token2_staff}"}
    )
    assert res_cross_enc.status_code == 403

    # Hospital 2 doctor attempts to confirm Hospital 1 encounter
    res_cross_confirm = client.post(
        f"/api/v1/hospital/encounters/{enc1_id}/confirm",
        json={"confirmed_diagnosis": "COLD", "cause": "Viral rhinitis", "treatment": "Rest"},
        headers={"Authorization": f"Bearer {token2_doc}"}
    )
    assert res_cross_confirm.status_code == 403


def test_staff_cannot_confirm_encounters():
    token_staff = _login("p3_staff1@trustfed.ai")
    headers_staff = {"Authorization": f"Bearer {token_staff}"}

    # Create patient with encounter
    res = client.post("/api/v1/hospital/patients", json={
        "name": "Staff Confirmation Test Patient",
        "contact": "+1-555-0002",
        "age": 55,
        "sex": 1,
        "symptoms": ["chest_pain", "breathlessness"],
        "vitals": {"bp_sys": 150, "bp_dia": 95, "hr": 105}
    }, headers=headers_staff)
    assert res.status_code == 200
    enc_id = res.json()["encounter"]["id"]

    # Staff attempts to confirm diagnosis
    res_confirm = client.post(
        f"/api/v1/hospital/encounters/{enc_id}/confirm",
        json={
            "confirmed_diagnosis": "CARDIAC_CAD",
            "cause": "Ischemic heart disease",
            "treatment": "Aspirin 75mg, Atorvastatin 40mg, Cardiology consult"
        },
        headers=headers_staff
    )
    # MUST return 403 Forbidden!
    assert res_confirm.status_code == 403
    assert "Staff cannot mark records confirmed" in res_confirm.json()["detail"]

    # Verify encounter remains unconfirmed and trainable is FALSE
    db = SessionLocal()
    try:
        enc = db.query(models.Encounter).filter_by(id=enc_id).first()
        assert enc.trainable is False
        assert enc.doctor_confirmed_diagnosis is None
    finally:
        db.close()


def test_doctor_confirmation_workflow_marks_trainable():
    token_staff = _login("p3_staff1@trustfed.ai")
    token_doc = _login("p3_doc1@trustfed.ai")

    # 1. Staff creates patient & encounter
    res = client.post("/api/v1/hospital/patients", json={
        "name": "Dengue Clinical Case",
        "contact": "+1-555-0003",
        "age": 36,
        "sex": 0,
        "symptoms": ["high_fever", "retro_orbital_pain", "severe_joint_pain", "rash"],
        "symptom_duration_days": 4,
        "vitals": {"temp_c": 39.5, "bp_sys": 110, "bp_dia": 70, "hr": 96, "spo2": 98, "resp_rate": 18},
        "optional_labs": {"platelets": 75}
    }, headers={"Authorization": f"Bearer {token_staff}"})
    assert res.status_code == 200
    enc_id = res.json()["encounter"]["id"]

    # Before confirmation: trainable must be False
    assert res.json()["encounter"]["trainable"] is False
    assert res.json()["encounter"]["status"] == "pending"

    # 2. Doctor confirms diagnosis
    confirm_payload = {
        "confirmed_diagnosis": "DENGUE",
        "cause": "Aedes aegypti vector exposure with thrombocytopenia",
        "treatment": "Strict oral fluid replacement, paracetamol 650mg QDS, avoid NSAIDs, monitor platelets daily"
    }
    res_confirm = client.post(
        f"/api/v1/hospital/encounters/{enc_id}/confirm",
        json=confirm_payload,
        headers={"Authorization": f"Bearer {token_doc}"}
    )
    assert res_confirm.status_code == 200, res_confirm.text
    data = res_confirm.json()

    assert data["trainable"] is True  # NOW TRAINABLE!
    assert data["status"] == "confirmed"
    assert data["doctorConfirmedDiagnosis"] == "DENGUE"
    assert data["cause"] == confirm_payload["cause"]
    assert data["treatment"] == confirm_payload["treatment"]
    assert data["confirmedByName"] == "Dr. Alpha"

    # Verify audit log recorded the confirmation
    db = SessionLocal()
    try:
        audit = db.query(models.AuditLog).filter_by(event_type="diagnosis_confirmed").order_by(models.AuditLog.id.desc()).first()
        assert audit is not None
        assert "DENGUE" in audit.description
        assert "Dr. Alpha" in audit.description
    finally:
        db.close()


def test_patient_names_never_appear_in_regional_or_global_api_response():
    token_staff = _login("p3_staff1@trustfed.ai")
    token_reg = _login("p3_reg@trustfed.ai")
    token_global = _login("p3_global@trustfed.ai")

    secret_name = f"ConfidentialPatient_{uuid.uuid4().hex[:8]}"
    secret_contact = "confidential.patient@classified-health.org"

    # Create patient at Hospital 1
    res = client.post("/api/v1/hospital/patients", json={
        "name": secret_name,
        "contact": secret_contact,
        "age": 48,
        "sex": 1,
        "symptoms": ["fever", "chills"],
    }, headers={"Authorization": f"Bearer {token_staff}"})
    assert res.status_code == 200

    # 1. Regional admin feed
    res_reg = client.get("/api/v1/regional/encounters", headers={"Authorization": f"Bearer {token_reg}"})
    assert res_reg.status_code == 200
    reg_data = res_reg.json()

    # Raw string check: confidential name and contact MUST NOT appear anywhere in the HTTP response body
    assert secret_name not in res_reg.text, "Patient name leaked into regional API response!"
    assert secret_contact not in res_reg.text, "Patient contact leaked into regional API response!"

    for item in reg_data["items"]:
        assert "name" not in item, f"Key 'name' found in de-identified item: {item}"
        assert "contact" not in item, f"Key 'contact' found in de-identified item: {item}"
        assert "patient_name" not in item
        assert "patientIdentifier" in item  # Pseudonym is allowed

    # 2. Global admin feed
    res_glob = client.get("/api/v1/admin/encounters", headers={"Authorization": f"Bearer {token_global}"})
    assert res_glob.status_code == 200
    glob_data = res_glob.json()

    assert secret_name not in res_glob.text, "Patient name leaked into global API response!"
    assert secret_contact not in res_glob.text, "Patient contact leaked into global API response!"

    for item in glob_data["items"]:
        assert "name" not in item
        assert "contact" not in item
        assert "patientIdentifier" in item
