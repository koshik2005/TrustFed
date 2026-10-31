"""Phase 7 Test Suite: Security Hardening, Security Headers, Health Endpoints,
Right to Erasure, Fine-Grained Consent Management, Retention Pruning, and PHI Log Redaction.
"""
import io
import json
import logging
import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SECRET_KEY"] = "phase7-hardening-and-compliance-test-key-2026"
os.environ["ENVIRONMENT"] = "production"

from main import app
from db.database import Base, engine, SessionLocal
from db import models
from db.migrations.v2_general_disease_migration import migrate_up
from services import auth
from core.logging_config import PHIRedactionFilter, redact_phi_text

client = TestClient(app)


def setup_module(module):
    """Ensure database schema, hubs, hospitals, and users exist."""
    Base.metadata.create_all(bind=engine)
    migrate_up(engine)
    db = SessionLocal()
    try:
        # Hub & Hospital
        if not db.query(models.RegionalHub).filter_by(id="hub-sec-1").first():
            db.add(models.RegionalHub(id="hub-sec-1", name="Security Hub", region="Central", status="active"))

        if not db.query(models.Hospital).filter_by(id="hosp-sec-1").first():
            db.add(models.Hospital(
                id="hosp-sec-1",
                name="Security Hospital 1",
                hub_id="hub-sec-1",
                status="active",
                share_deidentified=False
            ))

        if not db.query(models.Hospital).filter_by(id="hosp-sec-2").first():
            db.add(models.Hospital(
                id="hosp-sec-2",
                name="Security Hospital 2",
                hub_id="hub-sec-1",
                status="active",
                share_deidentified=False
            ))

        # Users
        users = [
            ("sec_admin@trustfed.ai", "Sec Admin", "global_admin", None, None),
            ("sec_doc1@trustfed.ai", "Sec Doctor 1", "doctor", "hosp-sec-1", None),
            ("sec_staff1@trustfed.ai", "Sec Staff 1", "hospital_staff", "hosp-sec-1", None),
            ("sec_doc2@trustfed.ai", "Sec Doctor 2", "doctor", "hosp-sec-2", None),
        ]
        for email, name, role, hid, hub_id in users:
            if not db.query(models.User).filter_by(email=email).first():
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


def _token(email: str) -> str:
    db = SessionLocal()
    try:
        u = db.query(models.User).filter_by(email=email).first()
        return auth.create_token({
            "sub": u.email,
            "role": u.role,
            "name": u.name,
            "user_id": u.id,
            "hospital_id": u.hospital_id,
            "hub_id": u.hub_id,
        })
    finally:
        db.close()


# ── 1. Security Headers & Compression ─────────────────────────────────────────

def test_security_headers_present_on_all_responses():
    """Verify CSP, HSTS, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy."""
    res = client.get("/health")
    assert res.status_code == 200

    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in headers.get("Content-Security-Policy", "")
    assert "max-age=31536000" in headers.get("Strict-Transport-Security", "")


def test_api_cache_control_no_store():
    """Verify sensitive API responses enforce no-store, no-cache."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    cache_ctrl = res.headers.get("Cache-Control", "")
    assert "no-store" in cache_ctrl
    assert "no-cache" in cache_ctrl


# ── 2. Health Endpoints ───────────────────────────────────────────────────────

def test_health_endpoints_database_ping_and_version():
    """Verify /health, /api/health, and /api/v1/health respond with database ping and version."""
    for path in ["/health", "/api/health", "/api/v1/health"]:
        res = client.get(path)
        assert res.status_code == 200, f"Failed on {path}: {res.text}"
        data = res.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["version"] == "2.0.0"


# ── 3. Data Deletion Controls (Right to Erasure / DPDP Act 2023) ──────────────

def test_patient_erasure_deletes_records_and_creates_audit_entry():
    """Verify DELETE /hospital/patients/{id} removes patient, encounters, and records audit."""
    db = SessionLocal()
    try:
        # Create a test patient with encounters
        p = models.Patient(
            patient_identifier="PT-SEC-DELETE-001",
            hospital_id="hosp-sec-1",
            name_encrypted="enc_name_delete_test",
            contact_encrypted="enc_contact_delete_test",
            age=50,
            sex="male",
            weight=75.0,
            height=180.0
        )
        db.add(p)
        db.flush()

        enc = models.Encounter(
            encounter_identifier=f"ENC-SEC-{p.id}",
            patient_id=p.id,
            hospital_id="hosp-sec-1",
            symptoms=json.dumps(["fever", "cough"]),
            symptom_duration_days=2,
            vitals=json.dumps({"temperature": 38.0}),
            structured_ecg_finding="normal",
            model_version="v2.0.0",
            predicted_top3=json.dumps([{"disease": "common cold", "probability": 0.8}]),
            trainable=False
        )
        db.add(enc)
        db.commit()
        p_id = p.id
    finally:
        db.close()

    token = _token("sec_staff1@trustfed.ai")
    res = client.delete(f"/api/v1/hospital/patients/{p_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "success"
    assert res.json()["deletedEncountersCount"] >= 1

    # Verify patient and encounter are permanently gone from database
    db = SessionLocal()
    try:
        assert db.query(models.Patient).filter_by(id=p_id).first() is None
        assert db.query(models.Encounter).filter_by(patient_id=p_id).first() is None

        # Verify audit ledger has erasure entry
        last_audit = db.query(models.AuditLog).filter_by(event_type="erasure").order_by(models.AuditLog.id.desc()).first()
        assert last_audit is not None
        assert "PT-SEC-DELETE-001" in last_audit.description
    finally:
        db.close()


def test_cross_hospital_erasure_forbidden():
    """Staff from Hosp 1 cannot delete a patient belonging to Hosp 2."""
    db = SessionLocal()
    try:
        p2 = db.query(models.Patient).filter_by(patient_identifier="PT-SEC-HOSP2-001").first()
        if not p2:
            p2 = models.Patient(
                patient_identifier="PT-SEC-HOSP2-001",
                hospital_id="hosp-sec-2",
                name_encrypted="enc_hosp2",
                contact_encrypted="enc_hosp2",
                age=30,
                sex="female"
            )
            db.add(p2)
            db.commit()
        p2_id = p2.id
    finally:
        db.close()

    # Hosp 1 user attempts deletion
    token1 = _token("sec_doc1@trustfed.ai")
    res = client.delete(f"/api/v1/hospital/patients/{p2_id}", headers={"Authorization": f"Bearer {token1}"})
    assert res.status_code == 403
    assert "belongs to another hospital" in res.json()["detail"]


# ── 4. Consent Management Controls ────────────────────────────────────────────

def test_consent_management_grant_and_revoke_flow():
    """Verify POST /consent/manage grants, revokes, and syncs hospital share settings."""
    token = _token("sec_doc1@trustfed.ai")

    # 1. Grant consent
    res_grant = client.post(
        "/api/v1/consent/manage",
        json={
            "hospital_id": "hosp-sec-1",
            "consent_type": "FEDERATED_TRAINING_DEIDENTIFIED",
            "status": "granted"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_grant.status_code == 200, res_grant.text
    assert res_grant.json()["consentStatus"] == "granted"
    assert res_grant.json()["shareDeidentified"] is True

    # 2. Revoke consent
    res_revoke = client.post(
        "/api/v1/consent/manage",
        json={
            "hospital_id": "hosp-sec-1",
            "consent_type": "FEDERATED_TRAINING_DEIDENTIFIED",
            "status": "revoked"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_revoke.status_code == 200, res_revoke.text
    assert res_revoke.json()["consentStatus"] == "revoked"
    assert res_revoke.json()["shareDeidentified"] is False


def test_cross_hospital_consent_management_forbidden():
    """Hosp 1 doctor cannot manage consent for Hosp 2."""
    token1 = _token("sec_doc1@trustfed.ai")
    res = client.post(
        "/api/v1/consent/manage",
        json={
            "hospital_id": "hosp-sec-2",
            "consent_type": "FEDERATED_TRAINING_DEIDENTIFIED",
            "status": "granted"
        },
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert res.status_code == 403


# ── 5. Data Retention Automated Pruning ───────────────────────────────────────

def test_data_retention_pruning_policy():
    """Verify POST /data-retention/prune removes stale unconfirmed encounters."""
    db = SessionLocal()
    try:
        # Add an encounter from 100 days ago (unconfirmed)
        import datetime
        stale_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=100)
        p = db.query(models.Patient).filter_by(patient_identifier="PT-SEC-RETENTION-001").first()
        if not p:
            p = models.Patient(
                patient_identifier="PT-SEC-RETENTION-001",
                hospital_id="hosp-sec-1",
                name_encrypted="enc_retention",
                contact_encrypted="enc_retention",
                age=60,
                sex="male"
            )
            db.add(p)
            db.flush()

        import time
        stale_enc = models.Encounter(
            encounter_identifier=f"ENC-STALE-{p.id}-{int(time.time()*1000)}",
            patient_id=p.id,
            hospital_id="hosp-sec-1",
            symptoms=json.dumps(["cough"]),
            vitals=json.dumps({"temperature": 37.0}),
            created_at=stale_date,
            doctor_confirmed_diagnosis=None
        )
        db.add(stale_enc)
        db.commit()
    finally:
        db.close()

    token = _token("sec_admin@trustfed.ai")
    res = client.post(
        "/api/v1/data-retention/prune",
        json={
            "hospital_id": "hosp-sec-1",
            "days_unconfirmed": 90,
            "purge_revoked_consent": False
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200, res.text
    assert res.json()["unconfirmedEncountersPruned"] >= 1


# ── 6. Structured Logging with PHI Redaction Filter ───────────────────────────

def test_phi_redaction_filter_scrubs_patient_identifiers_and_tokens():
    """Verify PHIRedactionFilter masks patient IDs, phone numbers, and bearer tokens."""
    raw_message = "Encounter recorded for PT-HOSP-9999 with phone +1-555-0199 and token Bearer eyJhbGciOi..."
    scrubbed = redact_phi_text(raw_message)

    assert "PT-HOSP-9999" not in scrubbed
    assert "[REDACTED_PATIENT_ID]" in scrubbed
    assert "+1-555-0199" not in scrubbed
    assert "[REDACTED_PHONE]" in scrubbed
    assert "Bearer [REDACTED_TOKEN]" in scrubbed

    # Test via logging framework
    logger = logging.getLogger("test_phi_logger")
    logger.setLevel(logging.INFO)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(PHIRedactionFilter())
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    logger.info("Processing intake for patient PT-123456 at local clinic node.")
    output = stream.getvalue()
    assert "PT-123456" not in output
    assert "[REDACTED_PATIENT_ID]" in output
