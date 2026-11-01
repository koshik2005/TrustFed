"""Migration script: v4 MFA (TOTP) and Soft Delete Lifecycle.

Adds:
- Soft delete auditing columns (`deleted_at`, `deleted_by`) on `regional_hubs`, `hospitals`, and `users`.
- MFA (TOTP) state columns (`mfa_enabled`, `mfa_secret`, `mfa_recovery_codes`) on `users`.
"""
from __future__ import annotations
from sqlalchemy import inspect, text


def migrate_up(engine) -> list[str]:
    """Apply schema additions for MFA and soft deletion."""
    inspector = inspect(engine)
    applied = []

    def get_cols(table: str) -> set[str]:
        try:
            return {c["name"] for c in inspector.get_columns(table)}
        except Exception:
            return set()

    with engine.begin() as conn:
        # 1. regional_hubs
        hub_cols = get_cols("regional_hubs")
        if "deleted_at" not in hub_cols:
            conn.execute(text("ALTER TABLE regional_hubs ADD COLUMN deleted_at TIMESTAMP"))
            applied.append("regional_hubs.deleted_at")
        if "deleted_by" not in hub_cols:
            conn.execute(text("ALTER TABLE regional_hubs ADD COLUMN deleted_by INTEGER"))
            applied.append("regional_hubs.deleted_by")

        # 2. hospitals
        hosp_cols = get_cols("hospitals")
        if "deleted_at" not in hosp_cols:
            conn.execute(text("ALTER TABLE hospitals ADD COLUMN deleted_at TIMESTAMP"))
            applied.append("hospitals.deleted_at")
        if "deleted_by" not in hosp_cols:
            conn.execute(text("ALTER TABLE hospitals ADD COLUMN deleted_by INTEGER"))
            applied.append("hospitals.deleted_by")

        # 3. users
        user_cols = get_cols("users")
        if "deleted_at" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP"))
            applied.append("users.deleted_at")
        if "deleted_by" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN deleted_by INTEGER"))
            applied.append("users.deleted_by")
        if "mfa_enabled" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE"))
            applied.append("users.mfa_enabled")
        if "mfa_secret" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN mfa_secret TEXT"))
            applied.append("users.mfa_secret")
        if "mfa_recovery_codes" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN mfa_recovery_codes TEXT"))
            applied.append("users.mfa_recovery_codes")

    print(f"[MIGRATION UP v4] Applied {len(applied)} columns for MFA and soft deletion.")
    return applied


def migrate_down(engine) -> list[str]:
    """Rollback soft delete and MFA columns if supported."""
    print("[MIGRATION DOWN v4] Rollback noted. Preserving database columns to avoid data loss.")
    return []
