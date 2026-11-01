"""Locust Load Test Suite for TrustFed API.

Simulates 50 concurrent clinical & public users querying:
- /ready & /health
- /api/v1/clinical/symptoms
- /api/v1/prediction/predict (Heart risk prediction with SHAP)
- /api/v1/clinical/predict (18-disease calibrated differential diagnosis)
- /metrics
"""
import os
import sys
import threading
import requests
from locust import HttpUser, task, between

# Shared token cache so virtual users do not hammer /login
_TOKEN_LOCK = threading.Lock()
_CACHED_TOKEN = None


class TrustFedUser(HttpUser):
    wait_time = between(0.2, 0.8)

    def on_start(self):
        global _CACHED_TOKEN
        # Each simulated client user gets an isolated simulated IP to prevent artificial rate-limit collapse
        self.user_ip = f"198.51.100.{(id(self) % 250) + 1}"

        with _TOKEN_LOCK:
            if not _CACHED_TOKEN:
                login_url = f"{self.host.rstrip('/')}/api/v1/auth/login"
                try:
                    resp = requests.post(
                        login_url,
                        json={"email": "admin@trustfed.ai", "password": "TrustFed2026!SecAdmin"},
                        headers={"Content-Type": "application/json"},
                        timeout=15
                    )
                    if resp.status_code == 200:
                        _CACHED_TOKEN = resp.json().get("token")
                except Exception as e:
                    print(f"[WARN] Remote login failed: {e}")

                if not _CACHED_TOKEN:
                    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
                    from services import auth
                    _CACHED_TOKEN = auth.create_token({
                        "sub": "admin@trustfed.ai",
                        "role": "global_admin",
                        "hospital_id": "1",
                        "user_id": 1
                    }, ttl=7200)

        internal_tok = os.getenv("INTERNAL_METRICS_TOKEN", "")
        self.headers = {
            "Authorization": f"Bearer {_CACHED_TOKEN}",
            "Content-Type": "application/json",
            "X-Internal-Token": internal_tok,
            "X-Forwarded-For": self.user_ip
        }

    @task(3)
    def test_ready_endpoint(self):
        self.client.get("/ready", headers=self.headers, name="/ready")

    @task(3)
    def test_health_endpoint(self):
        self.client.get("/health", headers=self.headers, name="/health")

    @task(3)
    def test_clinical_symptoms(self):
        self.client.get("/api/v1/clinical/symptoms", headers=self.headers, name="/api/v1/clinical/symptoms")

    @task(5)
    def test_cardiac_prediction(self):
        payload = {
            "age": 58,
            "sex": 1,
            "chestPainType": 2,
            "restingBP": 135,
            "cholesterol": 230,
            "fastingBloodSugar": 0,
            "restingECG": 1,
            "maxHeartRate": 145,
            "exerciseAngina": 0,
            "oldPeak": 1.4,
            "slope": 2,
            "ca": 0,
            "thal": 3
        }
        self.client.post("/api/v1/prediction/predict", json=payload, headers=self.headers, name="/api/v1/prediction/predict")

    @task(5)
    def test_clinical_differential(self):
        payload = {
            "age": 45,
            "sex": 1,
            "symptoms": ["fever", "cough", "fatigue"],
            "symptom_duration_days": 3,
            "vitals": {
                "temperature": 38.6,
                "heart_rate": 86,
                "spo2": 97.0,
                "bp_systolic": 125.0,
                "bp_dia": 82.0
            },
            "optional_labs": {
                "wbc": 6.8,
                "platelets": 210.0
            }
        }
        self.client.post("/api/v1/clinical/predict", json=payload, headers=self.headers, name="/api/v1/clinical/predict")

    @task(2)
    def test_metrics_endpoint(self):
        self.client.get("/metrics", headers=self.headers, name="/metrics")
