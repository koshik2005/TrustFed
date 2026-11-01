"""Locust Load Test Suite for TrustFed API.

Simulates 50 concurrent clinical & public users querying:
- /ready & /health
- /prediction/predict (Heart risk prediction with SHAP)
- /clinical/predict (18-disease calibrated differential diagnosis)
- /prediction/metrics
"""
import os
import sys
from locust import HttpUser, task, between, events

# Ensure backend modules can be imported to generate signed tokens
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
os.environ["SECRET_KEY"] = os.getenv("SECRET_KEY", "load-test-secret-key-32-chars-long-2026")
from services import auth


class TrustFedUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        """Generate authenticated session token for doctor / clinical role."""
        token = auth.create_token({
            "sub": "doctor@trustfed.ai",
            "role": "doctor",
            "hospital_id": "1",
            "user_id": 2
        }, ttl=7200)
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    @task(3)
    def test_ready_endpoint(self):
        self.client.get("/ready", name="/ready")

    @task(3)
    def test_health_endpoint(self):
        self.client.get("/health", name="/health")

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
        self.client.post("/prediction/predict", json=payload, headers=self.headers, name="/prediction/predict")

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
        self.client.post("/clinical/predict", json=payload, headers=self.headers, name="/clinical/predict")

    @task(2)
    def test_metrics_endpoint(self):
        self.client.get("/metrics", name="/metrics")
