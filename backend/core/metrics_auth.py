"""Authentication and internal token verification for metrics and telemetry endpoints."""
from __future__ import annotations
import os
from typing import Optional, Any
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from services import auth

INTERNAL_METRICS_TOKEN_DEFAULT = "trustfed-internal-metrics-secret"

def get_internal_metrics_token() -> str:
    return os.getenv("INTERNAL_METRICS_TOKEN", INTERNAL_METRICS_TOKEN_DEFAULT).strip()

def verify_metrics_access(
    authorization: Optional[str] = Header(None),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token"),
    x_metrics_token: Optional[str] = Header(None, alias="X-Metrics-Token"),
    db: Session = Depends(get_db)
) -> Any:
    """Ensures caller provides either a valid Bearer JWT or an internal token."""
    # 1. Check internal token
    valid_internal = get_internal_metrics_token()
    candidate_token = (x_internal_token or x_metrics_token or "").strip()
    if candidate_token and candidate_token == valid_internal:
        return {"auth_type": "internal_token"}

    # 2. Check standard JWT Bearer token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = auth.decode_token(token)
            return payload
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired Bearer token")

    raise HTTPException(
        status_code=401,
        detail="Authentication required: provide valid Bearer token or X-Internal-Token"
    )
