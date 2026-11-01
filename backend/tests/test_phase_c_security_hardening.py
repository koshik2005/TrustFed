"""Phase C Security Hardening Test Suite.

Verifies:
1. MFA (TOTP RFC 6238): Setup, enable, login challenge, verification, wrong code rejection,
   single-use recovery codes (replay prevention), disable, and audited admin reset.
2. Default Credential Guard: Startup rejection of default credentials ('password123'),
   and dev-seed strict prohibition under production environments.
3. Destructive Admin Actions & Soft Delete: Soft-delete for hubs, hospitals, and users;
   audit logging; immediate bearer token invalidation; restoration; and retention-based purge.
4. Security Disclosures & Endpoints: RFC 9116 security.txt route and content.
"""
import datetime
import os
import time
import pyotp
import pytest
from fastapi.testclient import TestClient

from db.database import SessionLocal, engine
from db import models
from services import auth, crypto, mfa, credential_guard, dev_seed, store
from main import app
from db.migrations.v4_mfa_and_soft_delete import migrate_up as migrate_v4_mfa

client = TestClient(app)


def setup_module(module):
    migrate_v4_mfa(engine)


@pytest.fixture(autouse=True)
def clean_auth_caches():
    auth.reset_auth_key_cache()
    yield
    auth.reset_auth_key_cache()


def _create_test_user(db, email, role="doctor", hospital_id="hosp-c-test", hub_id="hub-c-test", password="SecurePhaseCPass123!"):
    u = db.query(models.User).filter_by(email=email).first()
    if not u:
        u = models.User(
            email=email,
            name=f"User {email}",
            role=role,
            hospital_id=hospital_id,
            hub_id=hub_id,
            password_hash=auth.hash_password(password),
            status="active",
            must_reset_password=False,
            mfa_enabled=False
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    else:
        u.password_hash = auth.hash_password(password)
        u.status = "active"
        u.must_reset_password = False
        u.mfa_enabled = False
        u.deleted_at = None
        u.deleted_by = None
        db.commit()
    return u


def _create_test_hierarchy(db):
    hub = db.query(models.RegionalHub).filter_by(id="hub-c-test").first()
    if not hub:
        hub = models.RegionalHub(id="hub-c-test", name="Phase C Hub", region="North", status="active")
        db.add(hub)
        db.commit()
    else:
        hub.status = "active"
        hub.deleted_at = None
        hub.deleted_by = None
        db.commit()

    hosp = db.query(models.Hospital).filter_by(id="hosp-c-test").first()
    if not hosp:
        hosp = models.Hospital(id="hosp-c-test", name="Phase C Hospital", hub_id="hub-c-test", status="active")
        db.add(hosp)
        db.commit()
    else:
        hosp.status = "active"
        hosp.deleted_at = None
        hosp.deleted_by = None
        db.commit()


# ── 1. MFA (TOTP) Enrollment, Verification & Recovery ────────────────────────

def test_mfa_full_lifecycle():
    """Tests the complete MFA flow: setup -> enable -> challenge on login -> verify -> recovery -> disable."""
    db = SessionLocal()
    try:
        _create_test_hierarchy(db)
        user = _create_test_user(db, "mfa_doctor@trustfed.ai", role="doctor")
    finally:
        db.close()

    # Step 1: Login initially without MFA enabled
    login_resp = client.post("/api/v1/auth/login", json={"email": "mfa_doctor@trustfed.ai", "password": "SecurePhaseCPass123!"})
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Call /auth/mfa/setup
    setup_resp = client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup_resp.status_code == 200
    setup_data = setup_resp.json()
    secret = setup_data["secret"]
    assert len(secret) == 32
    assert "otpauth://" in setup_data["otpauth_uri"]

    # Verify secret is encrypted in database
    db = SessionLocal()
    try:
        u_db = db.query(models.User).filter_by(email="mfa_doctor@trustfed.ai").first()
        assert u_db.mfa_secret is not None
        assert u_db.mfa_secret != secret  # Must be encrypted at rest!
        assert mfa.decrypt_mfa_secret(u_db.mfa_secret) == secret
        assert u_db.mfa_enabled is False  # Not enabled until verified
    finally:
        db.close()

    # Step 3: Enable MFA with an INVALID code should fail
    bad_enable = client.post("/api/v1/auth/mfa/enable", json={"code": "000000"}, headers=headers)
    assert bad_enable.status_code == 400
    assert "Invalid MFA verification code" in bad_enable.json()["detail"]

    # Step 4: Enable MFA with a VALID code
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    good_enable = client.post("/api/v1/auth/mfa/enable", json={"code": valid_code}, headers=headers)
    assert good_enable.status_code == 200
    enable_data = good_enable.json()
    assert enable_data["mfa_enabled"] is True
    recovery_codes = enable_data["recovery_codes"]
    assert len(recovery_codes) == 8

    # Step 5: Next login MUST challenge for MFA code
    challenge_login = client.post("/api/v1/auth/login", json={"email": "mfa_doctor@trustfed.ai", "password": "SecurePhaseCPass123!"})
    assert challenge_login.status_code == 200
    c_data = challenge_login.json()
    assert c_data.get("mfa_required") is True
    assert "token" not in c_data or c_data.get("token") is None
    mfa_tok = c_data["mfa_token"]

    # Step 6: Verify with WRONG MFA code should fail (401)
    wrong_verify = client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa_tok, "code": "999999"})
    assert wrong_verify.status_code == 401
    assert "Invalid MFA code" in wrong_verify.json()["detail"]

    # Step 7: Verify with VALID MFA code should succeed and issue tokens
    valid_verify_code = totp.now()
    good_verify = client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa_tok, "code": valid_verify_code})
    assert good_verify.status_code == 200
    v_data = good_verify.json()
    assert "token" in v_data
    assert "csrf_token" in v_data
    assert "tf_refresh_token" in good_verify.cookies

    # Step 8: Recovery code authentication
    # Get a fresh challenge login
    chal_login2 = client.post("/api/v1/auth/login", json={"email": "mfa_doctor@trustfed.ai", "password": "SecurePhaseCPass123!"})
    mfa_tok2 = chal_login2.json()["mfa_token"]

    # Attempt with bad recovery code
    bad_rec = client.post("/api/v1/auth/mfa/recovery", json={"mfa_token": mfa_tok2, "recovery_code": "INVALID-CODE"})
    assert bad_rec.status_code == 401

    # Attempt with valid recovery code
    used_rec_code = recovery_codes[0]
    good_rec = client.post("/api/v1/auth/mfa/recovery", json={"mfa_token": mfa_tok2, "recovery_code": used_rec_code})
    assert good_rec.status_code == 200
    assert "token" in good_rec.json()

    # Replay protection: reusing the SAME recovery code MUST be rejected
    chal_login3 = client.post("/api/v1/auth/login", json={"email": "mfa_doctor@trustfed.ai", "password": "SecurePhaseCPass123!"})
    mfa_tok3 = chal_login3.json()["mfa_token"]
    replay_rec = client.post("/api/v1/auth/mfa/recovery", json={"mfa_token": mfa_tok3, "recovery_code": used_rec_code})
    assert replay_rec.status_code == 401
    assert "Invalid or already consumed recovery code" in replay_rec.json()["detail"]

    # Step 9: Disable MFA with valid code
    auth_header = {"Authorization": f"Bearer {good_rec.json()['token']}"}
    disable_resp = client.post("/api/v1/auth/mfa/disable", json={"code": totp.now()}, headers=auth_header)
    assert disable_resp.status_code == 200
    assert disable_resp.json()["mfa_enabled"] is False


def test_admin_mfa_reset_is_audited():
    """Verify that global admin can reset MFA for an account and the action is cryptographically logged."""
    db = SessionLocal()
    try:
        _create_test_hierarchy(db)
        admin = _create_test_user(db, "admin_mfa_reset@trustfed.ai", role="global_admin")
        target = _create_test_user(db, "locked_doctor@trustfed.ai", role="doctor")
        # Manually enable MFA on target
        target.mfa_enabled = True
        target.mfa_secret = mfa.encrypt_mfa_secret(pyotp.random_base32())
        db.commit()
        target_id = target.id
    finally:
        db.close()

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_mfa_reset@trustfed.ai", "password": "SecurePhaseCPass123!"})
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Perform admin MFA reset
    reset_resp = client.post(f"/api/v1/admin/users/{target_id}/mfa/reset", headers=admin_headers)
    assert reset_resp.status_code == 200
    assert reset_resp.json()["mfa_enabled"] is False

    # Check database state and audit log
    db = SessionLocal()
    try:
        updated = db.query(models.User).filter_by(id=target_id).first()
        assert updated.mfa_enabled is False
        assert updated.mfa_secret is None
        assert updated.must_reset_password is True

        # Verify audit record exists
        audit_entry = db.query(models.AuditLog).filter(
            models.AuditLog.event_type == "admin",
            models.AuditLog.description.contains("Admin MFA Reset")
        ).order_by(models.AuditLog.id.desc()).first()
        assert audit_entry is not None
        assert "locked_doctor@trustfed.ai" in audit_entry.description
    finally:
        db.close()


# ── 2. Credential Guard & Dev Seed Isolation ─────────────────────────────────

def test_startup_fails_if_default_credential_exists():
    """Verify that validate_no_default_credentials_on_startup raises RuntimeError on 'password123'."""
    db = SessionLocal()
    try:
        # Create a user with password123
        bad_user = models.User(
            email="insecure_demo@trustfed.ai",
            name="Insecure Demo",
            role="doctor",
            password_hash=auth.hash_password("password123"),
            status="active"
        )
        db.add(bad_user)
        db.commit()

        with pytest.raises(RuntimeError) as exc_info:
            credential_guard.validate_no_default_credentials_on_startup(db)
        assert "FATAL SECURITY VIOLATION" in str(exc_info.value)
        assert "password123" in str(exc_info.value)

        # Cleanup
        db.delete(bad_user)
        db.commit()
    finally:
        db.close()


def test_dev_seed_blocked_in_production():
    """Verify that dev_seed strictly refuses to run under ENVIRONMENT=production."""
    old_env = os.environ.get("ENVIRONMENT")
    try:
        os.environ["ENVIRONMENT"] = "production"
        db = SessionLocal()
        try:
            with pytest.raises(RuntimeError) as exc:
                dev_seed.seed_dev_environment(db)
            assert "strictly prohibited in production" in str(exc.value)
        finally:
            db.close()
    finally:
        if old_env:
            os.environ["ENVIRONMENT"] = old_env
        else:
            os.environ.pop("ENVIRONMENT", None)


# ── 3. Destructive Admin Actions & Soft Delete ───────────────────────────────

def test_hub_soft_delete_and_restore():
    """Test regional hub soft deletion, listing filter, and restore."""
    db = SessionLocal()
    try:
        admin = _create_test_user(db, "admin_hub_sd@trustfed.ai", role="global_admin")
        # Ensure temporary hub exists cleanly
        hub = db.query(models.RegionalHub).filter_by(id="hub-to-delete").first()
        if not hub:
            hub = models.RegionalHub(id="hub-to-delete", name="Hub To Delete", region="South", status="active")
            db.add(hub)
        else:
            hub.status = "active"
            hub.deleted_at = None
            hub.deleted_by = None
        db.commit()
    finally:
        db.close()

    try:
        admin_login = client.post("/api/v1/auth/login", json={"email": "admin_hub_sd@trustfed.ai", "password": "SecurePhaseCPass123!"})
        headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}

        # Soft delete the hub
        del_res = client.delete("/api/v1/admin/hubs/hub-to-delete", headers=headers)
        assert del_res.status_code == 200
        assert "soft-deleted" in del_res.json()["message"]

        # Verify not returned in default listing
        list_res = client.get("/api/v1/admin/hubs", headers=headers)
        assert list_res.status_code == 200
        hub_ids = [h["id"] for h in list_res.json()]
        assert "hub-to-delete" not in hub_ids

        # Verify returned when include_deleted=true
        list_all = client.get("/api/v1/admin/hubs?include_deleted=true", headers=headers)
        assert list_all.status_code == 200
        all_hub_ids = [h["id"] for h in list_all.json()]
        assert "hub-to-delete" in all_hub_ids

        # Restore the hub
        restore_res = client.post("/api/v1/admin/hubs/hub-to-delete/restore", headers=headers)
        assert restore_res.status_code == 200
        assert "restored" in restore_res.json()["message"]

        # Verify it appears in default listing again
        list_restored = client.get("/api/v1/admin/hubs", headers=headers)
        restored_ids = [h["id"] for h in list_restored.json()]
        assert "hub-to-delete" in restored_ids
    finally:
        db = SessionLocal()
        try:
            h = db.query(models.RegionalHub).filter_by(id="hub-to-delete").first()
            if h:
                db.delete(h)
                db.commit()
        finally:
            db.close()
    assert "hub-to-delete" in restored_ids


def test_user_soft_delete_immediate_token_revocation_and_restore():
    """Test that soft deleting a user immediately revokes bearer tokens and restore reactivates them."""
    db = SessionLocal()
    try:
        _create_test_hierarchy(db)
        admin = _create_test_user(db, "admin_user_sd@trustfed.ai", role="global_admin")
        target = _create_test_user(db, "doc_to_delete@trustfed.ai", role="doctor")
        target_id = target.id
    finally:
        db.close()

    # Log in as target to get an active token
    target_login = client.post("/api/v1/auth/login", json={"email": "doc_to_delete@trustfed.ai", "password": "SecurePhaseCPass123!"})
    target_token = target_login.json()["token"]
    target_headers = {"Authorization": f"Bearer {target_token}"}

    # Verify target token works initially
    pre_check = client.get("/api/v1/auth/me", headers=target_headers)
    assert pre_check.status_code == 200

    # Admin soft deletes target user
    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_user_sd@trustfed.ai", "password": "SecurePhaseCPass123!"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}

    del_user_res = client.delete(f"/api/v1/admin/users/{target_id}", headers=admin_headers)
    assert del_user_res.status_code == 200

    # Target token MUST BE REJECTED IMMEDIATELY with 401
    post_check = client.get("/api/v1/auth/me", headers=target_headers)
    assert post_check.status_code == 401
    assert "suspended, deleted, or inactive" in post_check.json()["detail"]

    # Admin restores the user
    restore_res = client.post(f"/api/v1/admin/users/{target_id}/restore", headers=admin_headers)
    assert restore_res.status_code == 200

    # Re-login should succeed after restore
    relogin = client.post("/api/v1/auth/login", json={"email": "doc_to_delete@trustfed.ai", "password": "SecurePhaseCPass123!"})
    assert relogin.status_code == 200


def test_purge_deleted_records_respects_retention():
    """Test that purge-deleted only purges records older than retention period."""
    db = SessionLocal()
    try:
        admin = _create_test_user(db, "admin_purge@trustfed.ai", role="global_admin")

        # 1. Old deleted user (40 days ago -> beyond 30-day retention)
        old_user = models.User(
            email="old_deleted@trustfed.ai",
            name="Old Deleted",
            role="hospital_staff",
            password_hash=auth.hash_password("Pass123!Secure"),
            status="deleted",
            deleted_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=40)
        )
        db.add(old_user)

        # 2. Recently deleted user (5 days ago -> within 30-day retention)
        recent_user = models.User(
            email="recent_deleted@trustfed.ai",
            name="Recent Deleted",
            role="hospital_staff",
            password_hash=auth.hash_password("Pass123!Secure"),
            status="deleted",
            deleted_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)
        )
        db.add(recent_user)
        db.commit()
    finally:
        db.close()

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_purge@trustfed.ai", "password": "SecurePhaseCPass123!"})
    headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}

    # Execute purge with 30-day retention
    purge_res = client.post("/api/v1/admin/purge-deleted", json={"retention_days": 30}, headers=headers)
    assert purge_res.status_code == 200
    purged_info = purge_res.json()["purged"]
    assert purged_info["users"] >= 1

    # Verify old user is purged (hard deleted), while recent user is preserved
    db = SessionLocal()
    try:
        assert db.query(models.User).filter_by(email="old_deleted@trustfed.ai").first() is None
        assert db.query(models.User).filter_by(email="recent_deleted@trustfed.ai").first() is not None
        # Clean up recent user
        r = db.query(models.User).filter_by(email="recent_deleted@trustfed.ai").first()
        db.delete(r)
        db.commit()
    finally:
        db.close()


# ── 4. RFC 9116 security.txt Endpoint ────────────────────────────────────────

def test_security_txt_endpoint():
    """Verify that /.well-known/security.txt serves RFC 9116 compliant contact info with text/plain."""
    res1 = client.get("/.well-known/security.txt")
    assert res1.status_code == 200
    assert "text/plain" in res1.headers["content-type"]
    assert "Contact: mailto:security@trustfed.ai" in res1.text
    assert "Expires:" in res1.text
    assert "Canonical:" in res1.text

    res2 = client.get("/security.txt")
    assert res2.status_code == 200
    assert "Contact: mailto:security@trustfed.ai" in res2.text
