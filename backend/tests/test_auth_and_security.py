"""Integration and security tests for TrustFed API:
- PyJWT validation and startup checks
- Rate limiting with proxy awareness
- Access + refresh token rotation with CSRF protection
- Object-level authorization for hospital staff
- Production demo password guard
"""
import os
import sys
import tempfile
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment secret before importing app
os.environ["SECRET_KEY"] = "test-secret-key-high-entropy-0123456789abcdef"
os.environ["ENVIRONMENT"] = "development"

from main import app
from db.database import Base, engine, SessionLocal
from db import models
from services import auth, store

client = TestClient(app)


def setup_module(module):
    from db.migrations.v2_general_disease_migration import migrate_up
    Base.metadata.create_all(bind=engine)
    migrate_up(engine)
    db = SessionLocal()
    try:
        # Seed test hospital users
        u1 = db.query(models.User).filter_by(email="hospital_bgh@trustfed.ai").first()
        if not u1:
            db.add(models.User(
                email="hospital_bgh@trustfed.ai", name="Dr. BGH", role="hospital_staff",
                hospital_id="hosp-bgh", password_hash=auth.hash_password("Pass123!Secure")
            ))
        u2 = db.query(models.User).filter_by(email="hospital_mayo@trustfed.ai").first()
        if not u2:
            db.add(models.User(
                email="hospital_mayo@trustfed.ai", name="Dr. Mayo", role="hospital_staff",
                hospital_id="hosp-mayo", password_hash=auth.hash_password("Pass123!Secure")
            ))
        adm = db.query(models.User).filter_by(email="admin_test@trustfed.ai").first()
        if not adm:
            db.add(models.User(
                email="admin_test@trustfed.ai", name="Global Admin", role="global_admin",
                hospital_id=None, password_hash=auth.hash_password("Pass123!Secure")
            ))

        # Add test predictions
        p1 = db.query(models.PatientPrediction).filter_by(patient_identifier="PT-BGH-01").first()
        if not p1:
            db.add(models.PatientPrediction(
                patient_identifier="PT-BGH-01", hospital_id="hosp-bgh", age=65,
                risk_score=0.82, confidence=0.91, explanation_text="BGH patient"
            ))
        p2 = db.query(models.PatientPrediction).filter_by(patient_identifier="PT-MAYO-02").first()
        if not p2:
            db.add(models.PatientPrediction(
                patient_identifier="PT-MAYO-02", hospital_id="hosp-mayo", age=58,
                risk_score=0.45, confidence=0.88, explanation_text="Mayo patient"
            ))
        db.commit()
    finally:
        db.close()


def test_secret_key_validation_fails_on_insecure_default():
    """Fails startup if SECRET_KEY is missing or insecure in production."""
    old_env = os.environ.get("ENVIRONMENT")
    old_sec = os.environ.get("SECRET_KEY")
    try:
        os.environ["ENVIRONMENT"] = "production"
        os.environ["SECRET_KEY"] = "default"
        try:
            auth.validate_secret_key_on_startup()
            assert False, "Expected startup validation to fail on insecure default secret"
        except RuntimeError as e:
            assert "FATAL" in str(e)
    finally:
        os.environ["ENVIRONMENT"] = old_env or "development"
        os.environ["SECRET_KEY"] = old_sec or "test-secret-key-high-entropy-0123456789abcdef"


def test_login_and_token_refresh_rotation_with_csrf():
    """Verify login issues short-lived token, refresh cookie, and rotation works with CSRF."""
    res = client.post("/api/auth/login", json={"email": "hospital_bgh@trustfed.ai", "password": "Pass123!Secure"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert "token" in data
    assert "csrf_token" in data
    csrf = data["csrf_token"]
    assert "tf_refresh_token" in res.cookies

    # Refresh with valid CSRF header and cookie
    refresh_res = client.post(
        "/api/auth/refresh",
        headers={"X-CSRF-Token": csrf},
        cookies={"tf_refresh_token": res.cookies["tf_refresh_token"]}
    )
    assert refresh_res.status_code == 200, refresh_res.text
    ref_data = refresh_res.json()
    assert "token" in ref_data
    assert "csrf_token" in ref_data
    new_csrf = ref_data["csrf_token"]

    # Replay of old refresh token must be rejected (Token Rotation)
    replay_res = client.post(
        "/api/auth/refresh",
        headers={"X-CSRF-Token": csrf},
        cookies={"tf_refresh_token": res.cookies["tf_refresh_token"]}
    )
    assert replay_res.status_code == 401, "Replayed refresh token must be rejected"

    # Refresh with invalid CSRF token must fail with 403
    bad_csrf_res = client.post(
        "/api/auth/refresh",
        headers={"X-CSRF-Token": "bad-csrf-token"},
        cookies={"tf_refresh_token": refresh_res.cookies["tf_refresh_token"]}
    )
    assert bad_csrf_res.status_code == 403


def test_role_access_control_hospital_staff_blocked_from_admin_routes():
    """Verify hospital staff cannot access restricted admin routes (returns 403)."""
    login_res = client.post("/api/auth/login", json={"email": "hospital_bgh@trustfed.ai", "password": "Pass123!Secure"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Blocked from comparison
    r_comp = client.get("/api/training/comparison", headers=headers)
    assert r_comp.status_code == 403, f"Expected 403, got {r_comp.status_code}"

    # Blocked from starting training
    r_train = client.post("/api/training/sessions", json={"rounds": 5}, headers=headers)
    assert r_train.status_code == 403, f"Expected 403, got {r_train.status_code}"

    # Blocked from audit logs
    r_audit = client.get("/api/audit/logs", headers=headers)
    assert r_audit.status_code == 403, f"Expected 403, got {r_audit.status_code}"

    # Blocked from TEFL fairness report
    r_fair = client.get("/api/tefl/fairness/latest", headers=headers)
    assert r_fair.status_code == 403, f"Expected 403, got {r_fair.status_code}"


def test_object_level_authorization_cross_hospital_isolation():
    """Verify hospital staff can only see their own hospital records; foreign hospital records return 403."""
    # Login as Boston General Hospital staff
    bgh_login = client.post("/api/auth/login", json={"email": "hospital_bgh@trustfed.ai", "password": "Pass123!Secure"})
    bgh_token = bgh_login.json()["token"]
    bgh_headers = {"Authorization": f"Bearer {bgh_token}"}

    # BGH can access its own patient PT-BGH-01
    own_res = client.get("/api/prediction/PT-BGH-01", headers=bgh_headers)
    assert own_res.status_code == 200
    assert own_res.json()["patientId"] == "PT-BGH-01"

    # BGH is FORBIDDEN from accessing Mayo Clinic patient PT-MAYO-02
    cross_res = client.get("/api/prediction/PT-MAYO-02", headers=bgh_headers)
    assert cross_res.status_code == 403, f"Cross-hospital access must return 403, got {cross_res.status_code}"

    # BGH prediction history only contains BGH patients
    hist_res = client.get("/api/prediction/history", headers=bgh_headers)
    assert hist_res.status_code == 200
    items = hist_res.json()["items"]
    for item in items:
        assert item["patientId"] != "PT-MAYO-02"


def test_production_seed_guard():
    """Verify seed_users never creates demo accounts with default passwords in strict production."""
    old_env = os.environ.get("ENVIRONMENT")
    old_allow = os.environ.get("ALLOW_DEMO_USERS")
    try:
        os.environ["ENVIRONMENT"] = "production"
        os.environ["ALLOW_DEMO_USERS"] = "false"
        db = SessionLocal()
        try:
            store.seed_users(db)
            # Verify demo users are either absent or not using "password123"
            for email, _, _, _ in store.DEMO_USERS:
                u = db.query(models.User).filter_by(email=email).first()
                if u:
                    assert not auth.verify_password("password123", u.password_hash)
        finally:
            db.close()
    finally:
        os.environ["ENVIRONMENT"] = old_env or "development"
        if old_allow is not None:
            os.environ["ALLOW_DEMO_USERS"] = old_allow
        else:
            os.environ.pop("ALLOW_DEMO_USERS", None)


def test_per_account_failed_login_throttling():
    """Verify that repeated failed logins against a single account trigger HTTP 429 lockout."""
    target_email = "target_account_throttle@trustfed.ai"
    # Seed user
    db = SessionLocal()
    try:
        u = db.query(models.User).filter_by(email=target_email).first()
        if not u:
            db.add(models.User(
                email=target_email,
                name="Throttled User",
                role="hospital_staff",
                hospital_id="hosp-bgh",
                password_hash=auth.hash_password("ValidPassword123!")
            ))
            db.commit()
    finally:
        db.close()

    # Attempt 5 incorrect passwords with varied client IPs (e.g. X-Forwarded-For)
    for i in range(5):
        resp = client.post(
            "/api/auth/login",
            json={"email": target_email, "password": f"WrongPass{i}!"},
            headers={"X-Forwarded-For": f"198.51.100.{i+1}"}
        )
        assert resp.status_code in (401, 429)

    # 6th attempt on this account must be locked out with HTTP 429 regardless of IP
    lockout_resp = client.post(
        "/api/auth/login",
        json={"email": target_email, "password": "EvenCorrectOrWrongPass!"},
        headers={"X-Forwarded-For": "203.0.113.99"}
    )
    assert lockout_resp.status_code == 429, f"Expected 429 Account Lockout, got {lockout_resp.status_code}"
    assert "Too many failed login attempts for account" in lockout_resp.json()["detail"]


def test_validate_encryption_key_startup_check():
    """Verify that in production environments, missing or invalid PATIENT_ENCRYPTION_KEY fails hard."""
    from services.crypto import validate_encryption_key_on_startup
    from cryptography.fernet import Fernet
    import pytest

    old_env = os.environ.get("ENVIRONMENT")
    old_key = os.environ.get("PATIENT_ENCRYPTION_KEY")
    old_demo = os.environ.get("ALLOW_DEMO_USERS")
    try:
        os.environ["ENVIRONMENT"] = "production"
        os.environ["ALLOW_DEMO_USERS"] = "false"
        
        # 1. Missing key in strict production must raise RuntimeError
        os.environ.pop("PATIENT_ENCRYPTION_KEY", None)
        with pytest.raises(RuntimeError) as exc_missing:
            validate_encryption_key_on_startup()
        assert "PATIENT_ENCRYPTION_KEY environment variable is required in production" in str(exc_missing.value)

        # 2. Invalid Fernet key in production must raise RuntimeError
        os.environ["PATIENT_ENCRYPTION_KEY"] = "not-a-valid-fernet-key"
        with pytest.raises(RuntimeError) as exc_invalid:
            validate_encryption_key_on_startup()
        assert "not a valid Fernet key" in str(exc_invalid.value)

        # 3. Valid Fernet key in production succeeds
        valid_key = Fernet.generate_key().decode()
        os.environ["PATIENT_ENCRYPTION_KEY"] = valid_key
        validate_encryption_key_on_startup()  # Should not raise

        # 4. In demo mode on Render without key set, logs warning without fatal crash
        os.environ["ALLOW_DEMO_USERS"] = "true"
        os.environ.pop("PATIENT_ENCRYPTION_KEY", None)
        validate_encryption_key_on_startup()  # Should not raise in demo mode

        # 5. In development, missing key is allowed
        os.environ["ENVIRONMENT"] = "development"
        os.environ["ALLOW_DEMO_USERS"] = "false"
        os.environ.pop("PATIENT_ENCRYPTION_KEY", None)
        validate_encryption_key_on_startup()  # Should not raise
    finally:
        if old_env: os.environ["ENVIRONMENT"] = old_env
        else: os.environ.pop("ENVIRONMENT", None)
        if old_key: os.environ["PATIENT_ENCRYPTION_KEY"] = old_key
        else: os.environ.pop("PATIENT_ENCRYPTION_KEY", None)
        if old_demo: os.environ["ALLOW_DEMO_USERS"] = old_demo
        else: os.environ.pop("ALLOW_DEMO_USERS", None)


def test_bcrypt_rehashing_on_successful_login():
    """Verify that legacy PBKDF2 password hashes are automatically upgraded to bcrypt (rounds=12) on successful login."""
    import hashlib
    from db.database import SessionLocal
    from db import models

    pw = "LegacyPBKDF2Password!2026"
    salt = "a1b2c3d4e5f60718"
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex()
    legacy_hash = f"pbkdf2_sha256$200000${salt}${dk}"

    db = SessionLocal()
    try:
        test_user = db.query(models.User).filter_by(email="legacy_user@trustfed.ai").first()
        if not test_user:
            test_user = models.User(
                email="legacy_user@trustfed.ai",
                name="Legacy Hash User",
                role="doctor",
                hospital_id="1",
                password_hash=legacy_hash,
                status="active"
            )
            db.add(test_user)
        else:
            test_user.password_hash = legacy_hash
            test_user.status = "active"
            test_user.deleted_at = None
        db.commit()

        db.refresh(test_user)
        assert test_user.password_hash.startswith("pbkdf2_sha256$")

        # Login via API
        login_res = client.post("/api/v1/auth/login", json={"email": "legacy_user@trustfed.ai", "password": pw})
        assert login_res.status_code == 200, f"Expected 200, got {login_res.status_code}: {login_res.text}"

        # Verify password_hash in DB has been transparently upgraded to bcrypt work factor 12
        db.refresh(test_user)
        assert test_user.password_hash.startswith(("$2b$12$", "$2a$12$", "$2y$12$")), (
            f"Expected bcrypt hash starting with $2b$12$, got: {test_user.password_hash[:15]}"
        )

        # Subsequent login works with upgraded bcrypt hash
        login_res_2 = client.post("/api/v1/auth/login", json={"email": "legacy_user@trustfed.ai", "password": pw})
        assert login_res_2.status_code == 200
    finally:
        db.close()


if __name__ == "__main__":
    import time
    setup_module(sys.modules[__name__])
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for f in fns:
        t = time.time(); f(); print(f"PASS {f.__name__} ({time.time()-t:.2f}s)")
    print(f"\n{len(fns)} security & auth tests passed successfully!")
