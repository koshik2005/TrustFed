"""Local Development-Only Database Seeding.

CRITICAL: Strictly blocked from running in production (ENVIRONMENT=production or RENDER=true).
Generates random high-entropy passwords for development accounts.
"""
from __future__ import annotations
import os
import sys
from sqlalchemy.orm import Session
from db.database import SessionLocal, engine
from db import models
from services import auth


def seed_dev_environment(db: Session) -> dict[str, str]:
    """Seed isolated local-dev accounts with randomly generated secure passwords."""
    env = os.getenv("ENVIRONMENT", "development").strip().lower()
    is_prod = env in ("production", "prod") or bool(os.getenv("RENDER"))
    if is_prod:
        raise RuntimeError("CRITICAL SECURITY ERROR: seed_dev_environment is strictly prohibited in production!")

    dev_accounts = [
        ("dev_admin@trustfed.local", "Dev Global Admin", "global_admin", None, None),
        ("dev_reg_east@trustfed.local", "Dev Regional Admin", "regional_admin", "hub-east", None),
        ("dev_doctor@trustfed.local", "Dev Doctor", "doctor", None, "1"),
        ("dev_nurse@trustfed.local", "Dev Hospital Staff", "hospital_staff", None, "1"),
    ]

    generated_credentials = {}

    for email, name, role, hub_id, hosp_id in dev_accounts:
        existing = db.query(models.User).filter_by(email=email).first()
        temp_pw = auth.generate_temp_password(16)
        if not existing:
            user = models.User(
                email=email,
                name=name,
                role=role,
                hub_id=hub_id,
                hospital_id=hosp_id,
                password_hash=auth.hash_password(temp_pw),
                must_reset_password=True,
                status="active"
            )
            db.add(user)
        else:
            existing.password_hash = auth.hash_password(temp_pw)
            existing.status = "active"
        generated_credentials[email] = temp_pw

    db.commit()
    print("[DEV SEED] Local development accounts generated with one-time high-entropy passwords:")
    for email, pw in generated_credentials.items():
        print(f"  {email}: {pw}")
    return generated_credentials


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_dev_environment(db)
    finally:
        db.close()

