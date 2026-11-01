"""Authentication and internal token verification for metrics and telemetry endpoints.

Guarantees:
- Endpoints (/metrics, /prediction/metrics, /system/metrics) restricted exclusively to:
  1. Authenticated global_admin users (via Bearer JWT).
  2. Internal background monitoring services presenting X-Internal-Token matching INTERNAL_METRICS_TOKEN.
- Non-global-admin roles (doctor, hospital_staff, regional_admin) are blocked with HTTP 403 Forbidden.
- Production startup refusal if INTERNAL_METRICS_TOKEN is unset, insecure, or equals previously committed defaults.
"""
from __future__ import annotations
import hmac
import logging
import os
import secrets
from typing import Optional, Any
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from services import auth

logger = logging.getLogger("trustfed.metrics_auth")

BANNED_INTERNAL_METRICS_TOKENS = {
    "", "default", "change-me", "secret", "password", "test", "demo",
    "trustfed-internal-metrics-secret",  # Rotated / deprecated committed token
    "internal-metrics-secret", "metrics-token"
}

_EPHEMERAL_DEV_TOKEN: Optional[str] = None


def get_internal_metrics_token() -> str:
    """Retrieve internal metrics token from environment, with secure ephemeral fallback in dev."""
    global _EPHEMERAL_DEV_TOKEN
    configured = os.getenv("INTERNAL_METRICS_TOKEN", "").strip()
    if configured:
        return configured
    # In non-production environments, generate an ephemeral random token once per process
    if _EPHEMERAL_DEV_TOKEN is None:
        _EPHEMERAL_DEV_TOKEN = secrets.token_urlsafe(32)
        logger.info("[METRICS AUTH] Generated ephemeral in-memory internal metrics token for local session.")
    return _EPHEMERAL_DEV_TOKEN


def validate_internal_metrics_token_on_startup() -> None:
    """Refuse to start in production if INTERNAL_METRICS_TOKEN is missing or insecure."""
    env = os.getenv("ENVIRONMENT", "development").strip().lower()
    is_production = env in ("production", "prod")
    token = os.getenv("INTERNAL_METRICS_TOKEN", "").strip()

    if is_production:
        if not token:
            msg = (
                "FATAL: INTERNAL_METRICS_TOKEN environment variable is required in production. "
                "Backend startup refused. Supply a high-entropy secret (>= 24 characters) in the host environment."
            )
            logger.critical(msg)
            raise RuntimeError(msg)
        if token.lower() in BANNED_INTERNAL_METRICS_TOKENS or len(token) < 24:
            msg = (
                "FATAL: INTERNAL_METRICS_TOKEN is insecure, too short (< 24 chars), or matches a deprecated token. "
                "Backend startup refused. Rotate to a cryptographically random secret."
            )
            logger.critical(msg)
            raise RuntimeError(msg)


def verify_metrics_access(
    authorization: Optional[str] = Header(None),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token"),
    x_metrics_token: Optional[str] = Header(None, alias="X-Metrics-Token"),
    db: Session = Depends(get_db)
) -> Any:
    """Ensures caller provides either a valid global_admin Bearer token or the internal token."""
    # 1. Check internal token
    valid_internal = get_internal_metrics_token()
    candidate_token = (x_internal_token or x_metrics_token or "").strip()
    if candidate_token:
        if hmac.compare_digest(candidate_token.encode("utf-8"), valid_internal.encode("utf-8")):
            return {"auth_type": "internal_token", "role": "internal"}
        raise HTTPException(
            status_code=401,
            detail="Invalid internal metrics token"
        )

    # 2. Check standard JWT Bearer token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = auth.decode_token(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired Bearer token")

        # Restrict metrics access exclusively to global_admin
        role = payload.get("role")
        if role != "global_admin":
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden: role '{role}' is not authorized. Metrics endpoints require global_admin role or internal token."
            )
        return payload

    raise HTTPException(
        status_code=401,
        detail="Authentication required: provide global_admin Bearer token or X-Internal-Token"
    )
