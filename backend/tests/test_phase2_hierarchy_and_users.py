"""Phase 2 tests: Hierarchy, role boundaries, user lifecycle, token revocation,
first-login password reset, and hash-chained audit logging.
"""
import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SECRET_KEY"] = "phase2-high-entropy-secret-key-0123456789abcdef"
os.environ["ENVIRONMENT"] = "development"

from main import app
from db.database import Base, engine, SessionLocal
from db import models
from db.migrations.v2_general_disease_migration import migrate_up
from services import auth, store

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)
    migrate_up(engine)
    db = SessionLocal()
    try:
        # Clean up any leftover test data from previous runs
        test_emails = [
            "temp_admin_p2@trustfed.ai", "admin_alpha@trustfed.ai", "admin_beta@trustfed.ai",
            "dr_gamma@trustfed.ai", "staff_delta@trustfed.ai", "doc_delta2@trustfed.ai"
        ]
        db.query(models.RefreshToken).filter(models.RefreshToken.user_id.in_(
            db.query(models.User.id).filter(models.User.email.in_(test_emails))
        )).delete(synchronize_session=False)
        db.query(models.User).filter(models.User.email.in_(test_emails)).delete(synchronize_session=False)
        db.query(models.Hospital).filter(models.Hospital.id.in_(["hosp-alpha-1", "hosp-beta-1", "hosp-gamma-1", "hosp-delta-1"])).delete(synchronize_session=False)
        db.query(models.HospitalNode).filter(models.HospitalNode.id.in_(["hosp-alpha-1", "hosp-beta-1", "hosp-gamma-1", "hosp-delta-1"])).delete(synchronize_session=False)
        db.query(models.RegionalHub).filter(models.RegionalHub.id.in_(["hub-reset-test", "hub-alpha", "hub-beta", "hub-gamma", "hub-delta"])).delete(synchronize_session=False)
        db.commit()

        # Global Admin for tests
        adm = db.query(models.User).filter_by(email="global_admin_p2@trustfed.ai").first()
        if not adm:
            db.add(models.User(
                email="global_admin_p2@trustfed.ai",
                name="Global Admin P2",
                role="global_admin",
                must_reset_password=False,
                status="active",
                password_hash=auth.hash_password("AdminPass123!Secure")
            ))
            db.commit()
    finally:
        db.close()


import uuid

def _login(email, password):
    ip = f"10.99.{hash(email) % 250}.{uuid.uuid4().hex[:2]}"
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password}, headers={"X-Forwarded-For": ip})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    data = res.json()
    return data["token"], data["csrf_token"], res.cookies.get("tf_refresh_token"), data["user"]


def test_first_login_password_reset_enforced():
    """Prove that newly issued users are blocked from protected endpoints until password reset."""
    admin_token, _, _, _ = _login("global_admin_p2@trustfed.ai", "AdminPass123!Secure")
    headers_adm = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create a hub and issue a new admin
    client.post("/api/v1/admin/hubs", json={"id": "hub-reset-test", "name": "Reset Hub", "region": "North"}, headers=headers_adm)
    res_issue = client.post(
        "/api/v1/admin/hubs/hub-reset-test/admins",
        json={"name": "Temp Admin", "email": "temp_admin_p2@trustfed.ai"},
        headers=headers_adm
    )
    assert res_issue.status_code == 200
    temp_pw = res_issue.json()["temp_password"]

    # 2. Login with temporary password
    token, csrf, refresh_cookie, user = _login("temp_admin_p2@trustfed.ai", temp_pw)
    assert user["mustResetPassword"] is True
    headers_user = {"Authorization": f"Bearer {token}"}

    # 3. Accessing normal endpoints must return 403
    res_blocked = client.get("/api/v1/regional/hospitals", headers=headers_user)
    assert res_blocked.status_code == 403
    assert "Password reset required" in res_blocked.json()["detail"]

    # 4. Password policy checks on reset
    # Weak password
    res_weak = client.post("/api/v1/auth/reset-password", json={"current_password": temp_pw, "new_password": "weak"}, headers=headers_user)
    assert res_weak.status_code == 422

    # Same password
    res_same = client.post("/api/v1/auth/reset-password", json={"current_password": temp_pw, "new_password": temp_pw}, headers=headers_user)
    assert res_same.status_code == 400

    # Wrong current password
    res_wrong = client.post("/api/v1/auth/reset-password", json={"current_password": "WrongPassword1!", "new_password": "NewStrongPass123!"}, headers=headers_user)
    assert res_wrong.status_code == 400

    # Valid reset
    new_pw = "NewStrongPass123!Secure"
    res_ok = client.post("/api/v1/auth/reset-password", json={"current_password": temp_pw, "new_password": new_pw}, headers=headers_user)
    assert res_ok.status_code == 200
    assert res_ok.json()["user"]["mustResetPassword"] is False

    # 5. Protected endpoints now succeed
    res_allowed = client.get("/api/v1/regional/hospitals", headers=headers_user)
    assert res_allowed.status_code == 200


def test_regional_admin_cannot_touch_other_hubs_hospitals():
    """Prove that a regional admin is strictly isolated to their own hub's hospitals."""
    admin_token, _, _, _ = _login("global_admin_p2@trustfed.ai", "AdminPass123!Secure")
    headers_adm = {"Authorization": f"Bearer {admin_token}"}

    # Create Hub A and Hub B
    client.post("/api/v1/admin/hubs", json={"id": "hub-alpha", "name": "Hub Alpha", "region": "Zone-A"}, headers=headers_adm)
    client.post("/api/v1/admin/hubs", json={"id": "hub-beta", "name": "Hub Beta", "region": "Zone-B"}, headers=headers_adm)

    # Issue Regional Admin A and B
    r_a = client.post("/api/v1/admin/hubs/hub-alpha/admins", json={"name": "Admin Alpha", "email": "admin_alpha@trustfed.ai"}, headers=headers_adm).json()
    r_b = client.post("/api/v1/admin/hubs/hub-beta/admins", json={"name": "Admin Beta", "email": "admin_beta@trustfed.ai"}, headers=headers_adm).json()

    # Reset passwords for both admins
    tok_a, _, _, _ = _login("admin_alpha@trustfed.ai", r_a["temp_password"])
    client.post("/api/v1/auth/reset-password", json={"current_password": r_a["temp_password"], "new_password": "AlphaPass123!Secure"}, headers={"Authorization": f"Bearer {tok_a}"})
    tok_a, _, _, _ = _login("admin_alpha@trustfed.ai", "AlphaPass123!Secure")
    headers_a = {"Authorization": f"Bearer {tok_a}"}

    tok_b, _, _, _ = _login("admin_beta@trustfed.ai", r_b["temp_password"])
    client.post("/api/v1/auth/reset-password", json={"current_password": r_b["temp_password"], "new_password": "BetaPass123!Secure"}, headers={"Authorization": f"Bearer {tok_b}"})
    tok_b, _, _, _ = _login("admin_beta@trustfed.ai", "BetaPass123!Secure")
    headers_b = {"Authorization": f"Bearer {tok_b}"}

    # Admin A creates hospital in Hub Alpha -> Success
    res_create_a = client.post("/api/v1/regional/hospitals", json={"id": "hosp-alpha-1", "name": "Alpha General Hospital"}, headers=headers_a)
    assert res_create_a.status_code == 200

    # Admin A attempts to create hospital in Hub Beta -> 403
    res_cross_create = client.post("/api/v1/regional/hospitals", json={"id": "hosp-beta-illegal", "name": "Illegal Hospital", "hub_id": "hub-beta"}, headers=headers_a)
    assert res_cross_create.status_code == 403

    # Admin B creates hospital in Hub Beta -> Success
    res_create_b = client.post("/api/v1/regional/hospitals", json={"id": "hosp-beta-1", "name": "Beta Central Hospital"}, headers=headers_b)
    assert res_create_b.status_code == 200

    # Admin A attempts to update, suspend, delete, or issue user for Beta's hospital -> 403 Forbidden
    assert client.put("/api/v1/regional/hospitals/hosp-beta-1", json={"name": "Hacked Name"}, headers=headers_a).status_code == 403
    assert client.post("/api/v1/regional/hospitals/hosp-beta-1/suspend", headers=headers_a).status_code == 403
    assert client.delete("/api/v1/regional/hospitals/hosp-beta-1", headers=headers_a).status_code == 403
    assert client.post("/api/v1/regional/hospitals/hosp-beta-1/users", json={"name": "Spy", "email": "spy@beta.ai", "role": "doctor"}, headers=headers_a).status_code == 403

    # Admin A lists hospitals -> Only sees hosp-alpha-1, not hosp-beta-1
    res_list = client.get("/api/v1/regional/hospitals", headers=headers_a)
    assert res_list.status_code == 200
    hosp_ids = [h["id"] for h in res_list.json()]
    assert "hosp-alpha-1" in hosp_ids
    assert "hosp-beta-1" not in hosp_ids


def test_hospital_user_cannot_call_hub_or_admin_endpoints():
    """Prove that hospital staff and doctors cannot access regional or global admin endpoints."""
    admin_token, _, _, _ = _login("global_admin_p2@trustfed.ai", "AdminPass123!Secure")
    headers_adm = {"Authorization": f"Bearer {admin_token}"}

    client.post("/api/v1/admin/hubs", json={"id": "hub-gamma", "name": "Hub Gamma", "region": "South"}, headers=headers_adm)
    client.post("/api/v1/regional/hospitals", json={"id": "hosp-gamma-1", "name": "Gamma Clinic", "hub_id": "hub-gamma"}, headers=headers_adm)

    # Issue Doctor credentials
    r_doc = client.post(
        "/api/v1/regional/hospitals/hosp-gamma-1/users",
        json={"name": "Dr. Gamma", "email": "dr_gamma@trustfed.ai", "role": "doctor"},
        headers=headers_adm
    ).json()

    tok_doc, _, _, _ = _login("dr_gamma@trustfed.ai", r_doc["temp_password"])
    client.post("/api/v1/auth/reset-password", json={"current_password": r_doc["temp_password"], "new_password": "DoctorPass123!Secure"}, headers={"Authorization": f"Bearer {tok_doc}"})
    tok_doc, _, _, _ = _login("dr_gamma@trustfed.ai", "DoctorPass123!Secure")
    headers_doc = {"Authorization": f"Bearer {tok_doc}"}

    # Doctor calling admin or regional management routes must get 403
    assert client.get("/api/v1/admin/hubs", headers=headers_doc).status_code == 403
    assert client.post("/api/v1/admin/hubs", json={"id": "h", "name": "n", "region": "r"}, headers=headers_doc).status_code == 403
    assert client.get("/api/v1/regional/hospitals", headers=headers_doc).status_code == 403
    assert client.post("/api/v1/regional/hospitals", json={"id": "h", "name": "n"}, headers=headers_doc).status_code == 403
    assert client.post("/api/v1/regional/hospitals/hosp-gamma-1/suspend", headers=headers_doc).status_code == 403


def test_removed_or_suspended_users_and_hospitals_tokens_revoked():
    """Prove that suspending/deleting users or hospitals immediately revokes tokens."""
    admin_token, _, _, _ = _login("global_admin_p2@trustfed.ai", "AdminPass123!Secure")
    headers_adm = {"Authorization": f"Bearer {admin_token}"}

    client.post("/api/v1/admin/hubs", json={"id": "hub-delta", "name": "Hub Delta", "region": "West"}, headers=headers_adm)
    client.post("/api/v1/regional/hospitals", json={"id": "hosp-delta-1", "name": "Delta Hospital", "hub_id": "hub-delta"}, headers=headers_adm)

    # 1. Test individual user suspension & revocation
    r_staff = client.post(
        "/api/v1/regional/hospitals/hosp-delta-1/users",
        json={"name": "Staff Delta", "email": "staff_delta@trustfed.ai", "role": "hospital_staff"},
        headers=headers_adm
    ).json()
    user_id = r_staff["user"]["id"]

    tok, csrf, cookie, _ = _login("staff_delta@trustfed.ai", r_staff["temp_password"])
    client.post("/api/v1/auth/reset-password", json={"current_password": r_staff["temp_password"], "new_password": "StaffPass123!Secure"}, headers={"Authorization": f"Bearer {tok}"})
    tok, csrf, cookie, _ = _login("staff_delta@trustfed.ai", "StaffPass123!Secure")
    headers_staff = {"Authorization": f"Bearer {tok}"}

    # Verify active access
    assert client.get("/api/v1/auth/me", headers=headers_staff).status_code == 200

    # Suspend user
    res_susp = client.post(f"/api/v1/regional/users/{user_id}/suspend", headers=headers_adm)
    assert res_susp.status_code == 200

    # Immediate access token call fails 401
    assert client.get("/api/v1/auth/me", headers=headers_staff).status_code == 401
    # Refresh token call fails 401
    assert client.post("/api/v1/auth/refresh", cookies={"tf_refresh_token": cookie}, headers={"X-CSRF-Token": csrf}).status_code == 401

    # 2. Test hospital suspension revokes all dependent users and sets node offline
    # Create doctor in same hospital
    r_doc2 = client.post(
        "/api/v1/regional/hospitals/hosp-delta-1/users",
        json={"name": "Doctor Delta 2", "email": "doc_delta2@trustfed.ai", "role": "doctor"},
        headers=headers_adm
    ).json()
    tok_doc, csrf_doc, cookie_doc, _ = _login("doc_delta2@trustfed.ai", r_doc2["temp_password"])
    client.post("/api/v1/auth/reset-password", json={"current_password": r_doc2["temp_password"], "new_password": "DocPassDelta123!"}, headers={"Authorization": f"Bearer {tok_doc}"})
    tok_doc, csrf_doc, cookie_doc, _ = _login("doc_delta2@trustfed.ai", "DocPassDelta123!")
    headers_doc = {"Authorization": f"Bearer {tok_doc}"}

    assert client.get("/api/v1/auth/me", headers=headers_doc).status_code == 200

    # Suspend hospital hosp-delta-1
    client.post("/api/v1/regional/hospitals/hosp-delta-1/suspend", headers=headers_adm)

    # Doctor access token immediately revoked
    assert client.get("/api/v1/auth/me", headers=headers_doc).status_code == 401

    # Check HospitalNode status is offline in database
    db = SessionLocal()
    node = db.query(models.HospitalNode).filter_by(id="hosp-delta-1").first()
    assert node is not None and node.status == "offline"
    db.close()


def test_actions_appear_in_hash_chained_audit_ledger():
    """Prove that all administrative actions are recorded in the SHA-256 hash-chained audit ledger."""
    db = SessionLocal()
    try:
        verification = store.verify_chain(db)
        assert verification["valid"] is True, f"Audit chain broken: {verification}"

        # Verify key audit event types exist
        events = [r.event_type for r in db.query(models.AuditLog).all()]
        assert "admin" in events
        assert "auth" in events

        # Verify descriptions reflect Phase 2 operations
        descriptions = [r.description for r in db.query(models.AuditLog).all()]
        assert any("Created regional hub" in d for d in descriptions)
        assert any("Issued regional_admin credentials" in d or "Issued" in d for d in descriptions)
        assert any("Suspended" in d for d in descriptions)
        assert any("Password reset" in d for d in descriptions)
    finally:
        db.close()
