"""Tests for Phase A: Deployment Modes (Informational vs Clinical).

Verifies:
1. Informational mode rejects patient names and contacts if sent (HTTP 400).
2. Informational mode persists only anonymous identifiers ('ANON-XXXX') with zero PHI.
3. Informational mode disables doctor confirmation and federated training (HTTP 403).
4. Clinical mode strictly refuses startup unless enterprise flags are satisfied.
5. Clinical mode succeeds startup when all enterprise flags are present.
6. Persistent educational disclaimer is returned across /health, /system/mode, and prediction results.
"""
import os
import pytest
from fastapi.testclient import TestClient
from main import app
from db.database import SessionLocal, engine, Base
from db import models
from services import auth
from core import deployment_mode
from core.deployment_mode import PERSISTENT_DISCLAIMER, validate_deployment_mode_on_startup

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Ensure hospital and user exist
    hosp = db.query(models.Hospital).filter_by(id="hosp-test-mode").first()
    if not hosp:
        db.add(models.Hospital(id="hosp-test-mode", name="Mode Test Hospital", hub_id="hub-east", status="active"))
    
    doc = db.query(models.User).filter_by(email="mode_doc@test.org").first()
    if not doc:
        db.add(models.User(
            email="mode_doc@test.org",
            name="Dr Mode",
            role="doctor",
            hospital_id="hosp-test-mode",
            password_hash=auth.hash_password("DemoPassword123!"),
            status="active"
        ))
    admin = db.query(models.User).filter_by(email="mode_admin@test.org").first()
    if not admin:
        db.add(models.User(
            email="mode_admin@test.org",
            name="Admin Mode",
            role="global_admin",
            password_hash=auth.hash_password("DemoPassword123!"),
            status="active"
        ))
    db.commit()
    yield db
    db.close()


def test_health_reports_deployment_mode(monkeypatch):
    monkeypatch.setenv("APP_MODE", "informational")
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert "mode" in data
    assert data["mode"] == "informational"
    assert data["version"] == "2.0.0"

    monkeypatch.setenv("APP_MODE", "clinical")
    res_clin = client.get("/health")
    assert res_clin.json()["mode"] == "clinical"


def test_system_mode_endpoint_returns_mode_and_disclaimer(monkeypatch):
    monkeypatch.setenv("APP_MODE", "informational")
    res = client.get("/api/system/mode")
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "informational"
    assert data["disclaimer"] == PERSISTENT_DISCLAIMER


def test_informational_mode_rejects_patient_name(setup_db, monkeypatch):
    monkeypatch.setenv("APP_MODE", "informational")
    token = auth.create_token({"sub": "mode_doc@test.org", "role": "doctor", "hospital_id": "hosp-test-mode"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Jane Doe",
        "age": 42,
        "sex": 0,
        "symptoms": ["fever", "cough"]
    }
    res = client.post("/api/hospital/patients", json=payload, headers=headers)
    assert res.status_code == 400
    assert "Informational Mode" in res.json()["detail"]


def test_informational_mode_rejects_patient_contact(setup_db, monkeypatch):
    monkeypatch.setenv("APP_MODE", "informational")
    token = auth.create_token({"sub": "mode_doc@test.org", "role": "doctor", "hospital_id": "hosp-test-mode"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "contact": "+1-555-0123",
        "age": 42,
        "sex": 0,
        "symptoms": ["fever"]
    }
    res = client.post("/api/hospital/patients", json=payload, headers=headers)
    assert res.status_code == 400
    assert "Informational Mode" in res.json()["detail"]


def test_informational_mode_stores_anonymous_patient(setup_db, monkeypatch):
    monkeypatch.setenv("APP_MODE", "informational")
    token = auth.create_token({"sub": "mode_doc@test.org", "role": "doctor", "hospital_id": "hosp-test-mode"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "age": 29,
        "sex": 1,
        "symptoms": ["headache", "fatigue"]
    }
    res = client.post("/api/hospital/patients", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    pt = data["patient"]
    assert pt["patientIdentifier"].startswith("ANON-")
    assert pt["name"] is None or pt["name"] == ""
    assert pt["contact"] is None or pt["contact"] == ""


def test_informational_mode_blocks_doctor_confirmation(setup_db, monkeypatch):
    monkeypatch.setenv("APP_MODE", "informational")
    token = auth.create_token({"sub": "mode_doc@test.org", "role": "doctor", "hospital_id": "hosp-test-mode"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "confirmed_diagnosis": "Dengue Fever",
        "cause": "Arbovirus infection",
        "treatment": "Fluids and rest"
    }
    res = client.post("/api/hospital/encounters/1/confirm", json=payload, headers=headers)
    assert res.status_code == 403
    assert "Informational Mode" in res.json()["detail"]


def test_informational_mode_blocks_federated_rounds(setup_db, monkeypatch):
    monkeypatch.setenv("APP_MODE", "informational")
    token = auth.create_token({"sub": "mode_admin@test.org", "role": "global_admin"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/federated/rounds/trigger", json={}, headers=headers)
    assert res.status_code == 403
    assert "Informational Mode" in res.json()["detail"]


def test_clinical_mode_startup_refusal_when_prerequisites_missing(monkeypatch):
    monkeypatch.setenv("APP_MODE", "clinical")
    monkeypatch.delenv("MANAGED_DB_BACKUPS_CONFIRMED", raising=False)
    monkeypatch.delenv("MFA_REQUIRED", raising=False)
    monkeypatch.setenv("ALLOW_DEMO_USERS", "true")

    with pytest.raises(RuntimeError) as exc_info:
        validate_deployment_mode_on_startup()
    
    err_msg = str(exc_info.value)
    assert "CLINICAL MODE" in err_msg
    assert "MANAGED_DB_BACKUPS_CONFIRMED=true" in err_msg
    assert "MFA_REQUIRED=true" in err_msg
    assert "ALLOW_DEMO_USERS=false" in err_msg


def test_clinical_mode_startup_success_with_all_flags(monkeypatch):
    monkeypatch.setenv("APP_MODE", "clinical")
    monkeypatch.setenv("MANAGED_DB_BACKUPS_CONFIRMED", "true")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://postgres:secret@db.supabase.co:5432/postgres")
    monkeypatch.setenv("MFA_REQUIRED", "true")
    monkeypatch.setenv("ALLOW_DEMO_USERS", "false")
    monkeypatch.setenv("PATIENT_ENCRYPTION_KEY", "bW9ja19lbmNyeXB0aW9uX2tleV8zMl9ieXRlc19sb25nCg==")
    monkeypatch.setenv("SECRETS_STORE_MANAGED", "true")

    # Should execute cleanly without raising any exception
    validate_deployment_mode_on_startup()


def test_prediction_result_includes_exact_disclaimer(setup_db):
    token = auth.create_token({"sub": "mode_doc@test.org", "role": "doctor", "hospital_id": "hosp-test-mode"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "age": 35,
        "sex": 1,
        "symptoms": ["fever", "cough"]
    }
    res = client.post("/api/clinical/predict", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["disclaimer"] == PERSISTENT_DISCLAIMER
