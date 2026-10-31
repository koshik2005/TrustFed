"""Phase 6 Comprehensive Test Suite: Role-Aware Dashboards,
Multi-Tier Data Scoping, Server-Side Security Guardrails, and Metric Correctness.
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SECRET_KEY"] = "phase6-role-dashboards-secure-key-2026-test"
os.environ["ENVIRONMENT"] = "development"

from main import app
from db.database import Base, engine, SessionLocal
from db import models
from db.migrations.v2_general_disease_migration import migrate_up
from services import auth

client = TestClient(app)


def setup_module(module):
    """Ensure database schema, hubs, hospitals, users, and encounters exist."""
    Base.metadata.create_all(bind=engine)
    migrate_up(engine)
    db = SessionLocal()
    try:
        # 1. Hubs
        hubs = [
            ("hub-fl-a", "Hub Alpha (North)", "North"),
            ("hub-fl-b", "Hub Beta (South)", "South"),
        ]
        for hid, name, reg in hubs:
            if not db.query(models.RegionalHub).filter_by(id=hid).first():
                db.add(models.RegionalHub(id=hid, name=name, region=reg, status="active"))

        # 2. Hospitals
        hosps = [
            ("hosp-fl-1", "Hospital 1 (Metro North)", "hub-fl-a", "active", False),
            ("hosp-fl-2", "Hospital 2 (Valley North)", "hub-fl-a", "active", True),
            ("hosp-fl-3", "Hospital 3 (Coast South)", "hub-fl-b", "active", True),
            ("hosp-fl-suspended", "Hospital Suspended", "hub-fl-b", "suspended", False),
            ("hosp-fl-low-records", "Hospital Sparse", "hub-fl-a", "active", False),
        ]
        for hid, name, hub_id, status, share in hosps:
            if not db.query(models.Hospital).filter_by(id=hid).first():
                db.add(models.Hospital(
                    id=hid,
                    name=name,
                    hub_id=hub_id,
                    status=status,
                    share_deidentified=share,
                    consent_recorded_by="admin@trustfed.ai",
                ))

        # 3. Users
        users = [
            ("dash_global_admin@trustfed.ai", "Global Admin Dash", "global_admin", None, None),
            ("dash_reg_a_admin@trustfed.ai", "Regional Admin A", "regional_admin", None, "hub-fl-a"),
            ("dash_reg_b_admin@trustfed.ai", "Regional Admin B", "regional_admin", None, "hub-fl-b"),
            ("dash_doc1@trustfed.ai", "Dr. One Metro", "doctor", "hosp-fl-1", None),
            ("dash_staff1@trustfed.ai", "Staff Metro", "hospital_staff", "hosp-fl-1", None),
            ("dash_doc2@trustfed.ai", "Dr. Two Valley", "doctor", "hosp-fl-2", None),
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

        # 4. Encounters for hosp-fl-1 (10 encounters) and hosp-fl-low-records (2 encounters)
        def _seed(hid, target):
            existing = db.query(models.Encounter).filter_by(hospital_id=hid).count()
            for i in range(target - existing):
                p = models.Patient(
                    patient_identifier=f"PT-{hid}-{i+1:04d}",
                    hospital_id=hid,
                    name_encrypted="enc_name_placeholder",
                    contact_encrypted="enc_contact_placeholder",
                    age=30 + i,
                    sex="male" if i % 2 == 0 else "female",
                    weight=70.0,
                    height=175.0
                )
                db.add(p)
                db.flush()

                e = models.Encounter(
                    patient_id=p.id,
                    hospital_id=hid,
                    symptoms=["fever", "cough", "sore throat"],
                    symptom_duration_days=3,
                    vitals={"temperature": 38.5, "heart_rate": 88},
                    structured_ecg="normal",
                    model_version="v2.0.0-initial",
                    top3_predictions=[
                        {"condition": "common cold", "probability": 0.72},
                        {"condition": "influenza", "probability": 0.18},
                        {"condition": "viral fever", "probability": 0.05}
                    ],
                    uncertainty_score=0.28,
                    doctor_confirmed_condition="common cold" if i % 2 == 0 else None,
                    cause="Viral upper respiratory infection" if i % 2 == 0 else None,
                    treatment="Rest, hydration, and paracetamol" if i % 2 == 0 else None,
                    trainable=(i % 2 == 0),
                    confirmed_by=1 if i % 2 == 0 else None
                )
                db.add(e)
            db.commit()

        _seed("hosp-fl-1", 10)
        _seed("hosp-fl-low-records", 2)

    finally:
        db.close()


def _token(email: str) -> str:
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=email).first()
        assert user, f"User {email} not found"
        return auth.create_token({
            "sub": user.email,
            "role": user.role,
            "name": user.name,
            "user_id": user.id,
            "hospital_id": user.hospital_id,
            "hub_id": user.hub_id,
        })
    finally:
        db.close()


# ── Hospital Dashboard Tests ──────────────────────────────────────────────────

def test_hospital_dashboard_scoped_data():
    """Hospital staff/doctor receives scoped metrics for their own hospital."""
    token = _token("dash_doc1@trustfed.ai")
    res = client.get("/api/v1/dashboard/hospital", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["hospital"]["id"] == "hosp-fl-1"
    assert data["hospital"]["name"] == "Hospital 1 (Metro North)"
    assert "patientsToday" in data
    assert "pendingConfirmationsCount" in data
    assert "totalEncounters" in data
    assert data["totalEncounters"] >= 10
    assert "localAccuracy" in data
    assert "top1Accuracy" in data["localAccuracy"]
    assert "top3Accuracy" in data["localAccuracy"]
    assert "contributionStatus" in data
    assert "currentModelVersion" in data
    assert "recentPredictions" in data

    # Verify recent predictions do NOT contain encrypted or raw PHI names
    for rec in data["recentPredictions"]:
        assert "name_encrypted" not in rec
        assert "contact_encrypted" not in rec
        assert "topCondition" in rec
        assert "topConfidence" in rec


def test_hospital_dashboard_cross_access_forbidden():
    """Hospital doctor attempting to view another hospital gets 403 Forbidden."""
    token = _token("dash_doc1@trustfed.ai")  # belongs to hosp-fl-1
    res = client.get("/api/v1/dashboard/hospital?hospital_id=hosp-fl-2", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert "cannot view another hospital's dashboard" in res.json()["detail"]


def test_regional_admin_forbidden_from_hospital_dashboard():
    """Regional admin cannot call hospital dashboard endpoint without being assigned or global admin."""
    token = _token("dash_reg_a_admin@trustfed.ai")
    res = client.get("/api/v1/dashboard/hospital?hospital_id=hosp-fl-1", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_global_admin_can_inspect_any_hospital_dashboard():
    """Global admin has authority to inspect any hospital's node dashboard."""
    token = _token("dash_global_admin@trustfed.ai")
    res = client.get("/api/v1/dashboard/hospital?hospital_id=hosp-fl-2", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["hospital"]["id"] == "hosp-fl-2"


def test_hospital_contribution_status_eligibility():
    """Check contribution eligibility reflects confirmed record count against threshold."""
    token_admin = _token("dash_global_admin@trustfed.ai")

    # hosp-fl-1 has >= 5 confirmed records -> eligible
    res1 = client.get("/api/v1/dashboard/hospital?hospital_id=hosp-fl-1", headers={"Authorization": f"Bearer {token_admin}"})
    assert res1.status_code == 200
    c1 = res1.json()["contributionStatus"]
    assert c1["eligible"] is True
    assert c1["confirmedCount"] >= 5

    # hosp-fl-low-records has < 5 confirmed records -> not eligible
    res_low = client.get("/api/v1/dashboard/hospital?hospital_id=hosp-fl-low-records", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_low.status_code == 200
    c_low = res_low.json()["contributionStatus"]
    assert c_low["eligible"] is False
    assert c_low["confirmedCount"] < c_low["minRequired"]


# ── Regional Hub Dashboard Tests ──────────────────────────────────────────────

def test_regional_dashboard_scoped_data():
    """Regional admin receives data strictly scoped to their assigned hub."""
    token = _token("dash_reg_a_admin@trustfed.ai")  # hub-fl-a
    res = client.get("/api/v1/dashboard/regional", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["hub"]["id"] == "hub-fl-a"
    assert data["hub"]["name"] == "Hub Alpha (North)"
    assert "regionalRecordVolume" in data
    assert "regionalModelPerformance" in data
    assert "eligibleHospitalsCount" in data
    assert "perDiseaseAccuracy" in data
    assert "hospitals" in data

    # Verify only hub-fl-a hospitals are in the list
    hosp_ids = [h["id"] for h in data["hospitals"]]
    assert "hosp-fl-1" in hosp_ids
    assert "hosp-fl-2" in hosp_ids
    assert "hosp-fl-3" not in hosp_ids  # hosp-fl-3 belongs to hub-fl-b!


def test_regional_dashboard_cross_hub_access_forbidden():
    """Regional admin attempting to view another hub gets 403 Forbidden."""
    token = _token("dash_reg_a_admin@trustfed.ai")  # hub-fl-a
    res = client.get("/api/v1/dashboard/regional?hub_id=hub-fl-b", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert "cannot view another regional hub's dashboard" in res.json()["detail"]


def test_hospital_user_forbidden_from_regional_dashboard():
    """Hospital staff/doctor cannot access the regional dashboard."""
    token = _token("dash_doc1@trustfed.ai")
    res = client.get("/api/v1/dashboard/regional", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_global_admin_can_inspect_any_regional_hub():
    """Global admin can query metrics for any regional hub."""
    token = _token("dash_global_admin@trustfed.ai")
    res = client.get("/api/v1/dashboard/regional?hub_id=hub-fl-b", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["hub"]["id"] == "hub-fl-b"
    hosp_ids = [h["id"] for h in data["hospitals"]]
    assert "hosp-fl-3" in hosp_ids


# ── Global Admin Dashboard Tests ──────────────────────────────────────────────

def test_global_dashboard_forbidden_for_non_admins():
    """Doctors, hospital staff, and regional admins are strictly rejected with 403."""
    doc_token = _token("dash_doc1@trustfed.ai")
    res1 = client.get("/api/v1/dashboard/global", headers={"Authorization": f"Bearer {doc_token}"})
    assert res1.status_code == 403

    reg_token = _token("dash_reg_a_admin@trustfed.ai")
    res2 = client.get("/api/v1/dashboard/global", headers={"Authorization": f"Bearer {reg_token}"})
    assert res2.status_code == 403


def test_global_dashboard_complete_governance_metrics():
    """Global admin dashboard contains all model versions, privacy accounting, and audit status."""
    token = _token("dash_global_admin@trustfed.ai")
    res = client.get("/api/v1/dashboard/global", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    data = res.json()

    # Network overview
    assert data["totalHubs"] >= 2
    assert data["totalHospitals"] >= 3
    assert data["recordVolume"]["totalEncounters"] >= 12

    # Model lineage and performance
    assert "currentModel" in data
    assert len(data["modelVersions"]) >= 1
    assert "perRegionAccuracy" in data
    assert len(data["perDiseaseAccuracy"]) >= 18

    # Privacy and Cryptographic Ledger Verification
    assert "privacySummary" in data
    assert "actualEpsilon" in data["privacySummary"] or "epsilon" in data["privacySummary"]
    assert "fairnessSummary" in data
    assert "auditVerification" in data
    assert data["auditVerification"]["chainIntact"] is True
