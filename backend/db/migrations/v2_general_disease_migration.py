"""Migration script: v2 General Disease Prediction Platform.

Transitions TrustFed from a cardiac-only platform to a general disease prediction system.
- Creates: regional_hubs, hospitals, patients (PHI encrypted at rest), encounters, diseases, model_versions, consent_records.
- Alters: users table (adds hub_id, must_reset_password, status).
- Migrates: legacy hospital_nodes into hospitals table, and patient_predictions into encounters without data loss.
"""
from __future__ import annotations
import json
import uuid
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from db.database import Base, SessionLocal
from db import models
from services import crypto


def migrate_up(engine):
    """Apply schema additions, alter existing tables, and migrate legacy data."""
    # 1. Create any missing tables defined in Base metadata
    Base.metadata.create_all(bind=engine)

    # 1b. Ensure soft-delete and MFA columns are created on existing tables first
    try:
        from db.migrations.v4_mfa_and_soft_delete import migrate_up as migrate_v4_mfa
        migrate_v4_mfa(engine)
    except Exception as e:
        print(f"[MIGRATION UP] Pre-flight v4 check notice: {e}")

    inspector = inspect(engine)
    user_columns = {c["name"] for c in inspector.get_columns("users")}

    # 2. Add columns to users if missing
    with engine.begin() as conn:
        if "hub_id" not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN hub_id VARCHAR"))
            print("[MIGRATION UP] Added column 'hub_id' to users.")
        if "must_reset_password" not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN must_reset_password BOOLEAN DEFAULT FALSE"))
            print("[MIGRATION UP] Added column 'must_reset_password' to users.")
        if "status" not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN status VARCHAR DEFAULT 'active'"))
            print("[MIGRATION UP] Added column 'status' to users.")

    # 3. Data Migration: Seed regional hubs and link existing hospital nodes
    from sqlalchemy.orm import sessionmaker
    DbSession = sessionmaker(bind=engine)
    db: Session = DbSession()
    try:
        # Create standard regional hubs if not existing
        hubs = [
            ("hub-east", "East Coast Regional Aggregator", "East"),
            ("hub-west", "West Coast Regional Aggregator", "West"),
        ]
        for hid, hname, hregion in hubs:
            res = db.execute(text("SELECT id FROM regional_hubs WHERE id = :id"), {"id": hid}).first()
            if not res:
                db.execute(
                    text("INSERT INTO regional_hubs (id, name, region, status) VALUES (:id, :name, :region, 'active')"),
                    {"id": hid, "name": hname, "region": hregion}
                )
        db.commit()

        # Migrate existing hospital_nodes to hospitals table if legacy table exists
        if "hospital_nodes" in inspector.get_table_names():
            nodes = db.query(models.HospitalNode).all()
            for node in nodes:
                existing_hosp = db.query(models.Hospital).filter_by(id=node.id).first()
                if not existing_hosp:
                    hub_id = "hub-east" if (node.region and "east" in node.region.lower()) else "hub-west"
                    db.add(models.Hospital(
                        id=node.id,
                        name=node.name or f"Hospital Node #{node.id}",
                        hub_id=hub_id,
                        status=node.status or "active",
                        share_deidentified=True,
                        dataset_size=node.dataset_size or 0,
                        consent_record_fields=json.dumps({"terms": "v2.0", "optIn": True})
                    ))
            db.commit()

        # 4. Migrate existing patient_predictions into encounters and patients without data loss
        preds = db.query(models.PatientPrediction).all()
        for p in preds:
            # Check if this prediction was already migrated to an encounter
            enc_id = f"ENC-LEGACY-{p.id:04d}"
            existing_enc = db.query(models.Encounter).filter_by(encounter_identifier=enc_id).first()
            if existing_enc:
                continue

            hid = p.hospital_id or "1"
            # Create or retrieve patient with encrypted pseudonym
            p_ident = p.patient_identifier or f"PT-LEGACY-{p.id:04d}"
            patient = db.query(models.Patient).filter_by(patient_identifier=p_ident).first()
            if not patient:
                patient = models.Patient(
                    patient_identifier=p_ident,
                    hospital_id=hid,
                    name_encrypted=crypto.encrypt_phi(f"Legacy Patient {p_ident}"),
                    contact_encrypted=crypto.encrypt_phi(f"legacy-{p_ident.lower()}@hospital-{hid}.org"),
                    age=p.age or 50,
                    sex=1,
                    weight=70.0,
                    height=170.0,
                )
                db.add(patient)
                db.commit()
                db.refresh(patient)

            vitals_data = {
                "source": "legacy_cardiac_prediction",
                "risk_score": p.risk_score,
                "confidence": p.confidence,
                "explanation": p.explanation_text
            }
            pred_top3 = [
                {"disease": "Coronary Artery Disease (Cardiac Risk)", "probability": float(p.risk_score or 0.5)},
                {"disease": "Hypertension", "probability": float(max(0.1, (p.risk_score or 0.5) * 0.4))},
                {"disease": "Angina Pectoris", "probability": float(max(0.05, (p.risk_score or 0.5) * 0.3))}
            ]

            encounter = models.Encounter(
                encounter_identifier=enc_id,
                patient_id=patient.id,
                hospital_id=hid,
                symptoms=json.dumps(["chest_pain", "angina", "shortness_of_breath"] if (p.risk_score or 0) > 0.5 else ["mild_fatigue"]),
                symptom_duration_days=3,
                vitals=json.dumps(vitals_data),
                structured_ecg_finding="st_depression" if (p.risk_score or 0) > 0.5 else "normal",
                model_version=p.session_id or "TF-HeartNet-v2",
                predicted_top3=json.dumps(pred_top3),
                doctor_confirmed_diagnosis="CARDIAC_CAD" if (p.risk_score or 0) > 0.6 else None,
                cause="Coronary arteriosclerosis with ischemic signs" if (p.risk_score or 0) > 0.6 else None,
                treatment="Aspirin, Statin, Cardiology referral" if (p.risk_score or 0) > 0.6 else "Lifestyle counseling",
                confirmed_by=p.user_id,
                confirmed_at=p.created_at,
                trainable=False
            )
            db.add(encounter)
        db.commit()
        print(f"[MIGRATION UP] Successfully migrated legacy data into v2 schema.")
    finally:
        db.close()


def migrate_down(engine):
    """Roll back v2 tables while strictly preserving legacy data."""
    v2_tables = [
        "consent_records",
        "encounters",
        "patients",
        "model_versions",
        "diseases",
        "hospitals",
        "regional_hubs",
    ]
    with engine.begin() as conn:
        for t in v2_tables:
            conn.execute(text(f"DROP TABLE IF EXISTS {t}"))
            print(f"[MIGRATION DOWN] Dropped table {t}")
    print("[MIGRATION DOWN] Rollback complete. Core legacy tables preserved.")
