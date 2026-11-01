"""Migration script: v3 Tenant & Lookup Performance Indexes.

Adds optimized composite and single-column indexes on tenant isolation,
audit logs, encounter dates, and high-frequency lookup columns across
PostgreSQL and SQLite.
"""
from __future__ import annotations
from sqlalchemy import text
from typing import List, Tuple

INDEXES: List[Tuple[str, str, str]] = [
    # (Index Name, Table Name, Columns Definition)
    ("ix_encounters_hospital_created", "encounters", "hospital_id, created_at"),
    ("ix_encounters_patient_created", "encounters", "patient_id, created_at"),
    ("ix_encounters_hospital_confirmed", "encounters", "hospital_id, confirmed_at"),
    ("ix_encounters_created_at", "encounters", "created_at"),
    ("ix_encounters_confirmed_at", "encounters", "confirmed_at"),
    ("ix_encounters_doctor_confirmed_diagnosis", "encounters", "doctor_confirmed_diagnosis"),
    ("ix_patients_hospital_identifier", "patients", "hospital_id, patient_identifier"),
    ("ix_patients_created_at", "patients", "created_at"),
    ("ix_consent_records_granted_at", "consent_records", "granted_at"),
    ("ix_audit_logs_node_id", "audit_logs", "node_id"),
    ("ix_audit_logs_event_type", "audit_logs", "event_type"),
    ("ix_audit_logs_timestamp", "audit_logs", "timestamp"),
    ("ix_audit_logs_node_timestamp", "audit_logs", "node_id, timestamp"),
    ("ix_patient_predictions_created_at", "patient_predictions", "created_at"),
    ("ix_refresh_tokens_expires_at", "refresh_tokens", "expires_at"),
    ("ix_refresh_tokens_user_expires", "refresh_tokens", "user_id, expires_at"),
    ("ix_regional_hubs_region", "regional_hubs", "region"),
    ("ix_hospitals_status", "hospitals", "status"),
    ("ix_users_role", "users", "role"),
]


def migrate_up(engine) -> List[str]:
    """Create all lookup and tenant composite indexes if they do not already exist."""
    applied = []
    with engine.begin() as conn:
        for idx_name, table, cols in INDEXES:
            try:
                sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({cols})"
                conn.execute(text(sql))
                applied.append(idx_name)
            except Exception as e:
                # Catch cases where SQLite or Postgres has specific syntax variations
                print(f"[WARN] Index creation skipped for {idx_name}: {e}")
    print(f"[MIGRATION UP v3] Applied {len(applied)} performance indexes.")
    return applied


def migrate_down(engine) -> List[str]:
    """Roll back all v3 performance indexes."""
    dropped = []
    with engine.begin() as conn:
        for idx_name, _, _ in INDEXES:
            try:
                conn.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
                dropped.append(idx_name)
            except Exception as e:
                print(f"[WARN] Failed to drop index {idx_name}: {e}")
    print(f"[MIGRATION DOWN v3] Dropped {len(dropped)} performance indexes.")
    return dropped

