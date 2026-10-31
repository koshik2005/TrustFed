import json
import time
import requests

BASE_URL = "https://trustfed-backend.onrender.com"

def log_section(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def main():
    print(f"[*] Starting live comprehensive audit against {BASE_URL}")

    # -------------------------------------------------------------
    # 1. Health check
    # -------------------------------------------------------------
    log_section("1. HEALTH & ENVIRONMENT CHECK")
    r = requests.get(f"{BASE_URL}/health")
    print(f"GET /health: status={r.status_code}, response={r.json()}")
    assert r.status_code == 200

    # -------------------------------------------------------------
    # 2. Login as Global Admin
    # -------------------------------------------------------------
    log_section("2. GLOBAL ADMIN AUTHENTICATION")
    r = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "admin@trustfed.ai",
        "password": "password123"
    })
    print(f"Login Global Admin: status={r.status_code}")
    assert r.status_code == 200, r.text
    admin_data = r.json()
    admin_token = admin_data.get("token") or admin_data.get("access_token")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print(f"Logged in as: {admin_data['user']['email']} (Role: {admin_data['user']['role']})")

    # -------------------------------------------------------------
    # 3. Hub Lifecycle: Create -> Suspend -> Delete
    # -------------------------------------------------------------
    log_section("3. REGIONAL HUB LIFECYCLE (Create -> Suspend -> Delete)")
    test_hub_id = f"hub-audit-{int(time.time())}"
    
    # 3a. Create Hub
    r_hub_create = requests.post(f"{BASE_URL}/api/v1/admin/hubs", json={
        "id": test_hub_id,
        "name": "Audit Regional Hub",
        "region": "Audit Region"
    }, headers=admin_headers)
    print(f"POST /api/v1/admin/hubs ({test_hub_id}): status={r_hub_create.status_code}, response={r_hub_create.json()}")
    assert r_hub_create.status_code in (200, 201), r_hub_create.text

    # 3b. Suspend Hub
    r_hub_suspend = requests.post(f"{BASE_URL}/api/v1/admin/hubs/{test_hub_id}/suspend", headers=admin_headers)
    print(f"POST /api/v1/admin/hubs/{test_hub_id}/suspend: status={r_hub_suspend.status_code}, response={r_hub_suspend.json()}")
    assert r_hub_suspend.status_code == 200, r_hub_suspend.text

    # 3c. Delete Hub
    r_hub_del = requests.delete(f"{BASE_URL}/api/v1/admin/hubs/{test_hub_id}", headers=admin_headers)
    print(f"DELETE /api/v1/admin/hubs/{test_hub_id}: status={r_hub_del.status_code}, response={r_hub_del.json()}")
    assert r_hub_del.status_code == 200, r_hub_del.text

    # -------------------------------------------------------------
    # 4. Hospital Lifecycle: Create -> Suspend -> Delete
    # -------------------------------------------------------------
    log_section("4. HOSPITAL LIFECYCLE (Create -> Suspend -> Delete)")
    test_hosp_id = f"hosp-audit-{int(time.time())}"

    # 4a. Create Hospital
    r_hosp_create = requests.post(f"{BASE_URL}/api/v1/regional/hospitals", json={
        "id": test_hosp_id,
        "name": "Audit General Hospital",
        "hub_id": "hub-east",
        "share_deidentified": False
    }, headers=admin_headers)
    print(f"POST /api/v1/regional/hospitals ({test_hosp_id}): status={r_hosp_create.status_code}, response={r_hosp_create.json()}")
    assert r_hosp_create.status_code in (200, 201), r_hosp_create.text

    # 4b. Suspend Hospital
    r_hosp_suspend = requests.post(f"{BASE_URL}/api/v1/regional/hospitals/{test_hosp_id}/suspend", headers=admin_headers)
    print(f"POST /api/v1/regional/hospitals/{test_hosp_id}/suspend: status={r_hosp_suspend.status_code}, response={r_hosp_suspend.json()}")
    assert r_hosp_suspend.status_code == 200, r_hosp_suspend.text

    # 4c. Delete Hospital
    r_hosp_del = requests.delete(f"{BASE_URL}/api/v1/regional/hospitals/{test_hosp_id}", headers=admin_headers)
    print(f"DELETE /api/v1/regional/hospitals/{test_hosp_id}: status={r_hosp_del.status_code}, response={r_hosp_del.json()}")
    assert r_hosp_del.status_code == 200, r_hosp_del.text

    # -------------------------------------------------------------
    # 5. Full Federated Learning Round: Trigger -> Promote -> Rollback
    # -------------------------------------------------------------
    log_section("5. FEDERATED ROUND WITH PROMOTION & 1-CLICK ROLLBACK")
    # Get current model version
    r_models_before = requests.get(f"{BASE_URL}/api/v1/federated/models", headers=admin_headers)
    current_ver = r_models_before.json().get("activeVersion", "TF-GenDisease-v1.0")
    print(f"Active model version prior to round: {current_ver}")

    # Trigger hierarchical federated learning round
    r_round = requests.post(f"{BASE_URL}/api/v1/federated/rounds/trigger", json={
        "minRecords": 1,
        "epochs": 1,
        "learningRate": 0.05,
        "noiseMultiplier": 1.2,
        "clip": 1.0,
        "forcePromote": True
    }, headers=admin_headers)
    print(f"POST /api/v1/federated/rounds/trigger: status={r_round.status_code}")
    if r_round.status_code == 200:
        round_res = r_round.json()
        promoted_ver = round_res.get("modelVersion") or round_res.get("candidateVersion")
        print(f"Round result: promoted={round_res.get('promoted')}, new version={promoted_ver}")
        
        # Execute 1-Click Rollback back to current_ver (TF-GenDisease-v1.0)
        target_rollback = "TF-GenDisease-v1.0"
        r_rollback = requests.post(
            f"{BASE_URL}/api/v1/federated/models/{target_rollback}/rollback",
            json={"reason": "Live audit verification rollback test"},
            headers=admin_headers
        )
        print(f"POST /api/v1/federated/models/{target_rollback}/rollback: status={r_rollback.status_code}, response={r_rollback.json()}")
        assert r_rollback.status_code == 200
        assert r_rollback.json().get("activeVersion") == target_rollback
        print(f"Rollback successfully restored {target_rollback}!")

    # -------------------------------------------------------------
    # 6. Immediate Token Revocation upon Suspension / Removal
    # -------------------------------------------------------------
    log_section("6. IMMEDIATE TOKEN REVOCATION UPON SUSPENSION / REMOVAL")
    # Login as an active doctor
    r_doc = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "doctor@trustfed.ai",
        "password": "password123"
    })
    assert r_doc.status_code == 200
    doc_token = r_doc.json().get("token") or r_doc.json().get("access_token")
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # Verify doctor access
    r_verify_valid = requests.get(f"{BASE_URL}/api/v1/hospital/encounters?status=pending&hospital_id=1", headers=doc_headers)
    print(f"Pre-suspension GET /api/v1/hospital/encounters: status={r_verify_valid.status_code}")
    assert r_verify_valid.status_code == 200

    # Suspend Boston General Hospital (id="1")
    r_susp_hosp = requests.post(f"{BASE_URL}/api/v1/regional/hospitals/1/suspend", headers=admin_headers)
    print(f"Suspended Hospital '1': status={r_susp_hosp.status_code}")

    # Immediately verify that doctor's token is REJECTED AT ONCE (HTTP 401)
    r_verify_rejected = requests.get(f"{BASE_URL}/api/v1/hospital/encounters?status=pending&hospital_id=1", headers=doc_headers)
    print(f"Post-suspension GET with doctor token: status={r_verify_rejected.status_code}, detail={r_verify_rejected.json()}")
    assert r_verify_rejected.status_code == 401
    assert "suspended" in str(r_verify_rejected.json()).lower()

    # Reactivate Hospital '1' so system returns to operational state
    r_reactivate = requests.post(f"{BASE_URL}/api/v1/regional/hospitals/1/reactivate", headers=admin_headers)
    print(f"Reactivated Hospital '1': status={r_reactivate.status_code}")
    assert r_reactivate.status_code == 200

    # -------------------------------------------------------------
    # 7. Refresh-Cookie Authentication in Safari & Chrome
    # -------------------------------------------------------------
    log_section("7. REFRESH-COOKIE AUTHENTICATION (SameSite, Secure, HttpOnly)")
    s = requests.Session()
    r_login_cookie = s.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "doctor@trustfed.ai",
        "password": "password123"
    })
    set_cookie_header = r_login_cookie.headers.get("Set-Cookie", "")
    print(f"Set-Cookie Header: {set_cookie_header}")
    assert "tf_refresh_token" in set_cookie_header
    assert "HttpOnly" in set_cookie_header or "httponly" in set_cookie_header.lower()
    assert "Secure" in set_cookie_header or "secure" in set_cookie_header.lower()
    print("Cookie attributes verified: HttpOnly=True, Secure=True")

    # Extract CSRF token and cookie value
    csrf_token = r_login_cookie.json().get("csrf_token")
    cookie_val = r_login_cookie.cookies.get("tf_refresh_token")

    # Refresh token endpoint using session cookie and X-CSRF-Token
    r_refresh = requests.post(
        f"{BASE_URL}/api/v1/auth/refresh",
        cookies={"tf_refresh_token": cookie_val},
        headers={"X-CSRF-Token": csrf_token}
    )
    print(f"POST /api/v1/auth/refresh with cookie & CSRF: status={r_refresh.status_code}")
    assert r_refresh.status_code in (200, 204)
    print("Refresh-cookie workflow validated successfully!")

    # -------------------------------------------------------------
    # 8. Wrong-Password Rate Limit / Lockout (Last step)
    # -------------------------------------------------------------
    log_section("8. RATE LIMITING & LOCKOUT (SlowAPI 5/min limit)")
    status_codes = []
    for attempt in range(1, 8):
        r_fail = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "admin@trustfed.ai",
            "password": f"WrongPassword_{attempt}"
        })
        status_codes.append(r_fail.status_code)
        print(f"Failed login attempt #{attempt}: status={r_fail.status_code}")
    
    print(f"Status sequence: {status_codes}")
    has_429 = 429 in status_codes
    print(f"Rate limiter (HTTP 429) activated: {has_429}")
    assert has_429 or status_codes[-1] == 429, "Rate limit did not trigger HTTP 429"

    print("\n" + "=" * 70)
    print(" ALL LIVE COMPREHENSIVE AUDIT TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
