"""Production Demo Data Cleanup Script.

Safely purges synthetic demonstration records (demo hubs, demo hospitals,
demo users, and synthetic patients matching PT-GEN-* or PT-BGH-*) from the database.

Usage:
  # Dry-run inspection (default, non-destructive):
  python scripts/purge_demo_data.py --dry-run

  # Execute cleanup (requires explicit confirmation flag):
  python scripts/purge_demo_data.py --confirm

Safety Guarantees:
  - Default mode is always --dry-run.
  - Never executes unless --confirm is explicitly passed.
  - Preserves global_admin account by default (--keep-admin).
  - Emits an immutable cryptographically hashed audit entry in AuditLog.
"""
from __future__ import annotations
import os
import sys
import argparse
from typing import Dict, Any

# Ensure backend root is on Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from db.database import SessionLocal, engine
from db import models
from services import store

DEMO_HUB_IDS = ["hub-east", "hub-west", "hub-north", "hub-south"]
DEMO_HOSPITAL_IDS = ["1", "2", "3", "4", "hospital-boston", "city-med-center"]
DEMO_PATIENT_PREFIXES = ["PT-GEN-", "PT-BGH-", "PT-DEMO-", "PT-SYNTH-"]
DEMO_STAFF_EMAILS = [
    "regional@trustfed.ai",
    "hospital@trustfed.ai",
    "doctor@trustfed.ai",
    "staff@trustfed.ai"
]


def identify_demo_data(db) -> Dict[str, Any]:
    """Scans all relational tables to identify records flagged as demo/synthetic."""
    # 1. Hubs
    hubs = db.query(models.RegionalHub).filter(models.RegionalHub.id.in_(DEMO_HUB_IDS)).all()

    # 2. Hospitals
    hospitals = db.query(models.Hospital).filter(
        (models.Hospital.id.in_(DEMO_HOSPITAL_IDS)) |
        (models.Hospital.hub_id.in_(DEMO_HUB_IDS))
    ).all()
    hospital_ids = list(set([h.id for h in hospitals] + DEMO_HOSPITAL_IDS))

    # 3. Patients (by prefix or hospital ID)
    patient_q = db.query(models.Patient).filter(
        models.Patient.hospital_id.in_(hospital_ids)
    ).all()
    prefix_patients = db.query(models.Patient).filter(
        models.Patient.patient_identifier.like("PT-GEN-%") |
        models.Patient.patient_identifier.like("PT-BGH-%")
    ).all()
    all_patients_map = {p.id: p for p in (patient_q + prefix_patients)}
    patients = list(all_patients_map.values())
    patient_ids = [p.id for p in patients]

    # 4. Encounters
    encounters = []
    if patient_ids:
        encounters = db.query(models.Encounter).filter(
            (models.Encounter.patient_id.in_(patient_ids)) |
            (models.Encounter.hospital_id.in_(hospital_ids))
        ).all()
    else:
        encounters = db.query(models.Encounter).filter(
            models.Encounter.hospital_id.in_(hospital_ids)
        ).all()

    # 5. Patient Predictions (Heart disease legacy)
    predictions = db.query(models.PatientPrediction).filter(
        (models.PatientPrediction.hospital_id.in_(hospital_ids)) |
        (models.PatientPrediction.patient_identifier.like("PT-GEN-%")) |
        (models.PatientPrediction.patient_identifier.like("PT-BGH-%"))
    ).all()

    # 6. Users (excluding global admin)
    users = db.query(models.User).filter(
        (models.User.email.in_(DEMO_STAFF_EMAILS)) |
        (models.User.hospital_id.in_(hospital_ids)) |
        (models.User.hub_id.in_(DEMO_HUB_IDS))
    ).all()

    return {
        "hubs": hubs,
        "hospitals": hospitals,
        "patients": patients,
        "encounters": encounters,
        "predictions": predictions,
        "users": users
    }


def run_cleanup(dry_run: bool = True, keep_admin: bool = True):
    print("=" * 70)
    print(" TRUSTFED PRODUCTION DEMO DATA PURGE")
    print(f" Mode: {'DRY RUN (No changes will be written)' if dry_run else 'LIVE EXECUTION (Records will be deleted)'}")
    print(f" Database: {engine.url.render_as_string(hide_password=True)}")
    print("=" * 70)

    db = SessionLocal()
    try:
        targets = identify_demo_data(db)

        # Filter users if keep_admin
        users_to_delete = targets["users"]
        if keep_admin:
            users_to_delete = [u for u in users_to_delete if u.role != "global_admin"]

        print(f"\n[IDENTIFIED DEMO RECORDS]")
        print(f"  * Regional Hubs:       {len(targets['hubs'])} found ({', '.join([h.id for h in targets['hubs']]) or 'None'})")
        print(f"  * Hospitals:           {len(targets['hospitals'])} found ({', '.join([h.id for h in targets['hospitals']]) or 'None'})")
        print(f"  * Staff / Demo Users:  {len(users_to_delete)} found ({', '.join([u.email for u in users_to_delete]) or 'None'})")
        print(f"  * Demo Patients:       {len(targets['patients'])} found")
        print(f"  * Clinical Encounters: {len(targets['encounters'])} found")
        print(f"  * Legacy Predictions:  {len(targets['predictions'])} found")

        total_records = (
            len(targets['hubs']) +
            len(targets['hospitals']) +
            len(users_to_delete) +
            len(targets['patients']) +
            len(targets['encounters']) +
            len(targets['predictions'])
        )

        print(f"\nTotal demo records marked for deletion: {total_records}")

        if dry_run:
            print("\n[DRY RUN COMPLETE] Zero database rows modified. Run with --confirm to execute purge.")
            return

        if not dry_run:
            print("\nExecuting relational purge in dependency-safe order...")

            # 1. Delete encounters
            for enc in targets['encounters']:
                db.delete(enc)
            db.flush()

            # 2. Delete patient predictions
            for pred in targets['predictions']:
                db.delete(pred)
            db.flush()

            # 3. Delete patients
            for pt in targets['patients']:
                db.delete(pt)
            db.flush()

            # 4. Delete demo staff users
            for u in users_to_delete:
                db.delete(u)
            db.flush()

            # 5. Delete demo hospitals
            for hosp in targets['hospitals']:
                db.delete(hosp)
            db.flush()

            # 6. Delete demo hubs
            for hub in targets['hubs']:
                db.delete(hub)
            db.flush()

            # 7. Record immutable audit log
            audit_desc = (
                f"Production demo data purge executed: {len(targets['encounters'])} encounters, "
                f"{len(targets['patients'])} patients, {len(targets['predictions'])} predictions, "
                f"{len(users_to_delete)} users, {len(targets['hospitals'])} hospitals, "
                f"{len(targets['hubs'])} hubs removed."
            )
            store.add_audit(
                db,
                session_id=None,
                node_id="SYSTEM_OPERATOR",
                event_type="data_purge",
                description=audit_desc
            )
            db.commit()

            print(f"[SUCCESS] Database purged. Cryptographically chained audit entry recorded.")
            print(f"Audit Description: {audit_desc}")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Cleanup failed: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Purge demo and synthetic data from TrustFed database.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview records without deleting (default: True)")
    parser.add_argument("--confirm", action="store_true", default=False, help="Confirm live deletion of demo data")
    parser.add_argument("--include-admin", action="store_true", default=False, help="Include global_admin in deletion (DANGEROUS)")

    args = parser.parse_args()

    # If --confirm is explicitly passed, disable dry-run
    dry_run = not args.confirm
    keep_admin = not args.include_admin

    run_cleanup(dry_run=dry_run, keep_admin=keep_admin)


if __name__ == "__main__":
    main()

