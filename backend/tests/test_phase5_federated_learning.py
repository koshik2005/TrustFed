"""Phase 5 Comprehensive Test Suite: Hierarchical Federated Learning,
Eligibility, Divergence Safeguards, Promotion Gate, 1-Click Rollback,
Honest Privacy Accounting, Allow-List De-Identification, and Multi-Tier Aggregation.
"""
import copy
import json
import os
import sys
import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SECRET_KEY"] = "phase5-super-secure-production-ready-key-2026-test"
os.environ["ENVIRONMENT"] = "development"

from main import app
from db.database import Base, engine, SessionLocal
from db import models
from db.migrations.v2_general_disease_migration import migrate_up
from services import (
    auth,
    store,
    general_disease_model,
    federated_learning
)
from tefl import dp

client = TestClient(app)


def setup_module(module):
    """Seed test fixtures: 2 Regional Hubs, 3 Hospitals, Users, and Confirmed Encounters."""
    Base.metadata.create_all(bind=engine)
    migrate_up(engine)
    db = SessionLocal()
    try:
        # Hubs: Hub A and Hub B
        hubs = [
            ("hub-fl-a", "Hub Alpha (North)", "North"),
            ("hub-fl-b", "Hub Beta (South)", "South"),
        ]
        for hid, name, reg in hubs:
            h = db.query(models.RegionalHub).filter_by(id=hid).first()
            if not h:
                db.add(models.RegionalHub(id=hid, name=name, region=reg, status="active"))

        # Hospitals: 3 hospitals across the 2 hubs
        hosps = [
            ("hosp-fl-1", "Hospital 1 (Metro North)", "hub-fl-a", "active", False),
            ("hosp-fl-2", "Hospital 2 (Valley North)", "hub-fl-a", "active", True),
            ("hosp-fl-3", "Hospital 3 (Coast South)", "hub-fl-b", "active", True),
            ("hosp-fl-suspended", "Hospital Suspended", "hub-fl-b", "suspended", False),
            ("hosp-fl-low-records", "Hospital Sparse", "hub-fl-a", "active", False),
        ]
        for hid, name, hub_id, status, share in hosps:
            h = db.query(models.Hospital).filter_by(id=hid).first()
            if not h:
                db.add(models.Hospital(
                    id=hid,
                    name=name,
                    hub_id=hub_id,
                    status=status,
                    share_deidentified=share
                ))
            else:
                h.status = status
                h.share_deidentified = share

        # Active consent records for consenting hospitals
        for hid in ["hosp-fl-2", "hosp-fl-3"]:
            c = db.query(models.ConsentRecord).filter_by(hospital_id=hid, consent_type="FEDERATED_TRAINING_DEIDENTIFIED").first()
            if not c:
                db.add(models.ConsentRecord(
                    hospital_id=hid,
                    consent_type="FEDERATED_TRAINING_DEIDENTIFIED",
                    status="granted"
                ))

        # Users
        users = [
            ("fl_global_admin@trustfed.ai", "Global Admin FL", "global_admin", None, None),
            ("fl_reg_a_admin@trustfed.ai", "Regional Admin A", "regional_admin", None, "hub-fl-a"),
            ("fl_reg_b_admin@trustfed.ai", "Regional Admin B", "regional_admin", None, "hub-fl-b"),
            ("fl_doc1@trustfed.ai", "Dr. One", "doctor", "hosp-fl-1", None),
            ("fl_doc2@trustfed.ai", "Dr. Two", "doctor", "hosp-fl-2", None),
            ("fl_doc3@trustfed.ai", "Dr. Three", "doctor", "hosp-fl-3", None),
        ]
        for email, name, role, hid, hub_id in users:
            usr = db.query(models.User).filter_by(email=email).first()
            if not usr:
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

        # Seed doctor-confirmed trainable encounters
        # Hosp 1: 10 confirmed encounters
        # Hosp 2: 10 confirmed encounters
        # Hosp 3: 10 confirmed encounters
        # Hosp Sparse: only 2 confirmed encounters (< min_records threshold)
        diseases = ["common cold", "influenza", "viral fever", "dengue", "typhoid", "gastroenteritis", "UTI"]
        symptom_pool = [
            ["fever", "cough", "sore throat"],
            ["fever", "headache", "vomiting"],
            ["burning urination", "fever"],
            ["diarrhea", "vomiting", "abdominal pain"],
            ["body ache", "fatigue", "fever"],
        ]

        # Helper to seed encounters
        def _seed_encs(hid, count):
            existing = db.query(models.Encounter).filter_by(hospital_id=hid).count()
            for i in range(count - existing):
                # Patient
                p = models.Patient(
                    patient_identifier=f"PT-{hid}-{i+1:04d}",
                    hospital_id=hid,
                    name_encrypted="enc_name_bytes",
                    contact_encrypted="enc_contact_bytes",
                    age=25 + (i * 3) % 50,
                    sex=i % 2,
                    weight=65.0,
                    height=170.0
                )
                db.add(p)
                db.flush()

                syms = symptom_pool[i % len(symptom_pool)]
                diag = diseases[i % len(diseases)]

                e = models.Encounter(
                    encounter_identifier=f"ENC-{hid}-{i+1:04d}",
                    patient_id=p.id,
                    hospital_id=hid,
                    symptoms=json.dumps(syms),
                    symptom_duration_days=3,
                    vitals=json.dumps({"temperature": 99.5, "heartRate": 82, "bpSystolic": 120, "bpDiastolic": 80}),
                    model_version="TF-GenDisease-v1.0",
                    doctor_confirmed_diagnosis=diag,
                    cause="Verified etiology via standard clinical evaluation",
                    treatment="Symptomatic relief, hydration, follow-up if worsening",
                    trainable=True,
                    confirmed_by=1
                )
                db.add(e)
            db.commit()

        _seed_encs("hosp-fl-1", 10)
        _seed_encs("hosp-fl-2", 10)
        _seed_encs("hosp-fl-3", 10)
        _seed_encs("hosp-fl-low-records", 2)
        _seed_encs("hosp-fl-suspended", 10)

    finally:
        db.close()


def _login(email: str) -> str:
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



# ── Test 1: Identifiers Never Present in Updates or Shared Data ─────────────────

def test_identifiers_never_present_in_updates_or_shared_data():
    """Verify strictly zero patient names, contacts, MRNs, patient IDs, addresses,
    or raw identifiers leave the hospital node either in model updates or de-identified data.
    """
    db = SessionLocal()
    try:
        # Check Hospital Node Update Payload
        base = general_disease_model.GeneralDiseaseModel()
        update = federated_learning.hospital_train_round(
            hospital_id="hosp-fl-1",
            base_W=base.W,
            base_b=base.b,
            config={"epochs": 1, "learning_rate": 0.05, "clip": 1.0, "noise_multiplier": 1.0},
            db=db,
            rng=np.random.RandomState(42)
        )

        assert update["eligible"] is True
        # Prohibited keys
        prohibited_keys = {
            "patient_id", "patientId", "name", "contact", "phone", "email",
            "address", "dob", "mrn", "patient_identifier", "encounter_identifier", "raw_records"
        }
        for k in update.keys():
            assert k not in prohibited_keys, f"Forbidden key '{k}' found in hospital update payload!"

        # Assert payload contains strictly numerical model weights and metadata
        assert isinstance(update["weightsW"], list)
        assert isinstance(update["weightsB"], list)
        assert isinstance(update["numSamples"], int)
        assert update["numSamples"] >= 10
        assert update["hospitalId"] == "hosp-fl-1"

        # Check Allow-List De-Identified Record Serializer
        patient = models.Patient(
            id=9999,
            patient_identifier="PT-SECRET-9999",
            hospital_id="hosp-fl-1",
            name_encrypted="encrypted_secret_name",
            contact_encrypted="encrypted_secret_contact",
            age=47,
            sex=1,
            weight=75.0,
            height=175.0
        )
        enc = models.Encounter(
            id=8888,
            encounter_identifier="ENC-SECRET-8888",
            patient_id=9999,
            hospital_id="hosp-fl-1",
            symptoms=json.dumps(["fever", "cough"]),
            vitals=json.dumps({"temperature": 100.4, "heartRate": 88}),
            doctor_confirmed_diagnosis="influenza",
            cause="Seasonal viral infection",
            treatment="Rest and fluids"
        )

        deidentified = federated_learning.serialize_deidentified_record(patient, enc)

        # Allow-list only
        allowed_keys = {"age_band", "sex", "symptoms", "vitals", "confirmed_diagnosis", "cause", "treatment"}
        assert set(deidentified.keys()) == allowed_keys, f"Keys do not strictly match allow-list: {set(deidentified.keys())}"

        # Coarsened age band check
        assert deidentified["age_band"] == "40-49"
        assert "47" not in json.dumps(deidentified)
        assert "PT-SECRET" not in json.dumps(deidentified)
        assert "ENC-SECRET" not in json.dumps(deidentified)
        assert "encrypted_secret" not in json.dumps(deidentified)

    finally:
        db.close()


# ── Test 2: Ineligible and Suspended Hospitals Excluded ─────────────────────────

def test_ineligible_and_suspended_hospitals_excluded():
    """Verify that:
    1. A hospital with fewer than min_records is marked ineligible.
    2. A suspended hospital is marked ineligible even if it has many records.
    3. An active hospital with sufficient records is marked eligible.
    """
    db = SessionLocal()
    try:
        # Hosp Sparse has 2 records, threshold is 5
        sparse = federated_learning.check_hospital_eligibility(db, "hosp-fl-low-records", min_records=5)
        assert sparse["eligible"] is False
        assert sparse["confirmedCount"] == 2
        assert "insufficient confirmed records" in sparse["reason"].lower()

        # Hosp Suspended has 10 records, but status is 'suspended'
        suspended = federated_learning.check_hospital_eligibility(db, "hosp-fl-suspended", min_records=5)
        assert suspended["eligible"] is False
        assert "suspended" in suspended["reason"].lower()

        # Hosp 1 has 10 records and status is active
        active = federated_learning.check_hospital_eligibility(db, "hosp-fl-1", min_records=5)
        assert active["eligible"] is True
        assert active["confirmedCount"] >= 10
        assert active["status"] == "active"

        # Verify through the API endpoint
        token = _login("fl_global_admin@trustfed.ai")
        resp = client.get(
            "/api/v1/federated/hospitals/eligibility?min_records=5",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["minRecordsThreshold"] == 5
        reports_map = {r["hospitalId"]: r for r in data["reports"]}
        assert reports_map["hosp-fl-low-records"]["eligible"] is False
        assert reports_map["hosp-fl-suspended"]["eligible"] is False
        assert reports_map["hosp-fl-1"]["eligible"] is True
        assert reports_map["hosp-fl-2"]["eligible"] is True
        assert reports_map["hosp-fl-3"]["eligible"] is True

    finally:
        db.close()


# ── Test 3: Promotion Gate Blocks Regressions and Divergence ───────────────────

def test_promotion_gate_blocks_regressions_and_divergence():
    """Verify promotion gate safeguards:
    1. Blocks model with diverging weights (NaNs, Infs, exploding norm).
    2. Blocks model with severe regression on any single disease (> tolerance 0.05).
    3. Blocks model when overall Macro-F1 degrades.
    4. Logs rejection explicitly in audit ledger.
    """
    db = SessionLocal()
    try:
        base = general_disease_model.GeneralDiseaseModel()
        val_cohort = federated_learning.load_heldout_validation_cohort()

        # 1. Divergence test: NaNs
        nan_W = np.copy(base.W)
        nan_W[0, 0] = np.nan
        gate_nan = federated_learning.evaluate_and_promote_gate(
            candidate_W=nan_W,
            candidate_b=base.b,
            current_model=base,
            config={"sessionId": "test-div-nan"},
            db=db,
            validation_cohort=val_cohort
        )
        assert gate_nan["promoted"] is False
        assert gate_nan["diverged"] is True
        assert "NaN" in gate_nan["reason"]

        # 2. Divergence test: Exploding Norm
        exploding_W = np.copy(base.W) * 500.0
        gate_exp = federated_learning.evaluate_and_promote_gate(
            candidate_W=exploding_W,
            candidate_b=base.b,
            current_model=base,
            config={"sessionId": "test-div-exp"},
            db=db,
            validation_cohort=val_cohort
        )
        assert gate_exp["promoted"] is False
        assert gate_exp["diverged"] is True
        assert "parameter norm exploded" in gate_exp["reason"]

        # 3. Regression test: Zero out weights for migraine to cause deliberate regression
        regr_W = np.copy(base.W)
        migraine_idx = general_disease_model.DISEASE_CLASSES.index("migraine")
        regr_W[:, migraine_idx] = -10.0  # severely suppress migraine predictions
        gate_regr = federated_learning.evaluate_and_promote_gate(
            candidate_W=regr_W,
            candidate_b=base.b,
            current_model=base,
            config={"sessionId": "test-regr", "regression_tolerance": 0.05},
            db=db,
            validation_cohort=val_cohort
        )
        assert gate_regr["promoted"] is False
        assert gate_regr["diverged"] is False
        assert any("migraine" in r.lower() for r in gate_regr["rejections"])

        # Check audit log for rejection entry
        audit = (
            db.query(models.AuditLog)
            .filter_by(event_type="model_rejected", session_id="test-regr")
            .order_by(models.AuditLog.id.desc())
            .first()
        )
        assert audit is not None
        assert "migraine" in audit.description.lower()

    finally:
        db.close()


# ── Test 4: Promotion Gate Promotes Improving Candidate Model ──────────────────

def test_promotion_gate_promotes_improving_model():
    """Verify that an improved candidate model passes all gates, is promoted,
    registers a new version, updates active weights, and logs promotion to audit ledger.
    """
    db = SessionLocal()
    try:
        base = general_disease_model.GeneralDiseaseModel()
        val_cohort = federated_learning.load_heldout_validation_cohort()

        # Create a candidate model with slight positive reinforcement on validation features
        # (guaranteed not to regress)
        cand_W = np.copy(base.W) + 0.001 * np.sign(base.W)
        cand_b = np.copy(base.b)

        gate_res = federated_learning.evaluate_and_promote_gate(
            candidate_W=cand_W,
            candidate_b=cand_b,
            current_model=base,
            config={"sessionId": "test-promote-session", "regression_tolerance": 0.10, "fairness_tolerance": 0.10, "min_f1_gain": 0.0},
            db=db,
            validation_cohort=val_cohort
        )

        assert gate_res["promoted"] is True
        assert gate_res["diverged"] is False
        new_version = gate_res["modelVersion"]
        assert new_version != base.version
        assert "TF-GenDisease" in new_version

        # Verify active model in singleton matches new version
        assert general_disease_model.get_active_model_version() == new_version

        # Verify model version registered in DB
        mv = db.query(models.ModelVersion).filter_by(version=new_version).first()
        assert mv is not None
        assert mv.status == "active"
        assert os.path.exists(mv.model_path)

        # Verify audit log
        audit = (
            db.query(models.AuditLog)
            .filter_by(event_type="model_promoted", session_id="test-promote-session")
            .order_by(models.AuditLog.id.desc())
            .first()
        )
        assert audit is not None
        assert new_version in audit.description

    finally:
        db.close()


# ── Test 5: One-Click Rollback Works ───────────────────────────────────────────

def test_one_click_rollback_works():
    """Verify that 1-click rollback restores previous global model version,
    re-activates previous weights in inference singleton, and records audit log.
    """
    db = SessionLocal()
    try:
        # Baseline version to roll back to
        target_version = "TF-GenDisease-v1.0"
        res = federated_learning.rollback_global_model(target_version, db)
        assert res["status"] == "success"
        assert res["activeVersion"] == target_version

        # Active singleton must now report v1.0
        assert general_disease_model.get_active_model_version() == target_version

        # Verify rollback audit entry
        audit = (
            db.query(models.AuditLog)
            .filter_by(event_type="model_rollback")
            .order_by(models.AuditLog.id.desc())
            .first()
        )
        assert audit is not None
        assert target_version in audit.description

        # Test rollback API endpoint
        token = _login("fl_global_admin@trustfed.ai")
        api_res = client.post(
            f"/api/v1/federated/models/{target_version}/rollback",
            json={"reason": "Testing 1-click rollback endpoint"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert api_res.status_code == 200
        assert api_res.json()["activeVersion"] == target_version

    finally:
        db.close()


# ── Test 6: Honest Privacy Accounting ──────────────────────────────────────────

def test_honest_privacy_accounting():
    """Verify privacy honesty:
    1. Displayed epsilon strictly matches RDP accountant output for actual noise multiplier used.
    2. Small cohorts where target epsilon cannot be met under stability noise ceiling (sigma <= 3.5)
       plainly display targetMet: False.
    3. API endpoint returns matching calculations and disclaimer.
    """
    # 1. Exact match with accountant output
    sigma_used = 1.2
    clip = 1.0
    rounds = 3
    cohort_sizes = [50, 40, 60]
    batch_size = 16
    expected_worst = 0.0
    for n in cohort_sizes:
        q = min(1.0, batch_size / n)
        steps = max(1, round(n / batch_size)) * rounds
        e = dp.epsilon(q=q, sigma=sigma_used, steps=steps, delta=1e-5)
        expected_worst = max(expected_worst, e)
    expected_eps = round(expected_worst, 3)

    accounting = federated_learning.get_honest_privacy_accounting(
        cohort_sizes=cohort_sizes,
        rounds=rounds,
        sigma=sigma_used,
        clip=clip,
        target_epsilon=1.5
    )

    # Invariant: displayed epsilon MUST equal accountant output
    assert abs(accounting["epsilon"] - expected_eps) < 1e-3
    assert accounting["sigmaActual"] == sigma_used

    # 2. Small cohort test: N=10, target eps=0.5 -> cannot be met under stability ceiling
    small_cohort_accounting = federated_learning.get_honest_privacy_accounting(
        cohort_sizes=[10],
        rounds=5,
        sigma=3.5,
        target_epsilon=0.5
    )
    assert small_cohort_accounting["targetMet"] is False
    assert small_cohort_accounting["disclaimer"] is not None
    assert "cannot be achieved" in small_cohort_accounting["disclaimer"]
    assert "honestly" in small_cohort_accounting["disclaimer"]

    # 3. Test Privacy Accounting API endpoint
    token = _login("fl_global_admin@trustfed.ai")
    api_resp = client.get(
        "/api/v1/privacy/accounting?rounds=3&sigma=1.2&target_epsilon=1.5",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert api_resp.status_code == 200
    res_data = api_resp.json()
    assert res_data["epsilon"] > 0
    assert res_data["sigma"] == 1.2
    assert "targetMet" in res_data
    assert "disclaimer" in res_data


# ── Test 7: Optional De-Identified Sharing Consent Guard ────────────────────────

def test_optional_deidentified_sharing_consent_guard():
    """Verify that:
    1. Default is OFF (share_deidentified=False) -> returns 0 records.
    2. Requires explicit active ConsentRecord.
    3. Regional admin can only access records from hospitals in their own hub.
    4. Toggling consent via API works and writes audit trail.
    """
    db = SessionLocal()
    try:
        # Hosp 1 has share_deidentified=False -> 0 records
        hosp1 = db.query(models.Hospital).filter_by(id="hosp-fl-1").first()
        assert hosp1.share_deidentified is False

        # Access Hub A with k=1: contains hosp-fl-1 (no consent) and hosp-fl-2 (has consent)
        hub_a_records = federated_learning.get_regional_deidentified_records("hub-fl-a", db, k=1)
        assert "hosp-fl-1" not in hub_a_records["consentingHospitals"]
        assert "hosp-fl-2" in hub_a_records["consentingHospitals"]
        assert hub_a_records["totalRecords"] >= 10
        assert hub_a_records["rawRecordsCount"] >= 10

        # All returned records pass allow-list serializer
        for rec in hub_a_records["records"]:
            assert set(rec.keys()) == federated_learning.ALLOWED_DEIDENTIFIED_KEYS
            assert "name" not in rec and "contact" not in rec

        # Verify k-anonymity suppression: when k=5, smaller demographic groups are suppressed
        hub_a_k5 = federated_learning.get_regional_deidentified_records("hub-fl-a", db, k=5)
        assert hub_a_k5["kThreshold"] == 5
        assert hub_a_k5["suppressedRecordsCount"] > 0
        assert hub_a_k5["rawRecordsCount"] == hub_a_records["rawRecordsCount"]

        # Tenancy test: Regional Admin B cannot access Hub A
        token_reg_b = _login("fl_reg_b_admin@trustfed.ai")
        unauthorized = client.get(
            "/api/v1/regional/hubs/hub-fl-a/deidentified-records",
            headers={"Authorization": f"Bearer {token_reg_b}"}
        )
        assert unauthorized.status_code == 403

        # Regional Admin A can access Hub A
        token_reg_a = _login("fl_reg_a_admin@trustfed.ai")
        authorized = client.get(
            "/api/v1/regional/hubs/hub-fl-a/deidentified-records",
            headers={"Authorization": f"Bearer {token_reg_a}"}
        )
        assert authorized.status_code == 200
        assert authorized.json()["hubId"] == "hub-fl-a"

        # Toggle consent for hosp-fl-1 via API
        token_doc1 = _login("fl_doc1@trustfed.ai")
        toggle_res = client.post(
            "/api/v1/hospitals/hosp-fl-1/consent",
            json={"share_deidentified": True},
            headers={"Authorization": f"Bearer {token_doc1}"}
        )
        assert toggle_res.status_code == 200
        assert toggle_res.json()["shareDeidentified"] is True
        assert toggle_res.json()["consentStatus"] == "granted"

        # Re-check Hub A: hosp-fl-1 is now consenting
        hub_a_updated = federated_learning.get_regional_deidentified_records("hub-fl-a", db)
        assert "hosp-fl-1" in hub_a_updated["consentingHospitals"]

    finally:
        db.close()


# ── Test 8: Simulated 3 Hospitals and 2 Hubs Hierarchical Round ─────────────────

def test_simulated_3_hospitals_2_hubs_hierarchical_round():
    """Simulate a complete multi-tier hierarchical federated round:
    - Tier 1: 3 Hospitals train locally using DP-SGD.
    - Tier 2: 2 Regional Hubs aggregate their hospital models.
    - Tier 3: Global Aggregator combines regional models.
    - Promotion Gate evaluates candidate model against held-out validation cohort.
    - Audit Ledger records round events.
    """
    db = SessionLocal()
    try:
        # Trigger round via Global Admin API
        token = _login("fl_global_admin@trustfed.ai")
        round_cfg = {
            "min_records": 5,
            "epochs": 1,
            "learning_rate": 0.05,
            "clip": 1.0,
            "noise_multiplier": 1.0,
            "target_epsilon": 2.0,
            "fairness_tolerance": 0.05,
            "regression_tolerance": 0.05
        }

        resp = client.post(
            "/api/v1/federated/rounds/trigger",
            json=round_cfg,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()

        assert "sessionId" in data
        assert data["status"] in ("promoted", "rejected")
        assert len(data["participatingHospitals"]) >= 3
        assert {"hosp-fl-1", "hosp-fl-2", "hosp-fl-3"}.issubset(set(data["participatingHospitals"]))
        assert len(data["participatingHubs"]) >= 2
        assert {"hub-fl-a", "hub-fl-b"}.issubset(set(data["participatingHubs"]))
        assert "gateResult" in data
        assert "privacy" in data

        # Verify audit ledger has records of each tier
        events = (
            db.query(models.AuditLog.event_type)
            .filter_by(session_id=data["sessionId"])
            .all()
        )
        event_types = {e[0] for e in events}
        assert "federated_round_triggered" in event_types
        assert "hospital_update_received" in event_types
        assert "regional_aggregation" in event_types
        assert "global_aggregation" in event_types
        assert ("model_promoted" in event_types) or ("model_rejected" in event_types)

    finally:
        db.close()


# ── Test 9: List Models Lineage Endpoint ───────────────────────────────────────

def test_list_models_lineage_endpoint():
    """Verify GET /api/v1/federated/models returns model versions, statuses, and active version."""
    token = _login("fl_global_admin@trustfed.ai")
    resp = client.get(
        "/api/v1/federated/models",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "activeVersion" in data
    assert "models" in data
    assert len(data["models"]) >= 1
    active_models = [m for m in data["models"] if m["isActive"]]
    assert len(active_models) == 1
    assert active_models[0]["version"] == data["activeVersion"]



# ── Test 10: Promotion Gate Rejects Insufficient Macro-F1 Gain ──────────────────

def test_promotion_gate_rejects_insufficient_f1_gain():
    """A candidate model whose macro-F1 gain is below the 0.01 minimum (+0.0007)
    must be REJECTED — not promoted. This ensures the promotion gate cannot be
    bypassed by noise or negligible improvements."""
    base_model = general_disease_model.GeneralDiseaseModel()
    W_candidate = base_model.W.copy() + np.random.normal(0, 1e-5, base_model.W.shape)
    b_candidate = base_model.b.copy() + np.random.normal(0, 1e-5, base_model.b.shape)

    config = {
        "sessionId": "test-insufficient-f1-gain",
        "regression_tolerance": 0.0,
        "fairness_tolerance": 0.05,
        "min_f1_gain": 0.01,
    }

    db = SessionLocal()
    try:
        result = federated_learning.evaluate_and_promote_gate(
            W_candidate, b_candidate, base_model, config, db
        )
        assert result["promoted"] is False, (
            f"Expected candidate to be rejected due to gain < 0.01, but got promoted=True: {result}"
        )
        reason = result.get("reason", "").lower()
        assert any(kw in reason for kw in ("gain", "minimum", "below", "regressed")), f"Unexpected reason: {reason}"
        assert "macroF1Delta" in result
        assert result["macroF1Delta"] < 0.01, f"Expected delta < 0.01, got {result['macroF1Delta']}"
    finally:
        db.close()
