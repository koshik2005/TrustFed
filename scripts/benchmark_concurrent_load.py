import sys
import os
import time
import statistics
import concurrent.futures

backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from main import app
from services import auth

def main():
    client = TestClient(app)
    token = auth.create_token({
        "sub": "doctor@trustfed.ai",
        "role": "doctor",
        "hospital_id": "hosp-1"
    })
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "age": 45,
        "sex": 1,
        "symptoms": ["cough", "fever", "headache"],
        "vitals": {"spo2": 97, "temp_c": 37.5}
    }

    # Warm-up request
    client.post("/api/v1/clinical/predict", headers=headers, json=payload)

    def do_request(_):
        t0 = time.perf_counter()
        resp = client.post("/api/v1/clinical/predict", headers=headers, json=payload)
        lat = (time.perf_counter() - t0) * 1000.0
        return resp.status_code, lat

    print("Running 50 concurrent workers benchmark (200 clinical differential inferences)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(do_request, range(200)))

    statuses = [r[0] for r in results]
    lats = sorted([r[1] for r in results])
    p50 = statistics.median(lats)
    p95 = lats[int(0.95 * len(lats))]
    p99 = lats[int(0.99 * len(lats))]

    print("=" * 60)
    print("CONCURRENT LOAD BENCHMARK (50 WORKERS, 200 REQUESTS)")
    print("=" * 60)
    print(f"Total Requests:     {len(results)}")
    print(f"Success Count:      {statuses.count(200)} / {len(results)} ({statuses.count(200)/len(results)*100:.1f}%)")
    print(f"Error Rate:         {(len(results) - statuses.count(200)) / len(results) * 100:.2f}%")
    print(f"Latency p50:        {p50:.2f} ms")
    print(f"Latency p95:        {p95:.2f} ms")
    print(f"Latency p99:        {p99:.2f} ms")
    print(f"Target (< 500 ms):  {'PASS' if p95 < 500.0 else 'FAIL'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
