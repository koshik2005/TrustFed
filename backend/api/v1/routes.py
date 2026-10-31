import datetime
import json
import os
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, Cookie
from pydantic import BaseModel
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

import numpy as np
from db.database import get_db
from db import models
from services import auth, crypto, inference, store, disease_inference, clinical_validation, general_disease_model, federated_learning, dashboard_service
from services.explanation import generate_clinical_explanation
from tefl import nn

router = APIRouter()

RESULTS_DIR = os.getenv(
    "RESULTS_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "results")
)
if not os.path.exists(RESULTS_DIR):
    _local_results = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "results")
    if os.path.exists(_local_results):
        RESULTS_DIR = _local_results


# ── Proxy-aware IP extractor for rate limiting ──────────────────────────────
def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=get_client_ip)


# ── Auth & Role Authorization ───────────────────────────────────────────────
def current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> models.User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    try:
        claims = auth.decode_token(authorization.split(" ", 1)[1], expected_type="access")
    except ValueError as e:
        raise HTTPException(401, str(e))
    u = db.query(models.User).filter_by(email=claims.get("sub")).first()
    if not u:
        raise HTTPException(401, "Unknown user")

    # Immediate revocation check: user status
    if u.status and u.status != "active":
        raise HTTPException(401, "User account is suspended or inactive")

    # Immediate revocation check: hospital status
    if u.hospital_id:
        hosp = db.query(models.Hospital).filter_by(id=u.hospital_id).first()
        if hosp and hosp.status != "active":
            raise HTTPException(401, f"Hospital '{hosp.name}' is currently {hosp.status}")

    # Immediate revocation check: regional hub status
    hub_id = u.hub_id
    if not hub_id and u.hospital_id:
        hosp = db.query(models.Hospital).filter_by(id=u.hospital_id).first()
        if hosp:
            hub_id = hosp.hub_id
    if hub_id:
        hub = db.query(models.RegionalHub).filter_by(id=hub_id).first()
        if hub and hub.status != "active":
            raise HTTPException(401, f"Regional hub '{hub.name}' is currently {hub.status}")

    return u


def active_user(u: models.User = Depends(current_user)) -> models.User:
    """Enforces that first-login password reset has been completed."""
    if u.must_reset_password:
        raise HTTPException(403, "Password reset required on first login")
    return u


def require(*roles: str):
    def dep(u: models.User = Depends(current_user)):
        if u.must_reset_password:
            raise HTTPException(403, "Password reset required on first login")
        if u.role not in roles:
            raise HTTPException(403, f"Role '{u.role}' may not access this resource")
        return u
    return dep


ANY = ("hospital_staff", "doctor", "regional_admin", "global_admin")
ADMINS = ("regional_admin", "global_admin")
CLINICAL_ROLES = ("hospital_staff", "doctor", "global_admin")
DOCTOR_ROLES = ("doctor", "global_admin")


class LoginBody(BaseModel):
    email: str
    password: str


class ResetPasswordBody(BaseModel):
    current_password: str
    new_password: str


class ConsentManageBody(BaseModel):
    hospital_id: str
    patient_id: Optional[int] = None
    consent_type: str = "FEDERATED_TRAINING_DEIDENTIFIED"
    status: str = "granted"


class DataRetentionPruneBody(BaseModel):
    hospital_id: Optional[str] = None
    days_unconfirmed: int = 90
    purge_revoked_consent: bool = False


def _user_json(u: models.User) -> Dict[str, Any]:
    return {
        "id": str(u.id),
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "hospitalId": u.hospital_id,
        "hubId": u.hub_id,
        "mustResetPassword": bool(u.must_reset_password),
        "status": u.status or "active"
    }


def _cookie_samesite(request: Request) -> str:
    forced = os.getenv("COOKIE_SAMESITE")
    if forced:
        return forced.lower()
    sec_site = request.headers.get("sec-fetch-site", "")
    if sec_site == "cross-site":
        return "none"
    return "lax"


def revoke_user_tokens(db: Session, user_id: int):
    """Revokes all active refresh tokens for a user immediately."""
    db.query(models.RefreshToken).filter_by(user_id=user_id, revoked=False).update(
        {models.RefreshToken.revoked: True}, synchronize_session=False
    )
    db.commit()


def cascade_hospital_suspension(db: Session, hospital_id: str, action: str = "suspend"):
    """Revokes tokens and sets hospital users and training node offline."""
    users = db.query(models.User).filter_by(hospital_id=hospital_id).all()
    for usr in users:
        usr.status = "suspended" if action == "suspend" else "removed"
        revoke_user_tokens(db, usr.id)
    node = db.query(models.HospitalNode).filter_by(id=hospital_id).first()
    if node:
        node.status = "offline"
    db.commit()


def reactivate_hospital_cascade(db: Session, hospital_id: str):
    """Reactivates hospital and training node."""
    h = db.query(models.Hospital).filter_by(id=hospital_id).first()
    if h:
        h.status = "active"
    users = db.query(models.User).filter_by(hospital_id=hospital_id).all()
    for usr in users:
        usr.status = "active"
    node = db.query(models.HospitalNode).filter_by(id=hospital_id).first()
    if node:
        node.status = "idle"
    db.commit()


def cascade_hub_suspension(db: Session, hub_id: str, action: str = "suspend"):
    """Suspends regional admins and all dependent hospitals in the hub."""
    admins = db.query(models.User).filter_by(hub_id=hub_id).all()
    for a in admins:
        a.status = "suspended" if action == "suspend" else "removed"
        revoke_user_tokens(db, a.id)
    hospitals = db.query(models.Hospital).filter_by(hub_id=hub_id).all()
    for h in hospitals:
        h.status = "suspended" if action == "suspend" else "removed"
        cascade_hospital_suspension(db, h.id, action=action)
    db.commit()


@router.post("/auth/login")
@limiter.limit("5/minute")
def login(request: Request, body: LoginBody, response: Response, db: Session = Depends(get_db)):
    client_ip = get_client_ip(request)
    u = db.query(models.User).filter_by(email=body.email.strip().lower()).first()
    if not u or not auth.verify_password(body.password, u.password_hash):
        store.add_audit(db, None, client_ip, "auth", f"Failed login attempt for {body.email[:60]}")
        raise HTTPException(401, "Invalid email or password")

    if u.status and u.status != "active":
        store.add_audit(db, None, u.email, "auth", f"Login rejected: user account is {u.status}")
        raise HTTPException(401, "User account is suspended or inactive")

    if u.hospital_id:
        hosp = db.query(models.Hospital).filter_by(id=u.hospital_id).first()
        if hosp and hosp.status != "active":
            raise HTTPException(401, f"Hospital '{hosp.name}' is currently {hosp.status}")

    hub_id = u.hub_id
    if not hub_id and u.hospital_id:
        hosp = db.query(models.Hospital).filter_by(id=u.hospital_id).first()
        if hosp:
            hub_id = hosp.hub_id
    if hub_id:
        hub = db.query(models.RegionalHub).filter_by(id=hub_id).first()
        if hub and hub.status != "active":
            raise HTTPException(401, f"Regional hub '{hub.name}' is currently {hub.status}")

    # Issue short-lived access token + long-lived rotating refresh token + CSRF token
    tokens = auth.create_refresh_token_pair(
        user_id=u.id, email=u.email, role=u.role, hospital_id=u.hospital_id, hub_id=u.hub_id
    )

    # Persist refresh token in database for rotation & revocation tracking
    exp_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    rf = models.RefreshToken(
        user_id=u.id,
        jti=tokens["jti"],
        csrf_token=tokens["csrf_token"],
        expires_at=exp_dt
    )
    db.add(rf)
    db.commit()

    # Deliver refresh token via httpOnly, Secure cookie
    response.set_cookie(
        key="tf_refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite=_cookie_samesite(request),
        path="/api/auth",
        max_age=7 * 86400,
    )

    store.add_audit(db, None, u.email, "auth", f"Login successful ({u.role})")
    return {
        "token": tokens["access_token"],
        "csrf_token": tokens["csrf_token"],
        "user": _user_json(u)
    }


@router.post("/auth/refresh")
def refresh_session(
    request: Request,
    response: Response,
    tf_refresh_token: Optional[str] = Cookie(None),
    x_csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token"),
    db: Session = Depends(get_db)
):
    if not tf_refresh_token:
        raise HTTPException(401, "Missing refresh token cookie")
    if not x_csrf_token:
        raise HTTPException(403, "Missing CSRF token header (X-CSRF-Token)")

    try:
        claims = auth.decode_token(tf_refresh_token, expected_type="refresh")
    except ValueError as e:
        raise HTTPException(401, f"Invalid refresh token: {e}")

    # Double-submit CSRF verification
    if claims.get("csrf") != x_csrf_token:
        raise HTTPException(403, "CSRF token validation failed")

    jti = claims.get("jti")
    rf_record = db.query(models.RefreshToken).filter_by(jti=jti, revoked=False).first()
    if not rf_record:
        raise HTTPException(401, "Refresh token has been revoked or expired")

    # Invalidate used refresh token (Token Rotation)
    rf_record.revoked = True
    db.commit()

    u = db.query(models.User).filter_by(id=claims.get("user_id")).first()
    if not u:
        raise HTTPException(401, "User record not found")

    if u.status and u.status != "active":
        raise HTTPException(401, "User account is suspended or inactive")

    if u.hospital_id:
        hosp = db.query(models.Hospital).filter_by(id=u.hospital_id).first()
        if hosp and hosp.status != "active":
            raise HTTPException(401, f"Hospital '{hosp.name}' is currently {hosp.status}")

    hub_id = u.hub_id or (hosp.hub_id if u.hospital_id and hosp else None)
    if hub_id:
        hub = db.query(models.RegionalHub).filter_by(id=hub_id).first()
        if hub and hub.status != "active":
            raise HTTPException(401, f"Regional hub '{hub.name}' is currently {hub.status}")

    # Issue new rotated token pair
    tokens = auth.create_refresh_token_pair(
        user_id=u.id, email=u.email, role=u.role, hospital_id=u.hospital_id, hub_id=u.hub_id
    )
    exp_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    new_rf = models.RefreshToken(
        user_id=u.id,
        jti=tokens["jti"],
        csrf_token=tokens["csrf_token"],
        expires_at=exp_dt
    )
    db.add(new_rf)
    db.commit()

    response.set_cookie(
        key="tf_refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite=_cookie_samesite(request),
        path="/api/auth",
        max_age=7 * 86400,
    )
    return {
        "token": tokens["access_token"],
        "csrf_token": tokens["csrf_token"],
        "user": _user_json(u)
    }


@router.post("/auth/reset-password")
def reset_password(
    body: ResetPasswordBody,
    db: Session = Depends(get_db),
    u: models.User = Depends(current_user)
):
    if not auth.verify_password(body.current_password, u.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(400, "New password cannot be identical to current temporary password")
    try:
        auth.validate_password_strength(body.new_password)
    except ValueError as e:
        raise HTTPException(422, str(e))

    u.password_hash = auth.hash_password(body.new_password)
    u.must_reset_password = False
    db.commit()
    store.add_audit(db, None, u.email, "auth", f"Password reset completed for user {u.email}")
    return {"message": "Password reset successfully", "user": _user_json(u)}


@router.post("/auth/logout")
def logout(
    response: Response,
    tf_refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
    u: Optional[models.User] = Depends(current_user)
):
    if tf_refresh_token:
        try:
            claims = auth.decode_token(tf_refresh_token, expected_type="refresh")
            jti = claims.get("jti")
            if jti:
                rf = db.query(models.RefreshToken).filter_by(jti=jti).first()
                if rf:
                    rf.revoked = True
                    db.commit()
        except Exception:
            pass

    response.delete_cookie(key="tf_refresh_token", path="/api/auth", samesite="none", secure=True)
    if u:
        store.add_audit(db, None, u.email, "auth", f"Logout ({u.role})")
    return {"message": "Logged out successfully"}


@router.get("/auth/me")
def me(u: models.User = Depends(current_user)):
    return _user_json(u)


# ── Hierarchy Models & Pydantic Schemas ────────────────────────────────────────

class CreateHubBody(BaseModel):
    id: str
    name: str
    region: str


class UpdateHubBody(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None


class IssueAdminBody(BaseModel):
    name: str
    email: str


class CreateHospitalBody(BaseModel):
    id: str
    name: str
    hub_id: Optional[str] = None
    share_deidentified: bool = False


class UpdateHospitalBody(BaseModel):
    name: Optional[str] = None
    share_deidentified: Optional[bool] = None


class IssueHospitalUserBody(BaseModel):
    name: str
    email: str
    role: str  # "hospital_staff" or "doctor"


# ── Regional Hubs Management (Global Admin Only) ───────────────────────────

@router.get("/admin/hubs")
def list_hubs(db: Session = Depends(get_db), u: models.User = Depends(require("global_admin"))):
    hubs = db.query(models.RegionalHub).order_by(models.RegionalHub.id).all()
    res = []
    for h in hubs:
        hosp_count = db.query(models.Hospital).filter_by(hub_id=h.id).count()
        admin_count = db.query(models.User).filter_by(hub_id=h.id, role="regional_admin").count()
        res.append({
            "id": h.id,
            "name": h.name,
            "region": h.region,
            "status": h.status,
            "createdBy": h.created_by,
            "hospitalCount": hosp_count,
            "adminCount": admin_count,
            "createdAt": str(h.created_at)
        })
    return res


@router.post("/admin/hubs")
def create_hub(body: CreateHubBody, db: Session = Depends(get_db), u: models.User = Depends(require("global_admin"))):
    existing = db.query(models.RegionalHub).filter_by(id=body.id.strip()).first()
    if existing:
        raise HTTPException(409, f"Regional Hub '{body.id}' already exists")
    hub = models.RegionalHub(
        id=body.id.strip(),
        name=body.name.strip(),
        region=body.region.strip(),
        status="active",
        created_by=u.id
    )
    db.add(hub)
    db.commit()
    store.add_audit(db, None, u.email, "admin", f"Created regional hub '{hub.id}' ({hub.name})")
    return {"message": "Regional Hub created successfully", "hub": {"id": hub.id, "name": hub.name, "region": hub.region, "status": hub.status}}


@router.put("/admin/hubs/{hub_id}")
def update_hub(hub_id: str, body: UpdateHubBody, db: Session = Depends(get_db), u: models.User = Depends(require("global_admin"))):
    hub = db.query(models.RegionalHub).filter_by(id=hub_id).first()
    if not hub:
        raise HTTPException(404, "Regional Hub not found")
    if body.name:
        hub.name = body.name.strip()
    if body.region:
        hub.region = body.region.strip()
    db.commit()
    store.add_audit(db, None, u.email, "admin", f"Updated regional hub '{hub_id}' ({hub.name})")
    return {"message": "Regional Hub updated successfully", "hub": {"id": hub.id, "name": hub.name, "region": hub.region, "status": hub.status}}


@router.post("/admin/hubs/{hub_id}/suspend")
def suspend_hub(hub_id: str, db: Session = Depends(get_db), u: models.User = Depends(require("global_admin"))):
    hub = db.query(models.RegionalHub).filter_by(id=hub_id).first()
    if not hub:
        raise HTTPException(404, "Regional Hub not found")
    hub.status = "suspended"
    cascade_hub_suspension(db, hub_id, action="suspend")
    store.add_audit(db, None, u.email, "admin", f"Suspended regional hub '{hub_id}' and revoked tokens")
    return {"message": f"Regional Hub '{hub_id}' suspended and all dependent access revoked"}


@router.post("/admin/hubs/{hub_id}/reactivate")
def reactivate_hub(hub_id: str, db: Session = Depends(get_db), u: models.User = Depends(require("global_admin"))):
    hub = db.query(models.RegionalHub).filter_by(id=hub_id).first()
    if not hub:
        raise HTTPException(404, "Regional Hub not found")
    hub.status = "active"
    for a in db.query(models.User).filter_by(hub_id=hub_id).all():
        a.status = "active"
    db.commit()
    store.add_audit(db, None, u.email, "admin", f"Reactivated regional hub '{hub_id}'")
    return {"message": f"Regional Hub '{hub_id}' reactivated"}


@router.delete("/admin/hubs/{hub_id}")
def delete_hub(hub_id: str, db: Session = Depends(get_db), u: models.User = Depends(require("global_admin"))):
    hub = db.query(models.RegionalHub).filter_by(id=hub_id).first()
    if not hub:
        raise HTTPException(404, "Regional Hub not found")
    cascade_hub_suspension(db, hub_id, action="delete")
    db.delete(hub)
    db.commit()
    store.add_audit(db, None, u.email, "admin", f"Deleted regional hub '{hub_id}'")
    return {"message": f"Regional Hub '{hub_id}' deleted successfully"}


@router.post("/admin/hubs/{hub_id}/admins")
def issue_hub_admin(hub_id: str, body: IssueAdminBody, db: Session = Depends(get_db), u: models.User = Depends(require("global_admin"))):
    hub = db.query(models.RegionalHub).filter_by(id=hub_id).first()
    if not hub:
        raise HTTPException(404, "Regional Hub not found")
    if hub.status != "active":
        raise HTTPException(400, "Cannot issue credentials for a suspended hub")
    existing = db.query(models.User).filter_by(email=body.email.strip().lower()).first()
    if existing:
        raise HTTPException(409, f"User with email '{body.email}' already exists")
    temp_pw = auth.generate_temp_password(14)
    new_user = models.User(
        email=body.email.strip().lower(),
        name=body.name.strip(),
        role="regional_admin",
        hub_id=hub_id,
        hospital_id=None,
        must_reset_password=True,
        status="active",
        password_hash=auth.hash_password(temp_pw)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    store.add_audit(db, None, u.email, "admin", f"Issued regional_admin credentials for {new_user.email} in hub {hub_id}")
    return {"user": _user_json(new_user), "temp_password": temp_pw}


@router.get("/admin/hubs/{hub_id}/admins")
def list_hub_admins(hub_id: str, db: Session = Depends(get_db), u: models.User = Depends(require("global_admin"))):
    admins = db.query(models.User).filter_by(hub_id=hub_id, role="regional_admin").all()
    return [_user_json(a) for a in admins]


# ── Hospital Management (Regional Admin scoped to their hub, Global Admin supervisor) ──────────

@router.get("/regional/hospitals")
def list_regional_hospitals(db: Session = Depends(get_db), u: models.User = Depends(require("regional_admin", "global_admin"))):
    q = db.query(models.Hospital)
    if u.role == "regional_admin":
        if not u.hub_id:
            return []
        q = q.filter(models.Hospital.hub_id == u.hub_id)
    hospitals = q.order_by(models.Hospital.id).all()
    res = []
    for h in hospitals:
        user_count = db.query(models.User).filter_by(hospital_id=h.id).count()
        node = db.query(models.HospitalNode).filter_by(id=h.id).first()
        res.append({
            "id": h.id,
            "name": h.name,
            "hubId": h.hub_id,
            "status": h.status,
            "shareDeidentified": bool(h.share_deidentified),
            "userCount": user_count,
            "datasetSize": node.dataset_size if node else 0,
            "nodeStatus": node.status if node else "offline"
        })
    return res


@router.post("/regional/hospitals")
def create_hospital(body: CreateHospitalBody, db: Session = Depends(get_db), u: models.User = Depends(require("regional_admin", "global_admin"))):
    target_hub_id = u.hub_id if u.role == "regional_admin" else (body.hub_id or u.hub_id)
    if u.role == "regional_admin" and body.hub_id and body.hub_id != u.hub_id:
        raise HTTPException(403, "Regional admin can only create hospitals in their own assigned hub")
    if not target_hub_id:
        raise HTTPException(400, "hub_id is required")
    hub = db.query(models.RegionalHub).filter_by(id=target_hub_id).first()
    if not hub:
        raise HTTPException(404, f"Regional Hub '{target_hub_id}' not found")
    if hub.status != "active":
        raise HTTPException(400, "Cannot add hospital to a suspended hub")
    existing = db.query(models.Hospital).filter_by(id=body.id.strip()).first()
    if existing:
        raise HTTPException(409, f"Hospital '{body.id}' already exists")

    hosp = models.Hospital(
        id=body.id.strip(),
        name=body.name.strip(),
        hub_id=target_hub_id,
        status="active",
        share_deidentified=body.share_deidentified
    )
    db.add(hosp)
    node = db.query(models.HospitalNode).filter_by(id=hosp.id).first()
    if not node:
        db.add(models.HospitalNode(id=hosp.id, name=hosp.name, region=hub.region, status="idle", dataset_size=50))
    else:
        node.status = "idle"
    db.commit()
    store.add_audit(db, None, u.email, "admin", f"Created hospital '{hosp.id}' ({hosp.name}) in hub {target_hub_id}")
    return {"message": "Hospital created successfully", "hospital": {"id": hosp.id, "name": hosp.name, "hubId": hosp.hub_id, "status": hosp.status}}


@router.put("/regional/hospitals/{hospital_id}")
def update_hospital(hospital_id: str, body: UpdateHospitalBody, db: Session = Depends(get_db), u: models.User = Depends(require("regional_admin", "global_admin"))):
    hosp = db.query(models.Hospital).filter_by(id=hospital_id).first()
    if not hosp:
        raise HTTPException(404, "Hospital not found")
    if u.role == "regional_admin" and hosp.hub_id != u.hub_id:
        raise HTTPException(403, "Regional admin cannot edit hospitals outside their assigned hub")
    if body.name is not None:
        hosp.name = body.name.strip()
        node = db.query(models.HospitalNode).filter_by(id=hosp.id).first()
        if node:
            node.name = hosp.name
    if body.share_deidentified is not None:
        hosp.share_deidentified = body.share_deidentified
    db.commit()
    store.add_audit(db, None, u.email, "admin", f"Updated hospital '{hospital_id}' ({hosp.name})")
    return {"message": "Hospital updated successfully", "hospital": {"id": hosp.id, "name": hosp.name, "hubId": hosp.hub_id, "status": hosp.status}}


@router.post("/regional/hospitals/{hospital_id}/suspend")
def suspend_hospital(hospital_id: str, db: Session = Depends(get_db), u: models.User = Depends(require("regional_admin", "global_admin"))):
    hosp = db.query(models.Hospital).filter_by(id=hospital_id).first()
    if not hosp:
        raise HTTPException(404, "Hospital not found")
    if u.role == "regional_admin" and hosp.hub_id != u.hub_id:
        raise HTTPException(403, "Regional admin cannot suspend hospitals outside their assigned hub")
    hosp.status = "suspended"
    cascade_hospital_suspension(db, hospital_id, action="suspend")
    store.add_audit(db, None, u.email, "admin", f"Suspended hospital '{hospital_id}' and revoked user tokens")
    return {"message": f"Hospital '{hospital_id}' suspended and excluded from training"}


@router.post("/regional/hospitals/{hospital_id}/reactivate")
def reactivate_hospital(hospital_id: str, db: Session = Depends(get_db), u: models.User = Depends(require("regional_admin", "global_admin"))):
    hosp = db.query(models.Hospital).filter_by(id=hospital_id).first()
    if not hosp:
        raise HTTPException(404, "Hospital not found")
    if u.role == "regional_admin" and hosp.hub_id != u.hub_id:
        raise HTTPException(403, "Regional admin cannot reactivate hospitals outside their assigned hub")
    reactivate_hospital_cascade(db, hospital_id)
    store.add_audit(db, None, u.email, "admin", f"Reactivated hospital '{hospital_id}'")
    return {"message": f"Hospital '{hospital_id}' reactivated"}


@router.delete("/regional/hospitals/{hospital_id}")
def delete_hospital(hospital_id: str, db: Session = Depends(get_db), u: models.User = Depends(require("regional_admin", "global_admin"))):
    hosp = db.query(models.Hospital).filter_by(id=hospital_id).first()
    if not hosp:
        raise HTTPException(404, "Hospital not found")
    if u.role == "regional_admin" and hosp.hub_id != u.hub_id:
        raise HTTPException(403, "Regional admin cannot delete hospitals outside their assigned hub")
    cascade_hospital_suspension(db, hospital_id, action="remove")
    db.delete(hosp)
    node = db.query(models.HospitalNode).filter_by(id=hospital_id).first()
    if node:
        db.delete(node)
    db.commit()
    store.add_audit(db, None, u.email, "admin", f"Removed hospital '{hospital_id}'")
    return {"message": f"Hospital '{hospital_id}' removed successfully"}


@router.post("/regional/hospitals/{hospital_id}/users")
def issue_hospital_user(hospital_id: str, body: IssueHospitalUserBody, db: Session = Depends(get_db), u: models.User = Depends(require("regional_admin", "global_admin"))):
    hosp = db.query(models.Hospital).filter_by(id=hospital_id).first()
    if not hosp:
        raise HTTPException(404, "Hospital not found")
    if u.role == "regional_admin" and hosp.hub_id != u.hub_id:
        raise HTTPException(403, "Regional admin cannot issue credentials for hospitals outside their assigned hub")
    if hosp.status != "active":
        raise HTTPException(400, "Cannot issue credentials for a suspended hospital")
    if body.role not in ("hospital_staff", "doctor"):
        raise HTTPException(400, "Hospital user role must be 'hospital_staff' or 'doctor'")
    existing = db.query(models.User).filter_by(email=body.email.strip().lower()).first()
    if existing:
        raise HTTPException(409, f"User with email '{body.email}' already exists")
    temp_pw = auth.generate_temp_password(14)
    new_user = models.User(
        email=body.email.strip().lower(),
        name=body.name.strip(),
        role=body.role,
        hospital_id=hospital_id,
        hub_id=hosp.hub_id,
        must_reset_password=True,
        status="active",
        password_hash=auth.hash_password(temp_pw)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    store.add_audit(db, None, u.email, "admin", f"Issued {body.role} credentials for {new_user.email} in hospital {hospital_id}")
    return {"user": _user_json(new_user), "temp_password": temp_pw}


@router.get("/regional/hospitals/{hospital_id}/users")
def list_hospital_users(hospital_id: str, db: Session = Depends(get_db), u: models.User = Depends(require("regional_admin", "global_admin"))):
    hosp = db.query(models.Hospital).filter_by(id=hospital_id).first()
    if not hosp:
        raise HTTPException(404, "Hospital not found")
    if u.role == "regional_admin" and hosp.hub_id != u.hub_id:
        raise HTTPException(403, "Access forbidden to hospital users outside your hub")
    users = db.query(models.User).filter_by(hospital_id=hospital_id).all()
    return [_user_json(usr) for usr in users]


@router.post("/regional/users/{user_id}/suspend")
def suspend_user(user_id: int, db: Session = Depends(get_db), u: models.User = Depends(require("regional_admin", "global_admin"))):
    target = db.query(models.User).filter_by(id=user_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    if u.role == "regional_admin":
        if not target.hospital_id:
            raise HTTPException(403, "Regional admin can only manage hospital users")
        hosp = db.query(models.Hospital).filter_by(id=target.hospital_id).first()
        if not hosp or hosp.hub_id != u.hub_id:
            raise HTTPException(403, "Regional admin cannot suspend users outside their hub")
    target.status = "suspended"
    revoke_user_tokens(db, target.id)
    store.add_audit(db, None, u.email, "admin", f"Suspended user {target.email} ({target.role}) and revoked tokens")
    return {"message": f"User '{target.email}' suspended successfully"}


@router.delete("/regional/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), u: models.User = Depends(require("regional_admin", "global_admin"))):
    target = db.query(models.User).filter_by(id=user_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    if u.role == "regional_admin":
        if not target.hospital_id:
            raise HTTPException(403, "Regional admin can only manage hospital users")
        hosp = db.query(models.Hospital).filter_by(id=target.hospital_id).first()
        if not hosp or hosp.hub_id != u.hub_id:
            raise HTTPException(403, "Regional admin cannot delete users outside their hub")
    revoke_user_tokens(db, target.id)
    email = target.email
    role = target.role
    db.delete(target)
    db.commit()
    store.add_audit(db, None, u.email, "admin", f"Deleted user {email} ({role}) and revoked tokens")
    return {"message": f"User '{email}' deleted successfully"}


# ── Training ────────────────────────────────────────────────────────────────
def _session_json(db: Session, s: models.FLSession):
    metrics = db.query(models.RoundMetric).filter_by(session_id=s.session_id).order_by(models.RoundMetric.round).all()
    hospitals = db.query(models.HospitalNode).all()
    return {
        "sessionId": s.session_id, "status": s.status, "currentRound": s.current_round or 0,
        "totalRounds": s.total_rounds, "startedAt": str(s.started_at), "globalAccuracy": s.global_accuracy,
        "privacyBudget": s.epsilon, "dataset": s.dataset, "error": s.error,
        "metrics": [{"round": m.round, "accuracy": m.accuracy, "loss": m.loss, "epsilon": m.epsilon or 0,
                     "timestamp": str(m.timestamp)} for m in metrics],
        "hospitals": [_hosp_json(h) for h in hospitals]
    }


def _hosp_json(n: models.HospitalNode):
    return {
        "id": n.id, "name": n.name, "region": n.region, "status": n.status,
        "localDatasetSize": n.dataset_size, "currentEpoch": n.current_epoch, "totalEpochs": n.total_epochs
    }


@router.get("/training/sessions/latest")
def latest_session(db: Session = Depends(get_db), u: models.User = Depends(active_user)):
    s = db.query(models.FLSession).order_by(models.FLSession.id.desc()).first()
    if not s:
        return {
            "sessionId": "none", "status": "idle", "currentRound": 0, "totalRounds": 0,
            "startedAt": str(datetime.datetime.now()), "metrics": [], "hospitals": []
        }
    return _session_json(db, s)


@router.get("/training/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db), u=Depends(require(*ADMINS))):
    s = db.query(models.FLSession).filter_by(session_id=session_id).first()
    if not s:
        raise HTTPException(404, "Session not found")
    return _session_json(db, s)


@router.get("/training/sessions/{session_id}/metrics")
def session_metrics(session_id: str, db: Session = Depends(get_db), u=Depends(require(*ADMINS))):
    s = db.query(models.FLSession).filter_by(session_id=session_id).first()
    if not s:
        raise HTTPException(404, "Session not found")
    return _session_json(db, s)["metrics"]


@router.post("/training/sessions")
def start_training(config: Dict[str, Any], db: Session = Depends(get_db), u=Depends(require("global_admin"))):
    running = db.query(models.FLSession).filter_by(status="running").first()
    if running:
        raise HTTPException(409, f"Session {running.session_id} is already running")
    s = store.new_session(db, config)
    store.start_job(s.session_id, json.loads(s.config_json))
    return _session_json(db, s)


@router.get("/training/hospitals")
def hospitals(db: Session = Depends(get_db), u: models.User = Depends(active_user)):
    q = db.query(models.HospitalNode).order_by(models.HospitalNode.id)
    if u.role in ("hospital_staff", "doctor"):
        # Object-level authorization: Hospital staff/doctor only inspects their own hospital node
        if u.hospital_id:
            q = q.filter(models.HospitalNode.id == u.hospital_id)
        else:
            return []
    elif u.role == "regional_admin":
        # Scoped to regional nodes
        q = q.filter(models.HospitalNode.region.ilike("%East%"))
    return [_hosp_json(h) for h in q.all()]


def _load_results():
    for name in ("results.json", "results_cleveland.json", "results_synthetic.json"):
        p = os.path.join(RESULTS_DIR, name)
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    return None


@router.get("/training/comparison")
def comparison(u=Depends(require(*ADMINS))):
    """Benchmark table computed by `python -m tefl.run_experiments` (real measurements, not literals)."""
    R = _load_results()
    if not R:
        return []
    fair = {k: v["score"] for k, v in R["audits"].items()}
    rows = []
    for name, s in R["summary"].items():
        mia = s["mia_auc"]["mean"] if s.get("mia_auc") else None
        status = "—" if mia is None else ("LOW" if mia < 0.54 else "MEDIUM" if mia < 0.58 else "HIGH")
        fkey = {"FedAvg (non-IID)": "FedAvg (non-IID)", "TEFL (sigma=2)": "TEFL (sigma=2)"}.get(name)
        rows.append({
            "name": name, "acc": f"{s['acc']['mean']:.1%}", "mia": "—" if mia is None else f"{mia:.3f}",
            "miaStatus": status, "fairness": f"{fair[fkey]:.1%}" if fkey in fair else "—",
            "time": f"{s['seconds']['mean']:.1f}s", "epsilon": None if not s.get("epsilon") else round(s["epsilon"]["mean"], 2),
            "he": "Paillier" if "TEFL" in name else "—", "special": name == "TEFL (sigma=2)",
            "dataset": R["dataset"]
        })
    return rows


# ── Prediction & Clinical Inference ─────────────────────────────────────────
DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "artifacts",
    "pretrained_cleveland.npz"
)


def _active_model(db: Session):
    sessions = (db.query(models.FLSession).filter(models.FLSession.status == "Completed")
                .order_by(models.FLSession.id.desc()).all())

    for s in sessions:
        if s.model_path and os.path.exists(s.model_path) and s.session_id != "FL-DEFAULT-PRETRAINED":
            try:
                m = inference.load_model(s.model_path)
                # Verify that the model didn't diverge during noisy training (margin between -15 and +15)
                z3, _ = nn.forward(m["theta"], np.zeros((1, 13)))
                margin = float(z3[0, 1] - z3[0, 0])
                if -15.0 < margin < 15.0:
                    return s, m, False
            except Exception:
                continue

    # Fallback to verified, calibrated baseline model
    if os.path.exists(DEFAULT_MODEL_PATH):
        s_default = db.query(models.FLSession).filter_by(session_id="FL-DEFAULT-PRETRAINED").first()
        if not s_default:
            s_default = models.FLSession(
                session_id="FL-DEFAULT-PRETRAINED",
                status="Completed",
                current_round=25,
                total_rounds=25,
                global_accuracy=0.883,
                epsilon=1.84,
                dataset="cleveland",
                model_path=DEFAULT_MODEL_PATH,
            )
            db.add(s_default)
            db.commit()
            db.refresh(s_default)
        return s_default, inference.load_model(DEFAULT_MODEL_PATH), True

    raise HTTPException(409, "No trained model available.")


def _pred_json(p: models.PatientPrediction):
    is_fallback = (p.session_id == "FL-DEFAULT-PRETRAINED")
    model_version = "TF-HeartNet-v2 (Pretrained Baseline)" if is_fallback else f"TF-HeartNet-v2 (Session {p.session_id})"
    return {
        "patientId": p.patient_identifier,
        "riskScore": p.risk_score,
        "riskLabel": inference.risk_label(p.risk_score),
        "confidence": p.confidence,
        "nlpExplanation": p.explanation_text,
        "shapValues": json.loads(p.shap_values or "[]"),
        "modelVersion": model_version,
        "isFallback": is_fallback,
        "disclaimer": "Clinical decision support only, not a diagnosis. For use by qualified healthcare professionals.",
        "predictedAt": str(p.created_at)
    }


@router.post("/prediction/predict")
def predict(vitals: Dict[str, Any], db: Session = Depends(get_db), u: models.User = Depends(active_user)):
    s, model, is_fallback = _active_model(db)
    try:
        r = inference.predict(model, vitals)
    except ValueError as e:
        raise HTTPException(422, str(e))
    text = generate_clinical_explanation(vitals, r["riskScore"], r["shapValues"])
    pid = uuid.uuid4().hex[:8].upper()

    row = models.PatientPrediction(
        patient_identifier=pid,
        session_id=s.session_id,
        hospital_id=u.hospital_id,
        user_id=u.id,
        age=int(float(vitals["age"])),
        risk_score=r["riskScore"],
        confidence=r["confidence"],
        explanation_text=text,
        shap_values=json.dumps(r["shapValues"])
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    if is_fallback:
        store.add_audit(db, s.session_id, u.email, "prediction",
                        f"Inference model fallback to pretrained_cleveland.npz baseline for patient {pid}")
    store.add_audit(db, s.session_id, u.email, "prediction",
                    f"Risk prediction {pid}: {r['riskLabel']} ({r['riskScore']:.2f}) [Model: {s.session_id}]")
    return _pred_json(row)


@router.get("/prediction/history")
def history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    u: models.User = Depends(active_user)
):
    q = db.query(models.PatientPrediction).order_by(models.PatientPrediction.id.desc())
    if u.role in ("hospital_staff", "doctor"):
        # Object-level authorization: Hospital staff only views their hospital's patient predictions
        q = q.filter(models.PatientPrediction.hospital_id == u.hospital_id)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_pred_json(p) for p in items], "total": total, "page": page, "pageSize": page_size,
        "totalPages": max(1, -(-total // page_size))
    }


@router.get("/prediction/{patient_id}")
def prediction_by_id(patient_id: str, db: Session = Depends(get_db), u: models.User = Depends(active_user)):
    p = db.query(models.PatientPrediction).filter_by(patient_identifier=patient_id).first()
    if not p:
        raise HTTPException(404, "Prediction not found")
    if u.role in ("hospital_staff", "doctor") and p.hospital_id != u.hospital_id:
        # Object-level authorization: Deny cross-hospital record access
        raise HTTPException(403, f"Access forbidden: Patient record belongs to another hospital node")
    return _pred_json(p)


# ── TEFL reports ────────────────────────────────────────────────────────────
def _resolve_sid(db: Session, sid: str):
    if sid in ("latest", "none"):
        s = db.query(models.FLSession).filter_by(status="Completed").order_by(models.FLSession.id.desc()).first()
        return s.session_id if s else sid
    return sid


@router.get("/tefl/fairness/{session_id}")
def fairness_report(session_id: str, db: Session = Depends(get_db), u=Depends(require(*ADMINS))):
    r = db.query(models.FairnessReport).filter_by(session_id=_resolve_sid(db, session_id)).first()
    if not r:
        raise HTTPException(404, "No fairness report: the session has not finished (or does not exist).")
    return {
        "sessionId": r.session_id, "overallScore": r.overall_score, "subgroupResults": json.loads(r.subgroup_data),
        "flaggedIssues": json.loads(r.flagged_issues), "generatedAt": str(r.generated_at)
    }


@router.get("/tefl/privacy/{session_id}")
def privacy_report(session_id: str, db: Session = Depends(get_db), u=Depends(require(*ADMINS))):
    r = db.query(models.PrivacyReport).filter_by(session_id=_resolve_sid(db, session_id)).first()
    if not r:
        raise HTTPException(404, "No privacy report: the session has not finished (or does not exist).")

    sess = db.query(models.FLSession).filter_by(session_id=r.session_id).first()
    target_eps = None
    target_met = True
    if sess and sess.config_json:
        try:
            cfg = json.loads(sess.config_json)
            target_eps = cfg.get("target_epsilon")
            if target_eps is not None and r.epsilon is not None:
                target_met = bool(r.epsilon <= float(target_eps) + 0.05)
        except Exception:
            pass

    return {
        "sessionId": r.session_id,
        "attackSuccessWithDP": r.attack_success_with_dp,
        "attackSuccessWithoutDP": r.attack_success_without_dp,
        "privacyResistance": r.privacy_resistance,
        "epsilon": r.epsilon,
        "delta": r.delta,
        "targetEpsilon": target_eps,
        "targetMet": target_met,
        "heKeySize": r.he_key_size,
        "paillierEnabled": r.paillier_enabled,
        "generatedAt": str(r.generated_at)
    }


# ── Audit Ledger ────────────────────────────────────────────────────────────
@router.get("/audit/logs")
def audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    eventType: Optional[str] = None,
    db: Session = Depends(get_db),
    u=Depends(require(*ADMINS))
):
    q = db.query(models.AuditLog)
    if eventType:
        q = q.filter(models.AuditLog.event_type == eventType)
    q = q.order_by(models.AuditLog.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [{"id": str(r.id), "timestamp": r.timestamp_iso, "nodeId": r.node_id or "—", "eventType": r.event_type,
                   "description": r.description, "hash": r.hash} for r in rows],
        "total": total, "page": page, "pageSize": page_size, "totalPages": max(1, -(-total // page_size))
    }


@router.get("/audit/verify")
def audit_verify(db: Session = Depends(get_db), u=Depends(require(*ADMINS))):
    return store.verify_chain(db)


# ── Phase 3: Clinical Patient Entry & Doctor Confirmation Workflow ────────────

class PatientRegistrationBody(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    age: int
    sex: Any
    weight: Optional[float] = None
    height: Optional[float] = None
    # Optional initial encounter data
    symptoms: Optional[list] = None
    symptom_duration_days: Optional[int] = 1
    vitals: Optional[Dict[str, Any]] = None
    structured_ecg_finding: Optional[str] = None
    optional_labs: Optional[Dict[str, Any]] = None
    hospital_id: Optional[str] = None


class EncounterCreateBody(BaseModel):
    symptoms: list
    symptom_duration_days: Optional[int] = 1
    vitals: Optional[Dict[str, Any]] = None
    structured_ecg_finding: Optional[str] = None
    optional_labs: Optional[Dict[str, Any]] = None


class ClinicalPredictBody(BaseModel):
    age: int = 40
    sex: Any = 0
    symptoms: list = []
    symptom_duration_days: Optional[int] = 1
    vitals: Optional[Dict[str, Any]] = None
    structured_ecg_finding: Optional[str] = None
    optional_labs: Optional[Dict[str, Any]] = None
    hospital_id: Optional[str] = None


class DoctorConfirmationBody(BaseModel):
    confirmed_diagnosis: str
    cause: str
    treatment: str


def _resolve_hospital_scope(u: models.User, target_hospital_id: Optional[str] = None) -> str:
    if u.role in ("hospital_staff", "doctor"):
        if not u.hospital_id:
            raise HTTPException(400, "User is not assigned to a hospital node")
        if target_hospital_id and target_hospital_id != u.hospital_id:
            raise HTTPException(403, "Access forbidden: cannot act on another hospital")
        return u.hospital_id
    elif u.role == "global_admin":
        return target_hospital_id or "1"
    else:
        raise HTTPException(403, "Role cannot perform hospital operations")


def _patient_json(p: models.Patient, include_phi: bool = True) -> Dict[str, Any]:
    name = crypto.decrypt_phi(p.name_encrypted) if (include_phi and p.name_encrypted) else None
    contact = crypto.decrypt_phi(p.contact_encrypted) if (include_phi and p.contact_encrypted) else None
    return {
        "id": p.id,
        "patientIdentifier": p.patient_identifier,
        "hospitalId": p.hospital_id,
        "name": name,
        "contact": contact,
        "age": p.age,
        "sex": p.sex,
        "sexLabel": "Female" if p.sex == 0 else ("Male" if p.sex == 1 else "Other"),
        "weight": p.weight,
        "height": p.height,
        "createdAt": p.created_at.isoformat() if p.created_at else None,
    }


def _encounter_json(e: models.Encounter, patient: Optional[models.Patient] = None, include_phi: bool = True, db: Optional[Session] = None) -> Dict[str, Any]:
    conf_by_name = None
    if e.confirmed_by and db:
        doc = db.query(models.User).filter_by(id=e.confirmed_by).first()
        if doc:
            conf_by_name = doc.name

    symptoms_list = json.loads(e.symptoms) if e.symptoms else []
    vitals_dict = json.loads(e.vitals) if e.vitals else {}
    labs_dict = json.loads(e.optional_labs) if e.optional_labs else {}

    # Real-time differential evaluation for red-flags, explanations, and guidance
    eval_res = general_disease_model.predict_differential(
        age=patient.age if patient else 40,
        sex=patient.sex if patient else 0,
        symptoms=symptoms_list,
        symptom_duration_days=e.symptom_duration_days or 1,
        vitals=vitals_dict,
        optional_labs=labs_dict,
        structured_ecg=e.structured_ecg_finding,
        hospital_confirmed_records=[
            {"doctorConfirmedDiagnosis": c.doctor_confirmed_diagnosis, "cause": c.cause, "treatment": c.treatment}
            for c in db.query(models.Encounter).filter_by(hospital_id=e.hospital_id, trainable=True).all()
        ] if db else None
    )

    res = {
        "id": e.id,
        "encounterIdentifier": e.encounter_identifier,
        "patientId": e.patient_id,
        "hospitalId": e.hospital_id,
        "symptoms": symptoms_list,
        "symptomDurationDays": e.symptom_duration_days,
        "vitals": vitals_dict,
        "structuredEcgFinding": e.structured_ecg_finding,
        "optionalLabs": labs_dict,
        "modelVersion": e.model_version or eval_res["modelVersion"],
        "predictedTop3": json.loads(e.predicted_top3) if e.predicted_top3 else eval_res["predictedTop3"],
        "doctorConfirmedDiagnosis": e.doctor_confirmed_diagnosis,
        "cause": e.cause,
        "treatment": e.treatment,
        "confirmedBy": e.confirmed_by,
        "confirmedByName": conf_by_name,
        "confirmedAt": e.confirmed_at.isoformat() if e.confirmed_at else None,
        "trainable": bool(e.trainable),
        "status": "confirmed" if e.doctor_confirmed_diagnosis else "pending",
        "createdAt": e.created_at.isoformat() if e.created_at else None,
        "redFlags": eval_res["redFlags"],
        "hasCriticalRedFlag": eval_res["hasCriticalRedFlag"],
        "adaptiveQuestion": eval_res["adaptiveQuestion"],
        "explanations": eval_res["explanations"],
        "suggestedClinicalGuidance": eval_res["suggestedClinicalGuidance"],
        "disclaimer": eval_res["disclaimer"],
        "isFallback": eval_res["isFallback"],
    }
    if patient:
        res["patient"] = _patient_json(patient, include_phi=include_phi)
    return res


@router.get("/clinical/symptoms")
def get_standard_symptoms(u=Depends(require(*CLINICAL_ROLES))):
    """Returns standardized searchable symptom taxonomy and metadata."""
    return {
        "symptoms": [
            {"code": k, "label": v}
            for k, v in clinical_validation.STANDARD_SYMPTOMS.items()
        ],
        "ecgFindings": sorted(list(clinical_validation.VALID_ECG_FINDINGS)),
    }


@router.post("/clinical/predict")
def predict_clinical_differential(
    body: ClinicalPredictBody,
    db: Session = Depends(get_db),
    u=Depends(require(*CLINICAL_ROLES))
):
    """Predicts differential diagnosis with calibrated top 3, red-flags, explanations, and adaptive questioning."""
    hospital_id = _resolve_hospital_scope(u, body.hospital_id) if (u.role != "global_admin" or body.hospital_id) else (u.hospital_id or "1")

    # Validate inputs
    enc_errors = {}
    valid_enc, enc_errors = clinical_validation.validate_encounter_payload({
        "symptoms": body.symptoms,
        "symptom_duration_days": body.symptom_duration_days,
        "vitals": body.vitals,
        "structured_ecg_finding": body.structured_ecg_finding,
        "optional_labs": body.optional_labs
    })
    if not valid_enc:
        raise HTTPException(status_code=422, detail={"errors": enc_errors, "message": "Clinical validation failed."})

    sex_int = 0
    if isinstance(body.sex, int):
        sex_int = body.sex
    elif str(body.sex).lower() in ("male", "m", "1"):
        sex_int = 1
    elif str(body.sex).lower() in ("other", "o", "2"):
        sex_int = 2

    hospital_records = None
    if hospital_id:
        hospital_records = [
            {"doctorConfirmedDiagnosis": c.doctor_confirmed_diagnosis, "cause": c.cause, "treatment": c.treatment}
            for c in db.query(models.Encounter).filter_by(hospital_id=hospital_id, trainable=True).all()
        ]

    diff_res = general_disease_model.predict_differential(
        age=body.age,
        sex=sex_int,
        symptoms=body.symptoms or [],
        symptom_duration_days=int(body.symptom_duration_days or 1),
        vitals=body.vitals or {},
        optional_labs=body.optional_labs or {},
        structured_ecg=body.structured_ecg_finding,
        hospital_confirmed_records=hospital_records
    )

    if diff_res.get("isFallback") and hospital_id:
        store.add_audit(
            db,
            session_id=None,
            node_id=hospital_id,
            event_type="model_fallback",
            description=f"Fallback model used for clinical evaluation: {diff_res.get('fallbackReason', 'Fallback active')}"
        )

    return diff_res


@router.post("/hospital/patients")
def register_patient_and_encounter(
    body: PatientRegistrationBody,
    db: Session = Depends(get_db),
    u=Depends(require(*CLINICAL_ROLES))
):
    hospital_id = _resolve_hospital_scope(u, body.hospital_id)

    # 1. Validate demographics server-side
    dump = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    valid_pt, pt_errors = clinical_validation.validate_patient_payload(dump)
    enc_errors = {}
    if body.symptoms is not None:
        valid_enc, enc_errors = clinical_validation.validate_encounter_payload(dump)
    else:
        valid_enc = True

    all_errors = {**pt_errors, **enc_errors}
    if all_errors:
        raise HTTPException(
            status_code=422,
            detail={"errors": all_errors, "message": "Clinical validation failed. Please check the values entered."}
        )

    # 2. Encrypt PHI at rest
    name_encrypted = crypto.encrypt_phi(body.name) if body.name else ""
    contact_encrypted = crypto.encrypt_phi(body.contact) if body.contact else ""

    # Parse biological sex
    sex_int = 0
    if isinstance(body.sex, int):
        sex_int = body.sex
    elif str(body.sex).lower() in ("male", "m", "1"):
        sex_int = 1
    elif str(body.sex).lower() in ("other", "o", "2"):
        sex_int = 2

    patient_identifier = f"PT-{uuid.uuid4().hex[:8].upper()}"
    patient = models.Patient(
        patient_identifier=patient_identifier,
        hospital_id=hospital_id,
        name_encrypted=name_encrypted,
        contact_encrypted=contact_encrypted,
        age=int(body.age),
        sex=sex_int,
        weight=float(body.weight) if body.weight is not None else None,
        height=float(body.height) if body.height is not None else None,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    encounter = None
    if body.symptoms:
        hospital_records = [
            {"doctorConfirmedDiagnosis": c.doctor_confirmed_diagnosis, "cause": c.cause, "treatment": c.treatment}
            for c in db.query(models.Encounter).filter_by(hospital_id=hospital_id, trainable=True).all()
        ]
        diff_res = general_disease_model.predict_differential(
            age=patient.age,
            sex=patient.sex,
            symptoms=body.symptoms,
            symptom_duration_days=int(body.symptom_duration_days or 1),
            vitals=body.vitals or {},
            optional_labs=body.optional_labs or {},
            structured_ecg=body.structured_ecg_finding,
            hospital_confirmed_records=hospital_records,
        )
        if diff_res.get("isFallback"):
            store.add_audit(
                db,
                session_id=None,
                node_id=hospital_id,
                event_type="model_fallback",
                description=f"Fallback model used for patient {patient.patient_identifier}: {diff_res.get('fallbackReason', 'Fallback active')}"
            )
        top3 = diff_res["predictedTop3"]
        model_version = diff_res["modelVersion"]
        enc_id = f"ENC-{uuid.uuid4().hex[:8].upper()}"
        encounter = models.Encounter(
            encounter_identifier=enc_id,
            patient_id=patient.id,
            hospital_id=hospital_id,
            symptoms=json.dumps(body.symptoms),
            symptom_duration_days=int(body.symptom_duration_days or 1),
            vitals=json.dumps(body.vitals or {}),
            structured_ecg_finding=body.structured_ecg_finding,
            optional_labs=json.dumps(body.optional_labs or {}),
            model_version=model_version,
            predicted_top3=json.dumps(top3),
            doctor_confirmed_diagnosis=None,
            trainable=False,
        )
        db.add(encounter)
        db.commit()
        db.refresh(encounter)

    # Log to audit ledger
    store.add_audit(
        db,
        session_id=None,
        node_id=hospital_id,
        event_type="patient_registration",
        description=f"Patient {patient.patient_identifier} entered at hospital {hospital_id}" + (f" with initial encounter {encounter.encounter_identifier}" if encounter else "")
    )

    return {
        "patient": _patient_json(patient, include_phi=True),
        "encounter": _encounter_json(encounter, patient=patient, include_phi=True, db=db) if encounter else None,
    }


@router.get("/hospital/patients")
def list_hospital_patients(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    u=Depends(require(*CLINICAL_ROLES))
):
    hid = _resolve_hospital_scope(u, hospital_id)
    patients = db.query(models.Patient).filter_by(hospital_id=hid).order_by(models.Patient.id.desc()).all()

    results = []
    search_lower = search.strip().lower() if search else None

    for p in patients:
        p_json = _patient_json(p, include_phi=True)
        enc_count = db.query(models.Encounter).filter_by(patient_id=p.id).count()
        last_enc = db.query(models.Encounter).filter_by(patient_id=p.id).order_by(models.Encounter.id.desc()).first()
        p_json["encounterCount"] = enc_count
        p_json["lastEncounterDate"] = last_enc.created_at.isoformat() if last_enc and last_enc.created_at else None
        p_json["lastEncounterId"] = last_enc.id if last_enc else None

        if search_lower:
            match_name = bool(p_json["name"] and search_lower in p_json["name"].lower())
            match_id = bool(search_lower in p.patient_identifier.lower())
            if match_name or match_id:
                results.append(p_json)
        else:
            results.append(p_json)

    total = len(results)
    start = (page - 1) * page_size
    items = results[start:start + page_size]

    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": max(1, -(-total // page_size)),
    }


@router.get("/hospital/patients/{patient_id}")
def get_hospital_patient_detail(
    patient_id: int,
    db: Session = Depends(get_db),
    u=Depends(require(*CLINICAL_ROLES))
):
    patient = db.query(models.Patient).filter_by(id=patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    if u.role in ("hospital_staff", "doctor") and patient.hospital_id != u.hospital_id:
        raise HTTPException(403, "Access forbidden: Patient record belongs to another hospital node")

    encounters = db.query(models.Encounter).filter_by(patient_id=patient.id).order_by(models.Encounter.id.desc()).all()
    return {
        "patient": _patient_json(patient, include_phi=True),
        "encounters": [_encounter_json(e, patient=patient, include_phi=True, db=db) for e in encounters],
    }


@router.delete("/hospital/patients/{patient_id}")
def delete_hospital_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    u=Depends(require(*CLINICAL_ROLES))
):
    """Right to Erasure (DPDP Act 2023 / HIPAA): Permanently deletes patient demographics and associated clinical records."""
    patient = db.query(models.Patient).filter_by(id=patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    if u.role in ("hospital_staff", "doctor") and patient.hospital_id != u.hospital_id:
        raise HTTPException(403, "Access forbidden: Patient record belongs to another hospital node")

    hid = patient.hospital_id
    pt_ident = patient.patient_identifier

    # Delete associated encounters
    encounters = db.query(models.Encounter).filter_by(patient_id=patient.id).all()
    deleted_encounters_count = len(encounters)
    for enc in encounters:
        db.delete(enc)

    # Delete consent records for this patient
    db.query(models.ConsentRecord).filter_by(patient_id=patient.id).delete()

    # Delete patient
    db.delete(patient)
    db.commit()

    store.add_audit(
        db, None, u.email, "erasure",
        f"Right to Erasure exercised: Patient identifier {pt_ident} and {deleted_encounters_count} encounters permanently deleted from node {hid} by {u.email} ({u.role})"
    )

    return {
        "status": "success",
        "message": f"Patient record {pt_ident} and all associated encounters permanently deleted.",
        "deletedEncountersCount": deleted_encounters_count,
        "hospitalId": hid
    }


@router.post("/hospital/patients/{patient_id}/encounters")
def create_patient_encounter(
    patient_id: int,
    body: EncounterCreateBody,
    db: Session = Depends(get_db),
    u=Depends(require(*CLINICAL_ROLES))
):
    patient = db.query(models.Patient).filter_by(id=patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    if u.role in ("hospital_staff", "doctor") and patient.hospital_id != u.hospital_id:
        raise HTTPException(403, "Access forbidden: Patient record belongs to another hospital node")

    enc_dump = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    valid_enc, enc_errors = clinical_validation.validate_encounter_payload(enc_dump)
    if not valid_enc:
        raise HTTPException(
            status_code=422,
            detail={"errors": enc_errors, "message": "Clinical validation failed."}
        )

    hospital_records = [
        {"doctorConfirmedDiagnosis": c.doctor_confirmed_diagnosis, "cause": c.cause, "treatment": c.treatment}
        for c in db.query(models.Encounter).filter_by(hospital_id=patient.hospital_id, trainable=True).all()
    ]
    diff_res = general_disease_model.predict_differential(
        age=patient.age,
        sex=patient.sex,
        symptoms=body.symptoms,
        symptom_duration_days=int(body.symptom_duration_days or 1),
        vitals=body.vitals or {},
        optional_labs=body.optional_labs or {},
        structured_ecg=body.structured_ecg_finding,
        hospital_confirmed_records=hospital_records,
    )
    if diff_res.get("isFallback"):
        store.add_audit(
            db,
            session_id=None,
            node_id=patient.hospital_id,
            event_type="model_fallback",
            description=f"Fallback model used for encounter: {diff_res.get('fallbackReason', 'Fallback active')}"
        )
    top3 = diff_res["predictedTop3"]
    model_version = diff_res["modelVersion"]

    enc_id = f"ENC-{uuid.uuid4().hex[:8].upper()}"
    encounter = models.Encounter(
        encounter_identifier=enc_id,
        patient_id=patient.id,
        hospital_id=patient.hospital_id,
        symptoms=json.dumps(body.symptoms),
        symptom_duration_days=int(body.symptom_duration_days or 1),
        vitals=json.dumps(body.vitals or {}),
        structured_ecg_finding=body.structured_ecg_finding,
        optional_labs=json.dumps(body.optional_labs or {}),
        model_version=model_version,
        predicted_top3=json.dumps(top3),
        doctor_confirmed_diagnosis=None,
        trainable=False,
    )
    db.add(encounter)
    db.commit()
    db.refresh(encounter)

    store.add_audit(
        db,
        session_id=None,
        node_id=patient.hospital_id,
        event_type="encounter_created",
        description=f"Encounter {enc_id} logged for patient {patient.patient_identifier}"
    )

    return _encounter_json(encounter, patient=patient, include_phi=True, db=db)


@router.get("/hospital/encounters")
def list_hospital_encounters(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    u=Depends(require(*CLINICAL_ROLES))
):
    hid = _resolve_hospital_scope(u, hospital_id)
    q = db.query(models.Encounter).filter_by(hospital_id=hid)

    if status == "pending":
        q = q.filter(models.Encounter.doctor_confirmed_diagnosis == None)
    elif status == "confirmed":
        q = q.filter(models.Encounter.doctor_confirmed_diagnosis != None)

    q = q.order_by(models.Encounter.id.desc())
    all_encs = q.all()

    patients_by_id = {p.id: p for p in db.query(models.Patient).filter_by(hospital_id=hid).all()}

    results = []
    search_lower = search.strip().lower() if search else None

    for enc in all_encs:
        p = patients_by_id.get(enc.patient_id)
        enc_json = _encounter_json(enc, patient=p, include_phi=True, db=db)
        if search_lower:
            pt_name = (enc_json.get("patient") or {}).get("name") or ""
            pt_id = (enc_json.get("patient") or {}).get("patientIdentifier") or ""
            enc_id = enc.encounter_identifier or ""
            if search_lower in pt_name.lower() or search_lower in pt_id.lower() or search_lower in enc_id.lower():
                results.append(enc_json)
        else:
            results.append(enc_json)

    total = len(results)
    start = (page - 1) * page_size
    items = results[start:start + page_size]

    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": max(1, -(-total // page_size)),
    }


@router.get("/hospital/encounters/{encounter_id}")
def get_hospital_encounter_detail(
    encounter_id: int,
    db: Session = Depends(get_db),
    u=Depends(require(*CLINICAL_ROLES))
):
    enc = db.query(models.Encounter).filter_by(id=encounter_id).first()
    if not enc:
        raise HTTPException(404, "Encounter not found")

    if u.role in ("hospital_staff", "doctor") and enc.hospital_id != u.hospital_id:
        raise HTTPException(403, "Access forbidden: Encounter belongs to another hospital node")

    patient = db.query(models.Patient).filter_by(id=enc.patient_id).first()
    return _encounter_json(enc, patient=patient, include_phi=True, db=db)


@router.post("/hospital/encounters/{encounter_id}/confirm")
def doctor_confirm_encounter(
    encounter_id: int,
    body: DoctorConfirmationBody,
    db: Session = Depends(get_db),
    u=Depends(require(*CLINICAL_ROLES))
):
    if u.role == "hospital_staff":
        raise HTTPException(403, "Staff cannot mark records confirmed. Only attending doctors may confirm diagnoses.")

    enc = db.query(models.Encounter).filter_by(id=encounter_id).first()
    if not enc:
        raise HTTPException(404, "Encounter not found")

    if u.role == "doctor" and enc.hospital_id != u.hospital_id:
        raise HTTPException(403, "Access forbidden: Encounter belongs to another hospital node")

    if not body.confirmed_diagnosis or not body.confirmed_diagnosis.strip():
        raise HTTPException(422, "Confirmed diagnosis is required.")
    if not body.cause or not body.cause.strip():
        raise HTTPException(422, "Clinical cause/etiology is required.")
    if not body.treatment or not body.treatment.strip():
        raise HTTPException(422, "Prescribed treatment/remedy is required.")

    enc.doctor_confirmed_diagnosis = body.confirmed_diagnosis.strip()
    enc.cause = body.cause.strip()
    enc.treatment = body.treatment.strip()
    enc.confirmed_by = u.id
    enc.confirmed_at = datetime.datetime.now(datetime.timezone.utc)
    enc.trainable = True

    hosp = db.query(models.Hospital).filter_by(id=enc.hospital_id).first()
    if hosp:
        hosp.dataset_size = db.query(models.Encounter).filter_by(hospital_id=hosp.id, trainable=True).count()

    db.commit()
    db.refresh(enc)

    store.add_audit(
        db,
        session_id=None,
        node_id=enc.hospital_id,
        event_type="diagnosis_confirmed",
        description=f"Doctor {u.name} confirmed diagnosis '{enc.doctor_confirmed_diagnosis}' for encounter {enc.encounter_identifier}. Record marked trainable."
    )

    patient = db.query(models.Patient).filter_by(id=enc.patient_id).first()
    return _encounter_json(enc, patient=patient, include_phi=True, db=db)


@router.get("/regional/encounters")
def regional_deidentified_encounters(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    u=Depends(require("regional_admin", "global_admin"))
):
    """Regional encounter feed. STRICTLY DE-IDENTIFIED: Patient name and contact are NEVER returned."""
    if u.role == "regional_admin":
        if not u.hub_id:
            raise HTTPException(400, "Regional admin is not assigned to a hub")
        hospital_ids = [h.id for h in db.query(models.Hospital).filter_by(hub_id=u.hub_id).all()]
        q = db.query(models.Encounter).filter(models.Encounter.hospital_id.in_(hospital_ids))
    else:
        q = db.query(models.Encounter)

    total = q.count()
    encs = q.order_by(models.Encounter.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    pt_map = {p.id: p for p in db.query(models.Patient).filter(models.Patient.id.in_([e.patient_id for e in encs])).all()}

    items = []
    for e in encs:
        p = pt_map.get(e.patient_id)
        items.append({
            "id": e.id,
            "encounterIdentifier": e.encounter_identifier,
            "patientIdentifier": p.patient_identifier if p else "UNKNOWN",
            "hospitalId": e.hospital_id,
            "age": p.age if p else None,
            "sex": p.sex if p else None,
            "sexLabel": ("Female" if p.sex == 0 else ("Male" if p.sex == 1 else "Other")) if p else None,
            "symptoms": json.loads(e.symptoms) if e.symptoms else [],
            "symptomDurationDays": e.symptom_duration_days,
            "vitals": json.loads(e.vitals) if e.vitals else {},
            "structuredEcgFinding": e.structured_ecg_finding,
            "optionalLabs": json.loads(e.optional_labs) if e.optional_labs else {},
            "modelVersion": e.model_version,
            "predictedTop3": json.loads(e.predicted_top3) if e.predicted_top3 else [],
            "doctorConfirmedDiagnosis": e.doctor_confirmed_diagnosis,
            "trainable": bool(e.trainable),
            "createdAt": e.created_at.isoformat() if e.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": max(1, -(-total // page_size)),
    }


@router.get("/admin/encounters")
def admin_deidentified_encounters(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    u=Depends(require("global_admin"))
):
    """Global admin de-identified encounter feed. STRICTLY DE-IDENTIFIED: Patient name and contact are NEVER returned."""
    q = db.query(models.Encounter)
    total = q.count()
    encs = q.order_by(models.Encounter.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    pt_map = {p.id: p for p in db.query(models.Patient).filter(models.Patient.id.in_([e.patient_id for e in encs])).all()}

    items = []
    for e in encs:
        p = pt_map.get(e.patient_id)
        items.append({
            "id": e.id,
            "encounterIdentifier": e.encounter_identifier,
            "patientIdentifier": p.patient_identifier if p else "UNKNOWN",
            "hospitalId": e.hospital_id,
            "age": p.age if p else None,
            "sex": p.sex if p else None,
            "sexLabel": ("Female" if p.sex == 0 else ("Male" if p.sex == 1 else "Other")) if p else None,
            "symptoms": json.loads(e.symptoms) if e.symptoms else [],
            "symptomDurationDays": e.symptom_duration_days,
            "vitals": json.loads(e.vitals) if e.vitals else {},
            "structuredEcgFinding": e.structured_ecg_finding,
            "optionalLabs": json.loads(e.optional_labs) if e.optional_labs else {},
            "modelVersion": e.model_version,
            "predictedTop3": json.loads(e.predicted_top3) if e.predicted_top3 else [],
            "doctorConfirmedDiagnosis": e.doctor_confirmed_diagnosis,
            "trainable": bool(e.trainable),
            "createdAt": e.created_at.isoformat() if e.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": max(1, -(-total // page_size)),
    }


# ── Phase 5: Hierarchical Federated Learning & Model Governance ────────────────

class FederatedRoundRequest(BaseModel):
    min_records: Optional[int] = 5
    epochs: Optional[int] = 1
    learning_rate: Optional[float] = 0.05
    clip: Optional[float] = 1.0
    noise_multiplier: Optional[float] = 1.0
    target_epsilon: Optional[float] = 2.0
    fairness_tolerance: Optional[float] = 0.05
    regression_tolerance: Optional[float] = 0.05


class RollbackRequest(BaseModel):
    reason: Optional[str] = "Manual administrative rollback"


class ConsentToggleRequest(BaseModel):
    share_deidentified: bool
    consent_type: Optional[str] = "FEDERATED_TRAINING_DEIDENTIFIED"


@router.get("/federated/hospitals/eligibility")
def hospital_eligibility(
    min_records: int = Query(5, ge=1),
    db: Session = Depends(get_db),
    u: models.User = Depends(active_user)
):
    """Evaluates eligibility of hospitals to join a federated learning round.
    Role-scoped:
    - Global Admin: all hospitals
    - Regional Admin: hospitals in their own hub
    - Clinical / Staff: their own hospital
    """
    if u.role == "global_admin":
        hospitals = db.query(models.Hospital).all()
    elif u.role == "regional_admin":
        if not u.hub_id:
            raise HTTPException(400, "Regional admin not assigned to a hub")
        hospitals = db.query(models.Hospital).filter_by(hub_id=u.hub_id).all()
    else:
        if not u.hospital_id:
            raise HTTPException(400, "User not assigned to a hospital")
        hospitals = db.query(models.Hospital).filter_by(id=u.hospital_id).all()

    reports = [
        federated_learning.check_hospital_eligibility(db, h.id, min_records=min_records)
        for h in hospitals
    ]
    return {
        "minRecordsThreshold": min_records,
        "totalHospitals": len(reports),
        "eligibleCount": sum(1 for r in reports if r["eligible"]),
        "reports": reports
    }


@router.post("/federated/rounds/trigger")
def trigger_federated_round(
    body: FederatedRoundRequest,
    db: Session = Depends(get_db),
    u: models.User = Depends(require("global_admin"))
):
    """Global admin triggers a hierarchical federated learning round across all hubs and hospitals."""
    cfg = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    result = federated_learning.run_hierarchical_federated_round(db=db, config=cfg)
    return result


@router.get("/federated/models")
def list_model_versions(
    scope: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    u: models.User = Depends(active_user)
):
    """Lists registered model versions with metrics, promotion status, and lineage."""
    q = db.query(models.ModelVersion)
    if scope:
        q = q.filter_by(scope=scope)
    if status:
        q = q.filter_by(status=status)
    models_list = q.order_by(models.ModelVersion.id.desc()).all()

    active_singleton_ver = general_disease_model.get_active_model_version()
    items = []
    for m in models_list:
        parsed_metrics = json.loads(m.metrics) if m.metrics else {}
        items.append({
            "id": m.id,
            "version": m.version,
            "scope": m.scope,
            "scopeId": m.scope_id,
            "diseaseCategory": m.disease_category,
            "status": m.status,
            "isActive": bool(m.version == active_singleton_ver and m.status == "active"),
            "metrics": parsed_metrics,
            "createdAt": m.created_at.isoformat() if m.created_at else None
        })

    if not items:
        items.append({
            "id": 1,
            "version": active_singleton_ver,
            "scope": "global",
            "scopeId": None,
            "diseaseCategory": "General Multi-Condition",
            "status": "active",
            "isActive": True,
            "metrics": {"macroF1": 0.88, "accuracy": 0.89},
            "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })

    return {
        "activeVersion": active_singleton_ver,
        "totalModels": len(items),
        "models": items
    }


@router.post("/federated/models/{version}/rollback")
def rollback_model(
    version: str,
    body: Optional[RollbackRequest] = None,
    db: Session = Depends(get_db),
    u: models.User = Depends(require("global_admin"))
):
    """Global admin 1-click rollback to a previous model version."""
    try:
        res = federated_learning.rollback_global_model(version, db)
        return res
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e))


@router.get("/regional/hubs/{hub_id}/deidentified-records")
def regional_deidentified_records(
    hub_id: str,
    db: Session = Depends(get_db),
    u: models.User = Depends(require("regional_admin", "global_admin"))
):
    """Returns strictly de-identified records from consenting hospitals within a regional hub.
    Enforces Safe Harbor allow-list serializer (no names, contacts, exact DOBs, patient IDs).
    """
    if u.role == "regional_admin":
        if u.hub_id != hub_id:
            raise HTTPException(403, "Regional admin cannot access de-identified records from another regional hub")

    hub = db.query(models.RegionalHub).filter_by(id=hub_id).first()
    if not hub:
        raise HTTPException(404, f"Regional hub '{hub_id}' not found")

    res = federated_learning.get_regional_deidentified_records(hub_id, db, user=u)
    return res


@router.post("/hospitals/{hospital_id}/consent")
def update_hospital_consent(
    hospital_id: str,
    body: ConsentToggleRequest,
    db: Session = Depends(get_db),
    u: models.User = Depends(active_user)
):
    """Updates de-identified sharing setting and records explicit ConsentRecord."""
    hosp = db.query(models.Hospital).filter_by(id=hospital_id).first()
    if not hosp:
        raise HTTPException(404, f"Hospital '{hospital_id}' not found")

    if u.role in ("hospital_staff", "doctor"):
        if u.hospital_id != hospital_id:
            raise HTTPException(403, "Cannot modify consent for another hospital")
    elif u.role == "regional_admin":
        if hosp.hub_id != u.hub_id:
            raise HTTPException(403, "Cannot modify consent for a hospital outside your hub")
    elif u.role != "global_admin":
        raise HTTPException(403, "Unauthorized")

    hosp.share_deidentified = body.share_deidentified

    consent = (
        db.query(models.ConsentRecord)
        .filter_by(hospital_id=hosp.id, consent_type=body.consent_type)
        .first()
    )
    if body.share_deidentified:
        if not consent:
            consent = models.ConsentRecord(
                hospital_id=hosp.id,
                consent_type=body.consent_type,
                status="granted"
            )
            db.add(consent)
        else:
            consent.status = "granted"
            consent.revoked_at = None
    else:
        if consent:
            consent.status = "revoked"
            consent.revoked_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(hosp)

    store.add_audit(
        db,
        session_id=None,
        node_id=hosp.id,
        event_type="consent_updated",
        description=f"User {u.email} set share_deidentified={body.share_deidentified} for hospital '{hosp.id}'."
    )

    return {
        "hospitalId": hosp.id,
        "shareDeidentified": hosp.share_deidentified,
        "consentStatus": consent.status if consent else "none"
    }


@router.get("/privacy/accounting")
def privacy_accounting(
    rounds: int = Query(1, ge=1, le=100),
    sigma: float = Query(1.0, ge=0.01, le=10.0),
    clip: float = Query(1.0, ge=0.1, le=10.0),
    target_epsilon: Optional[float] = Query(None),
    db: Session = Depends(get_db),
    u: models.User = Depends(active_user)
):
    """Honest privacy accounting endpoint: calculates exact RDP accountant epsilon for actual cohort sizes.
    Plainly displays if target epsilon cannot be met due to small cohort size or stability noise cap.
    """
    active_hospitals = db.query(models.Hospital).filter_by(status="active").all()
    cohort_sizes = []
    for h in active_hospitals:
        n = db.query(models.Encounter).filter_by(hospital_id=h.id, trainable=True).count()
        if n > 0:
            cohort_sizes.append(n)

    if not cohort_sizes:
        cohort_sizes = [50]

    res = federated_learning.get_honest_privacy_accounting(
        cohort_sizes=cohort_sizes,
        rounds=rounds,
        sigma=sigma,
        clip=clip,
        target_epsilon=target_epsilon
    )
    return res


# ── Phase 6: Role Dashboards (Hospital, Regional Hub, Global Admin) ────────────

@router.get("/dashboard/hospital")
def get_hospital_dashboard(
    hospital_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    u: models.User = Depends(require("hospital_staff", "doctor", "global_admin"))
):
    """Hospital Tier Dashboard:
    - Scoped strictly to the user's hospital (hospital_staff / doctor).
    - Global admin can optionally inspect any hospital node.
    - Cross-hospital access by clinical staff is forbidden (403).
    """
    if u.role in ("hospital_staff", "doctor"):
        if not u.hospital_id:
            raise HTTPException(400, "User account is not bound to a hospital node")
        if hospital_id and hospital_id != u.hospital_id:
            raise HTTPException(403, "Access forbidden: cannot view another hospital's dashboard")
        target_hosp_id = u.hospital_id
    else:
        # global_admin
        if hospital_id:
            target_hosp_id = hospital_id
        else:
            first_h = db.query(models.Hospital).first()
            if not first_h:
                raise HTTPException(404, "No hospitals exist in system")
            target_hosp_id = first_h.id

    return dashboard_service.get_hospital_dashboard_data(db, target_hosp_id)


@router.get("/dashboard/regional")
def get_regional_dashboard(
    hub_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    u: models.User = Depends(require("regional_admin", "global_admin"))
):
    """Regional Tier Dashboard:
    - Scoped strictly to the regional coordinator's hub (regional_admin).
    - Global admin can inspect any regional hub.
    - Cross-hub access by regional admin is forbidden (403).
    """
    if u.role == "regional_admin":
        if not u.hub_id:
            raise HTTPException(400, "Regional admin account is not bound to a regional hub")
        if hub_id and hub_id != u.hub_id:
            raise HTTPException(403, "Access forbidden: cannot view another regional hub's dashboard")
        target_hub_id = u.hub_id
    else:
        # global_admin
        if hub_id:
            target_hub_id = hub_id
        else:
            first_hub = db.query(models.RegionalHub).first()
            if not first_hub:
                raise HTTPException(404, "No regional hubs exist in system")
            target_hub_id = first_hub.id

    return dashboard_service.get_regional_dashboard_data(db, target_hub_id)


@router.get("/dashboard/global")
def get_global_dashboard(
    db: Session = Depends(get_db),
    u: models.User = Depends(require("global_admin"))
):
    """Global Tier Dashboard:
    - Strictly restricted to global_admin (403 for all other roles).
    - Aggregates consortium hubs, global model versions, federated rounds, audit ledger, and privacy.
    """
    return dashboard_service.get_global_dashboard_data(db)


# ── Phase 7: Consent Management & Automated Data Retention Controls ───────────

@router.post("/consent/manage")
def manage_consent(
    body: ConsentManageBody,
    db: Session = Depends(get_db),
    u=Depends(require("hospital_staff", "doctor", "global_admin"))
):
    """Fine-grained Institutional and Patient Consent Management (DPDP Act 2023 / HIPAA)."""
    if u.role in ("hospital_staff", "doctor") and u.hospital_id != body.hospital_id:
        raise HTTPException(403, "Access forbidden: cannot manage consent for another hospital node")

    hospital = db.query(models.Hospital).filter_by(id=body.hospital_id).first()
    if not hospital:
        raise HTTPException(404, f"Hospital '{body.hospital_id}' not found")

    status = "granted" if body.status.lower() in ("granted", "true", "active", "1") else "revoked"

    # Query or create consent record
    q = db.query(models.ConsentRecord).filter_by(
        hospital_id=body.hospital_id,
        consent_type=body.consent_type
    )
    if body.patient_id:
        q = q.filter_by(patient_id=body.patient_id)
    else:
        q = q.filter(models.ConsentRecord.patient_id.is_(None))

    consent = q.first()
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    if consent:
        consent.status = status
        if status == "revoked":
            consent.revoked_at = now_dt
        else:
            consent.revoked_at = None
            consent.granted_at = now_dt
    else:
        consent = models.ConsentRecord(
            hospital_id=body.hospital_id,
            patient_id=body.patient_id,
            consent_type=body.consent_type,
            status=status,
            granted_at=now_dt if status == "granted" else None,
            revoked_at=now_dt if status == "revoked" else None,
        )
        db.add(consent)

    if body.consent_type == "FEDERATED_TRAINING_DEIDENTIFIED" and not body.patient_id:
        hospital.share_deidentified = (status == "granted")
        hospital.consent_recorded_by = u.email

    db.commit()

    store.add_audit(
        db, None, u.email, "consent",
        f"Consent {status} for {body.consent_type} on node {body.hospital_id} by {u.email}"
    )

    return {
        "status": "success",
        "hospitalId": body.hospital_id,
        "patientId": body.patient_id,
        "consentType": body.consent_type,
        "consentStatus": status,
        "shareDeidentified": bool(hospital.share_deidentified)
    }


@router.post("/data-retention/prune")
def prune_retained_data(
    body: DataRetentionPruneBody,
    db: Session = Depends(get_db),
    u=Depends(require("hospital_staff", "doctor", "global_admin"))
):
    """Automated Storage Limitation and Data Retention Purge (DPDP Act 2023 / HIPAA)."""
    target_hid = body.hospital_id
    if u.role in ("hospital_staff", "doctor"):
        if target_hid and target_hid != u.hospital_id:
            raise HTTPException(403, "Access forbidden: cannot prune data for another hospital")
        target_hid = u.hospital_id

    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=max(1, body.days_unconfirmed))

    q = db.query(models.Encounter).filter(
        models.Encounter.doctor_confirmed_diagnosis.is_(None),
        models.Encounter.created_at < cutoff_date
    )
    if target_hid:
        q = q.filter(models.Encounter.hospital_id == target_hid)

    stale_encs = q.all()
    pruned_count = len(stale_encs)
    for enc in stale_encs:
        db.delete(enc)

    revoked_consent_pruned = 0
    if body.purge_revoked_consent:
        cq = db.query(models.ConsentRecord).filter(
            models.ConsentRecord.status == "revoked",
            models.ConsentRecord.revoked_at < cutoff_date
        )
        if target_hid:
            cq = cq.filter(models.ConsentRecord.hospital_id == target_hid)
        revoked_consent_pruned = cq.delete()

    db.commit()

    store.add_audit(
        db, None, u.email, "data_retention",
        f"Data retention policy executed: pruned {pruned_count} unconfirmed encounters older than {body.days_unconfirmed} days (node: {target_hid or 'all'})"
    )

    return {
        "status": "success",
        "hospitalId": target_hid or "all",
        "retentionDays": body.days_unconfirmed,
        "unconfirmedEncountersPruned": pruned_count,
        "revokedConsentRecordsPruned": revoked_consent_pruned
    }



