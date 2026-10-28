import urllib.request
import urllib.error
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
sys.path.insert(0, "backend")

BASE_URL = "https://trustfed-backend.onrender.com"

# 1. Login as hospital staff
req = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=json.dumps({"email": "hospital@trustfed.ai", "password": "password123"}).encode(),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    token = data["token"]
    user = data["user"]
    print("Login status:", resp.status)
    print(f"Logged in user: {user.get('email')} ({user.get('role')}), hospitalId: {user.get('hospitalId')}")

def fetch(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

# 2. Attempt to access Global Admin route /api/audit/logs as hospital_staff
status, body = fetch(f"{BASE_URL}/api/audit/logs", token)
print(f"Access /api/audit/logs as hospital_staff -> Status: {status} ({body})")

# 3. Attempt to access /api/training/hospitals as hospital_staff
status, body = fetch(f"{BASE_URL}/api/training/hospitals", token)
items = json.loads(body) if status == 200 else body
print(f"Access /api/training/hospitals as hospital_staff -> Status: {status}, Returned nodes count: {len(items) if isinstance(items, list) else items}")

# 5. Create a prediction as hospital_staff (hospital_id: 1)
vitals_data = {
    "age": "60", "sex": "1", "chestPainType": "3", "restingBP": "140", "cholesterol": "250",
    "fastingBloodSugar": False, "restingECG": "1", "maxHeartRate": "130", "exerciseAngina": True,
    "oldPeak": "1.5", "slope": "2", "ca": "1", "thal": "6"
}
pred_req = urllib.request.Request(
    f"{BASE_URL}/api/prediction/predict",
    data=json.dumps(vitals_data).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
)
with urllib.request.urlopen(pred_req) as resp:
    pred_data = json.loads(resp.read().decode())
    patient_id = pred_data["patientId"]
    print(f"Created patient prediction #{patient_id} for hospital 1 (Score: {pred_data['riskScore']:.2f})")

# 6. Attempt to access this prediction with a user from a DIFFERENT hospital (e.g. hospital 2)
from services import auth
other_hospital_token = auth.create_token({
    "sub": "doctor@chicago-general.org",
    "role": "hospital_staff",
    "hospital_id": "2",
    "user_id": 999
}, ttl=300)

status, body = fetch(f"{BASE_URL}/api/prediction/{patient_id}", other_hospital_token)
print(f"Cross-Hospital access attempt: Hospital 2 user requesting Hospital 1 patient #{patient_id} -> Status: {status} ({body})")
