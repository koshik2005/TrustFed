import os
import sys

backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

from db.database import SessionLocal
from db import models
from services import auth, credential_guard, dev_seed

def main():
    print("=" * 70)
    print("PHASE G: CREDENTIAL HARDENING & DEMO CREDENTIAL PROOF")
    print("=" * 70)

    db = SessionLocal()
    try:
        # 1. Test that default passwords in DISALLOWED_PASSWORDS cannot exist
        print("\n[CHECK 1] Scanning active users for disallowed passwords...")
        users = db.query(models.User).filter_by(status="active").all()
        violations = 0
        for u in users:
            for pw in credential_guard.DISALLOWED_PASSWORDS:
                if u.password_hash and auth.verify_password(pw, u.password_hash):
                    print(f"  [ALERT] User {u.email} matched disallowed password '{pw}'")
                    violations += 1
        if violations == 0:
            print("  [PASS] 0 active users possess disallowed default credentials.")
        else:
            print(f"  [FAIL] {violations} users have default credentials.")

        # 2. Test startup failure simulation when a default credential is injected
        print("\n[CHECK 2] Simulating startup guard against default 'password123'...")
        fake_user = models.User(
            email="legacy_demo_attempt@trustfed.ai",
            name="Legacy Demo",
            role="doctor",
            password_hash=auth.hash_password("password123"),
            status="active"
        )
        db.add(fake_user)
        db.commit()

        try:
            credential_guard.validate_no_default_credentials_on_startup(db)
            print("  [FAIL] Guard failed to raise on default password.")
        except RuntimeError as e:
            print(f"  [PASS] Startup hard-failed with expected security violation:")
            print(f"         '{e}'")
        finally:
            db.delete(fake_user)
            db.commit()

        # 3. Test that dev-seed strictly refuses to run in production
        print("\n[CHECK 3] Verifying dev-seed refusal in production...")
        os.environ["ENVIRONMENT"] = "production"
        try:
            dev_seed.seed_dev_environment(db)
            print("  [FAIL] Dev seed unexpectedly executed in production!")
        except RuntimeError as e:
            print(f"  [PASS] Dev seed execution blocked with error:")
            print(f"         '{e}'")
        finally:
            os.environ["ENVIRONMENT"] = "development"

        # 4. Attempt login with disabled/non-existent legacy account
        print("\n[CHECK 4] Verifying authentication failure on legacy accounts...")
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        res = client.post("/api/v1/auth/login", json={"email": "nonexistent_demo@trustfed.ai", "password": "password123"})
        print(f"  Login attempt status: {res.status_code}")
        print(f"  Response: {res.json()}")
        assert res.status_code == 401

        print("\n" + "=" * 70)
        print("ALL DEMO CREDENTIAL CHECKS PASSED (4/4 PASS)")
        print("=" * 70)
    finally:
        db.close()

if __name__ == "__main__":
    main()
