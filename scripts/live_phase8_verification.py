import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
base_url = "https://trustfed-backend.onrender.com"

def api_call(path, method="GET", data=None, token=None):
    url = f"{base_url}{path}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx) as res:
            resp_body = res.read().decode()
            return res.status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        try:
            return e.code, json.loads(err_body)
        except:
            return e.code, err_body

print("=" * 70)
print("TrustFed AI — Phase 8 Live Deployed End-to-End Verification")
print("Target Backend:", base_url)
print("=" * 70)

# 1. System Health Check
code, res = api_call("/health")
print(f"\n[1] Health Check: HTTP {code}")
print(f"    Status: {res.get('status')}, Version: {res.get('version')}, DB: {res.get('database')}")
assert code == 200 and res.get("status") == "healthy"

# 2. Global Admin Role Flow
code, res = api_call("/api/v1/auth/login", method="POST", data={"email": "admin@trustfed.ai", "password": "password123"})
admin_token = res.get("token")
print(f"\n[2] Global Admin Login: HTTP {code}")
print(f"    Authenticated as: {res['user']['name']} (role: {res['user']['role']})")

code, res = api_call("/api/v1/dashboard/global", token=admin_token)
print(f"    Global Dashboard: HTTP {code}")
print(f"    Active Model: {res['currentModel']['version']}, Macro-F1: {res['currentModel']['macroF1']}, Total Encounters: {res['recordVolume']['totalEncounters']}")
assert code == 200

code, res = api_call("/api/v1/audit/verify", token=admin_token)
print(f"    Audit Ledger Verification: HTTP {code}")
print(f"    Ledger Intact: {res.get('valid')}, Chain Length: {res.get('chain_length')}")
assert code == 200

# 3. Regional Admin Role Flow
code, res = api_call("/api/v1/auth/login", method="POST", data={"email": "regional@trustfed.ai", "password": "password123"})
regional_token = res.get("token")
print(f"\n[3] Regional Admin Login: HTTP {code}")
print(f"    Authenticated as: {res['user']['name']} (hub_id: {res['user']['hubId']})")

code, res = api_call("/api/v1/dashboard/regional?hub_id=hub-east", token=regional_token)
print(f"    Regional Dashboard: HTTP {code}")
print(f"    Hub Name: {res['hub']['name']}, Eligible Hospitals: {res['eligibleHospitalsCount']}, Volume: {res['regionalRecordVolume']}")
assert code == 200

# 4. Doctor Role Flow
code, res = api_call("/api/v1/auth/login", method="POST", data={"email": "doctor@trustfed.ai", "password": "password123"})
doctor_token = res.get("token")
print(f"\n[4] Doctor Login: HTTP {code}")
print(f"    Authenticated as: {res['user']['name']} (role: {res['user']['role']}, hospital_id: {res['user']['hospitalId']})")

code, res = api_call("/api/v1/hospital/encounters?status=pending", token=doctor_token)
print(f"    Pending Confirmations Queue: HTTP {code}")
items = res.get("items", [])
print(f"    Pending Review Count: {len(items)}")
assert code == 200

# 5. Hospital Staff Role Flow (Intake & Prediction)
code, res = api_call("/api/v1/auth/login", method="POST", data={"email": "hospital@trustfed.ai", "password": "password123"})
staff_token = res.get("token")
print(f"\n[5] Hospital Staff Login: HTTP {code}")
print(f"    Authenticated as: {res['user']['name']} (hospital_id: {res['user']['hospitalId']})")

code, res = api_call("/api/v1/clinical/predict", method="POST", data={
    "age": 52,
    "sex": "M",
    "symptoms": ["chest_pain", "breathlessness", "fatigue"],
    "symptom_duration_days": 2,
    "vitals": {
        "temp_c": 37.1,
        "bp_sys": 142,
        "bp_dia": 92,
        "hr": 96,
        "spo2": 95.0,
        "resp_rate": 20,
        "blood_sugar": 128
    },
    "structured_ecg_finding": "normal",
    "optional_labs": {"platelets": 220, "wbc": 7.5}
}, token=staff_token)
print(f"    Differential AI Prediction: HTTP {code}")
top_cond = res["predictedTop3"][0]
print(f"    Top-1 Condition: {res['topCondition']} ({res['topConfidence']*100:.1f}%)")
print(f"    Remedy Disclaimer: '{res['suggestedClinicalGuidance']['verificationNotice']}'")
print(f"    Mandatory Notice: '{res['disclaimer']}'")
assert code == 200 and len(res["predictedTop3"]) == 3

# 6. Security Tenancy Verification
print("\n[6] Security & Tenancy Re-Test:")
# A. Staff blocked from Global Admin dashboard
code, res = api_call("/api/v1/dashboard/global", token=staff_token)
print(f"    Staff -> Global Dashboard: HTTP {code} ({res.get('detail')})")
assert code == 403

# B. Staff blocked from accessing another hospital's dashboard
code, res = api_call("/api/v1/dashboard/hospital?hospital_id=hosp-fl-2", token=staff_token)
print(f"    Staff -> Cross-Hospital Dashboard: HTTP {code} ({res.get('detail')})")
assert code == 403

# C. Staff blocked from Doctor Confirmation endpoint
code, res = api_call("/api/v1/hospital/encounters/1/confirm", method="POST", data={
    "confirmed_diagnosis": "heart_disease",
    "cause": "test",
    "treatment": "test"
}, token=staff_token)
print(f"    Staff -> Doctor Confirm Endpoint: HTTP {code} ({res.get('detail')})")
assert code == 403

# D. Unauthenticated access blocked
code, res = api_call("/api/v1/dashboard/hospital?hospital_id=1")
print(f"    Unauthenticated API Request: HTTP {code} ({res.get('detail')})")
assert code == 401

print("\n" + "=" * 70)
print("ALL LIVE PRODUCTION VERIFICATION CHECKS PASSED (100% SUCCESS)")
print("=" * 70)
