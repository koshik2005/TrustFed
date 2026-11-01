"""Security Guard: Prevents default, demo, and insecure credentials in TrustFed.

Rules:
- No user account may possess 'password123', 'admin', 'password', or known default passwords.
- Startup MUST fail in production/deployed mode if any default password is found.
- Local dev seed accounts are isolated and strictly prohibited from executing in production.
"""
from __future__ import annotations
import os
import secrets
from typing import List
from sqlalchemy.orm import Session
from db import models
from . import auth

DISALLOWED_PASSWORDS = [
    "password123",
    "password",
    "admin",
    "admin123",
    "demo",
    "default",
    "changeme",
    "12345678",
]


def sanitize_legacy_default_credentials(db: Session) -> int:
    """Disables any legacy demo accounts that still utilize 'password123' or known default credentials."""
    users = db.query(models.User).all()
    sanitized_count = 0
    for u in users:
        if not u.password_hash or u.password_hash.startswith("DISABLED$"):
            continue
        for pw in DISALLOWED_PASSWORDS:
            if auth.verify_password(pw, u.password_hash):
                u.password_hash = f"DISABLED${secrets.token_hex(32)}"
                u.status = "suspended"
                sanitized_count += 1
                break
    if sanitized_count > 0:
        db.commit()
        print(f"[SECURITY GUARD] Sanitized and disabled {sanitized_count} legacy accounts with default passwords.")
    return sanitized_count


def validate_no_default_credentials_on_startup(db: Session) -> None:
    """Checks all database users against known default passwords.

    In production/informational/clinical modes, raises RuntimeError if any user has
    a known default password.
    """
    env = os.getenv("ENVIRONMENT", "development").strip().lower()
    is_prod = env in ("production", "prod") or bool(os.getenv("RENDER"))
    app_mode = os.getenv("APP_MODE", "informational").strip().lower()

    users = db.query(models.User).all()
    violations: List[str] = []

    for u in users:
        if not u.password_hash or u.password_hash.startswith("DISABLED$"):
            continue
        for pw in DISALLOWED_PASSWORDS:
            if auth.verify_password(pw, u.password_hash):
                violations.append(f"{u.email} (matched '{pw}')")
                break

    if violations:
        # In both informational and clinical modes, fail hard immediately
        msg = (
            f"FATAL SECURITY VIOLATION: Default credentials detected in database for {len(violations)} account(s): "
            f"{', '.join(violations[:3])}. All default passwords must be removed or rotated before startup."
        )
        raise RuntimeError(msg)
