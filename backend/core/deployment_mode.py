"""Deployment Mode Configuration for TrustFed-Health.

Provides strict separation between:
1. INFORMATIONAL MODE (Default):
   - Educational decision support only.
   - No patient names or contact identifiers collected or stored.
   - Persists only anonymous, non-linkable usage metrics.
   - Persistent disclaimer on all pages and API results.
   - Doctor confirmation and federated training rounds are disabled.
   
2. CLINICAL MODE (Explicitly enabled with enterprise security flags):
   - Multi-tenant hospital data with field-level encryption.
   - Licensed doctor diagnostic confirmations and trainable tagging.
   - Federated rounds with Differential Privacy and audit ledger.
   - Refuses startup unless all enterprise compliance flags are confirmed.
"""
from __future__ import annotations
import os
import logging
from typing import Literal

logger = logging.getLogger("trustfed.deployment_mode")

AppMode = Literal["informational", "clinical"]

PERSISTENT_DISCLAIMER = (
    "Educational decision support. Not medical advice. "
    "Not clinically validated. In an emergency call your local emergency number."
)


def get_app_mode() -> AppMode:
    """Returns 'clinical' if APP_MODE is explicitly set to clinical/prod, otherwise 'informational'."""
    raw = os.getenv("APP_MODE", "informational").strip().lower()
    if raw in ("clinical", "prod", "production"):
        return "clinical"
    return "informational"


def is_clinical_mode() -> bool:
    """Checks whether the backend is operating in clinical mode."""
    return get_app_mode() == "clinical"


def is_informational_mode() -> bool:
    """Checks whether the backend is operating in informational mode."""
    return get_app_mode() == "informational"


def validate_deployment_mode_on_startup() -> None:
    """Validates operational mode prerequisites on startup.
    
    In Informational Mode:
      - Validates cleanly without requiring enterprise hospital infrastructure.
      
    In Clinical Mode:
      - Strictly refuses to run unless all four enterprise readiness conditions are met:
        1. Managed DB with confirmed backup strategy (MANAGED_DB_BACKUPS_CONFIRMED=true).
        2. Multi-factor authentication enforced (MFA_REQUIRED=true).
        3. Demo/mock accounts disabled (ALLOW_DEMO_USERS=false).
        4. Persistent encryption key supplied via secrets manager (SECRETS_STORE_MANAGED=true).
    """
    mode = get_app_mode()
    logger.info("TrustFed-Health operating mode: [%s]", mode.upper())

    if mode == "clinical":
        errors = []

        # 1. Managed DB with confirmed automated backups
        managed_db = os.getenv("MANAGED_DB_BACKUPS_CONFIRMED", "").strip().lower() in ("true", "1", "yes")
        db_url = os.getenv("SUPABASE_DB_URL", "")
        if not managed_db:
            errors.append(
                "MANAGED_DB_BACKUPS_CONFIRMED=true is required. "
                "Clinical mode requires verified automated backups and point-in-time recovery on the database."
            )
        elif not db_url or "sqlite" in db_url.lower():
            errors.append(
                "A managed PostgreSQL connection (SUPABASE_DB_URL) is required in Clinical Mode. Local SQLite is prohibited."
            )

        # 2. MFA enabled / enforced
        mfa_required = (
            os.getenv("MFA_REQUIRED", "").strip().lower() in ("true", "1", "yes") or
            os.getenv("MFA_ENABLED", "").strip().lower() in ("true", "1", "yes")
        )
        if not mfa_required:
            errors.append(
                "MFA_REQUIRED=true is required. Clinical accounts must be guarded by Multi-Factor Authentication."
            )

        # 3. Demo accounts disabled
        allow_demo = os.getenv("ALLOW_DEMO_USERS", "true").strip().lower() in ("true", "1", "yes")
        if allow_demo:
            errors.append(
                "ALLOW_DEMO_USERS=false is required in Clinical Mode. Hardcoded demo credentials must be disabled."
            )

        # 4. Encryption key from a managed secrets store
        enc_key = os.getenv("PATIENT_ENCRYPTION_KEY", "").strip()
        secrets_store = os.getenv("SECRETS_STORE_MANAGED", "").strip().lower() in ("true", "1", "yes")
        if not enc_key or len(enc_key) < 32:
            errors.append(
                "PATIENT_ENCRYPTION_KEY must be a valid 32-byte base64 encryption key."
            )
        if not secrets_store:
            errors.append(
                "SECRETS_STORE_MANAGED=true is required in Clinical Mode to confirm keys originate from a verified secrets store."
            )

        if errors:
            formatted_errors = "\n  - " + "\n  - ".join(errors)
            msg = (
                f"FATAL: TrustFed startup refused in CLINICAL MODE due to unfulfilled security prerequisites:{formatted_errors}\n"
                "To run with public/synthetic datasets in educational prototype mode, set APP_MODE=informational (default)."
            )
            logger.critical(msg)
            raise RuntimeError(msg)
