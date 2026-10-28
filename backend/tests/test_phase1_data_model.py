"""Phase 1 Automated Verification Suite:
- Schema migration up/down
- Patient PHI encryption at rest (Fernet AES-128-CBC + HMAC-SHA256)
- Zero-data-loss legacy cardiac prediction migration
- Production seed guard validation
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from db.database import Base
from db import models
from db.migrations.v2_general_disease_migration import migrate_up, migrate_down
from services import crypto, seed_data


def test_encryption_of_patient_name_and_contact():
    """Verify that patient PHI is encrypted at rest and decrypts accurately."""
    name = "Elizabeth Warren-Smyth"
    contact = "+1 (555) 234-5678 / e.smyth@cardiac.org"

    enc_name = crypto.encrypt_phi(name)
    enc_contact = crypto.encrypt_phi(contact)

    # Core Security Invariant: Ciphertext must not contain plaintext
    assert enc_name != name
    assert enc_contact != contact
    assert name not in enc_name
    assert contact not in enc_contact

    # Fernet tokens start with version byte (0x80 -> 'gAAAAA')
    assert enc_name.startswith("gAAAAA")
    assert enc_contact.startswith("gAAAAA")

    # Decrypt and verify fidelity
    dec_name = crypto.decrypt_phi(enc_name)
    dec_contact = crypto.decrypt_phi(enc_contact)
    assert dec_name == name
    assert dec_contact == contact

    # Tampered ciphertext must fail authentication
    tampered = enc_name[:-5] + "AAAAA"
    try:
        crypto.decrypt_phi(tampered)
        assert False, "Tampered ciphertext should have raised ValueError"
    except ValueError:
        pass
    print("PASS: test_encryption_of_patient_name_and_contact")


def test_schema_migration_up_and_down():
    """Verify that migrate_up creates all required tables/columns and migrate_down rolls back cleanly."""
    engine = create_engine("sqlite:///:memory:")
    
    # 1. Initialize legacy schema
    Base.metadata.create_all(bind=engine)
    
    # 2. Run migrate_up
    migrate_up(engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    
    required_tables = {
        "regional_hubs",
        "hospitals",
        "users",
        "patients",
        "encounters",
        "diseases",
        "model_versions",
        "consent_records",
        "patient_predictions", # backward compatibility
        "audit_logs"
    }
    for t in required_tables:
        assert t in tables, f"Expected table {t} missing after migrate_up"

    user_cols = {c["name"] for c in inspector.get_columns("users")}
    assert "hub_id" in user_cols
    assert "must_reset_password" in user_cols
    assert "status" in user_cols

    # 3. Run migrate_down
    migrate_down(engine)
    inspector = inspect(engine)
    tables_after = set(inspector.get_table_names())
    
    # V2 tables should be dropped
    v2_dropped = {"regional_hubs", "hospitals", "patients", "encounters", "diseases", "model_versions", "consent_records"}
    for t in v2_dropped:
        assert t not in tables_after, f"Table {t} should have been dropped on migrate_down"

    # Core legacy tables should remain intact
    assert "users" in tables_after
    assert "patient_predictions" in tables_after
    assert "audit_logs" in tables_after
    print("PASS: test_schema_migration_up_and_down")


def test_legacy_data_migration_without_data_loss():
    """Verify that existing heart-disease predictions and hospital nodes are preserved and mapped."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    TestSession = sessionmaker(bind=engine)
    db = TestSession()

    # Seed legacy node & prediction
    db.add(models.HospitalNode(id="1", name="Boston General Node", region="East", dataset_size=50))
    db.add(models.PatientPrediction(
        id=101,
        patient_identifier="PT-HIST-101",
        hospital_id="1",
        user_id=1,
        age=58,
        risk_score=0.88,
        confidence=0.92,
        explanation_text="Legacy cardiac risk model evaluation"
    ))
    db.commit()
    db.close()

    # Execute migration
    # Monkey-patch SessionLocal temporarily to use test engine
    import db.migrations.v2_general_disease_migration as mig
    orig_session_local = mig.SessionLocal
    mig.SessionLocal = TestSession
    try:
        migrate_up(engine)
    finally:
        mig.SessionLocal = orig_session_local

    db = TestSession()
    # 1. Verify hospital node migrated to hospitals table
    hosp = db.query(models.Hospital).filter_by(id="1").first()
    assert hosp is not None
    assert hosp.name == "Boston General Node"
    assert hosp.hub_id == "hub-east"

    # 2. Verify legacy prediction is preserved in patient_predictions
    legacy_pred = db.query(models.PatientPrediction).filter_by(id=101).first()
    assert legacy_pred is not None
    assert legacy_pred.risk_score == 0.88

    # 3. Verify encounter and patient created without data loss
    enc = db.query(models.Encounter).filter_by(encounter_identifier="ENC-LEGACY-0101").first()
    assert enc is not None
    assert enc.hospital_id == "1"
    assert "Coronary Artery Disease" in enc.predicted_top3
    assert enc.doctor_confirmed_diagnosis == "CARDIAC_CAD"

    pat = db.query(models.Patient).filter_by(patient_identifier="PT-HIST-101").first()
    assert pat is not None
    assert pat.hospital_id == "1"
    assert crypto.decrypt_phi(pat.name_encrypted).startswith("Legacy Patient")
    db.close()
    print("PASS: test_legacy_data_migration_without_data_loss")


def test_seed_guard_in_production():
    """Verify that synthetic demo seeding is strictly blocked in production unless ALLOW_DEMO_USERS=true."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    db = TestSession()

    orig_env = os.environ.get("ENVIRONMENT")
    orig_allow = os.environ.get("ALLOW_DEMO_USERS")
    try:
        # 1. Production with ALLOW_DEMO_USERS=false -> Must block seeding
        os.environ["ENVIRONMENT"] = "production"
        os.environ["ALLOW_DEMO_USERS"] = "false"
        result = seed_data.seed_synthetic_data(db)
        assert result is False
        assert db.query(models.Patient).count() == 0
        assert db.query(models.Disease).count() == 0

        # 2. Showcase / Demo environment with ALLOW_DEMO_USERS=true -> Seeding permitted
        os.environ["ALLOW_DEMO_USERS"] = "true"
        result = seed_data.seed_synthetic_data(db)
        assert result is True
        assert db.query(models.Disease).count() >= 7
        assert db.query(models.Patient).count() >= 5
        assert db.query(models.Encounter).count() >= 5
        assert db.query(models.Hospital).count() >= 4
        assert db.query(models.RegionalHub).count() >= 2
    finally:
        if orig_env is not None: os.environ["ENVIRONMENT"] = orig_env
        else: os.environ.pop("ENVIRONMENT", None)
        if orig_allow is not None: os.environ["ALLOW_DEMO_USERS"] = orig_allow
        else: os.environ.pop("ALLOW_DEMO_USERS", None)
        db.close()
    print("PASS: test_seed_guard_in_production")


if __name__ == "__main__":
    test_encryption_of_patient_name_and_contact()
    test_schema_migration_up_and_down()
    test_legacy_data_migration_without_data_loss()
    test_seed_guard_in_production()
    print("All Phase 1 data model and migration tests passed successfully!")
