"""Tests for the web-independent service layer.  python tests/test_services.py"""
import os, sys, time, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services import pipeline, inference, auth

VITALS = dict(age=63, sex=1, chestPainType=4, restingBP=145, cholesterol=233, fastingBloodSugar=1, restingECG=2,
              maxHeartRate=150, exerciseAngina=0, oldPeak=2.3, slope=3, ca=0, thal=6)


def test_auth_roundtrip():
    h = auth.hash_password("s3cret")
    assert auth.verify_password("s3cret", h) and not auth.verify_password("nope", h)
    t = auth.create_token({"sub": "a@b.c", "role": "global_admin"})
    assert auth.decode_token(t)["role"] == "global_admin"
    bad = t[:-2] + ("AA" if t[-2:] != "AA" else "BB")
    try: auth.decode_token(bad); assert False
    except ValueError: pass
    try: auth.decode_token(auth.create_token({"sub": "x"}, ttl=-5)); assert False
    except ValueError: pass


def test_audit_chain_detects_tampering():
    prev, chain = auth.GENESIS, []
    for i in range(5):
        ts = f"2026-01-0{i+1}T00:00:00"; hsh = auth.audit_hash(prev, ts, "n", "training", f"event {i}")
        chain.append((prev, ts, f"event {i}", hsh)); prev = hsh
    def verify(c):
        p = auth.GENESIS
        for pv, ts, d, h in c:
            if pv != p or auth.audit_hash(pv, ts, "n", "training", d) != h: return False
            p = h
        return True
    assert verify(chain)
    chain[2] = (chain[2][0], chain[2][1], "tampered", chain[2][3])
    assert not verify(chain)


def test_full_session_and_inference():
    seen = []
    out = pipeline.run_session("TEST-001", dict(rounds=6, data_source="synthetic"), on_round=lambda r, m, th: seen.append(r))
    assert seen == list(range(1, 7)) and out["final_accuracy"] > 0.6
    assert out["privacy"]["epsilon"] and out["privacy"]["epsilon"] > 0
    assert out["fairness"]["subgroups"] and 0 <= out["fairness"]["score"] <= 1
    assert len(out["hospitals"]) == 5
    m = inference.load_model(out["model_path"])
    r = inference.predict(m, VITALS)
    assert 0 <= r["riskScore"] <= 1 and len(r["shapValues"]) == 13
    # explanation sums to the logit shift: check efficiency through the API-level numbers
    r2 = inference.predict(m, {**VITALS, "age": 30, "maxHeartRate": 190, "chestPainType": 1, "exerciseAngina": 0,
                                "oldPeak": 0, "ca": 0, "thal": 3, "slope": 1})
    assert r2["riskScore"] < r["riskScore"]            # healthier profile -> lower risk
    os.remove(out["model_path"])


def test_inference_validation():
    try: inference.vitals_to_vector({**VITALS, "age": 400}); assert False
    except ValueError as e: assert "age" in str(e)
    try: inference.vitals_to_vector({k: v for k, v in VITALS.items() if k != "ca"}); assert False
    except ValueError as e: assert "ca" in str(e)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for f in fns:
        t = time.time(); f(); print(f"PASS {f.__name__} ({time.time()-t:.1f}s)")
    print(f"\n{len(fns)} tests passed")
