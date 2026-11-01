import os
import json
import urllib.request
import urllib.error

BACKEND_URL = "https://trustfed-backend.onrender.com/api/v1"

# Read target new passwords from environment variables or use strong defaults
ACCOUNTS = {
    "admin@trustfed.ai": os.getenv("TEST_ADMIN_PASSWORD", "TrustFed2026!SecAdmin"),
    "doctor@trustfed.ai": os.getenv("TEST_DOCTOR_PASSWORD", "TrustFed2026!SecDoc"),
    "regional@trustfed.ai": os.getenv("TEST_REGIONAL_PASSWORD", "TrustFed2026!SecReg"),
    "hospital@trustfed.ai": os.getenv("TEST_STAFF_PASSWORD", "TrustFed2026!SecStaff"),
}

def rotate():
    print("=" * 70)
    print("ROTATING PASSWORDS ON DEPLOYED BACKEND AWAY FROM password123")
    print("=" * 70)
    
    for email, new_pwd in ACCOUNTS.items():
        # Step 1: Login with password123
        login_data = json.dumps({"email": email, "password": "password123"}).encode("utf-8")
        req = urllib.request.Request(
            f"{BACKEND_URL}/auth/login",
            data=login_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                token = data["token"]
                print(f"[LOGIN OK] {email} logged in with temporary password123.")
                
                # Step 2: Reset password
                reset_data = json.dumps({
                    "current_password": "password123",
                    "new_password": new_pwd
                }).encode("utf-8")
                reset_req = urllib.request.Request(
                    f"{BACKEND_URL}/auth/reset-password",
                    data=reset_data,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(reset_req) as r_resp:
                    r_data = json.loads(r_resp.read().decode())
                    print(f"  [ROTATED] {email}: {r_data.get('message')}")
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            print(f"  [INFO] {email}: HTTP {e.code} ({err}) - may already be rotated.")

if __name__ == "__main__":
    rotate()
