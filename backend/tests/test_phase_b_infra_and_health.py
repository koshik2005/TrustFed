"""Tests for Phase B: Infrastructure, /ready, /health, Latency Metrics, and Performance Indexes."""
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy import text

os.environ["SECRET_KEY"] = "phase-b-test-secret-key-32-chars-long!"
os.environ["ENVIRONMENT"] = "development"

from main import app
from db.database import engine, Base, SessionLocal
from db.migrations.v3_performance_indexes import migrate_up, migrate_down, INDEXES
from core.metrics import LatencyTracker, predict_latency_tracker
from api.v1.routes import get_cached_active_model, invalidate_active_model_cache
from services import auth

client = TestClient(app)


def test_health_endpoint_is_clean_and_free_of_sensitive_data():
    """Verify that /health reports liveness without leaking passwords, hostnames, or traces."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "version" in data
    assert "mode" in data
    # Sensitive field checks
    assert "password" not in str(data).lower()
    assert "traceback" not in str(data).lower()
    assert "exception" not in str(data).lower()


def test_health_endpoint_handles_db_failure_without_leaking_exception():
    """When DB query fails, /health should report degraded/disconnected without raw exception details."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = RuntimeError("FATAL: password authentication failed for user postgres at 10.0.0.1")

    from main import health
    result = health(db=mock_db)
    assert result["status"] == "degraded"
    assert result["database"] == "disconnected"
    assert "password" not in str(result).lower()
    assert "10.0.0.1" not in str(result)


def test_ready_endpoint_healthy():
    """When DB and models are loaded, /ready returns HTTP 200 with status=ready."""
    res = client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert data["model"] == "loaded"
    assert data["version"] == "2.1.1"


def test_ready_endpoint_db_failure():
    """When DB fails, /ready returns HTTP 503 and status=not_ready."""
    from main import readiness_check
    from fastapi import Response

    mock_db = MagicMock()
    mock_db.execute.side_effect = ConnectionError("Could not connect to host")
    response = Response()

    result = readiness_check(response=response, db=mock_db)
    assert response.status_code == 503
    assert result["status"] == "not_ready"
    assert result["database"] == "disconnected"


def test_ready_endpoint_model_failure():
    """When model is not loaded, /ready returns HTTP 503."""
    from main import readiness_check
    from fastapi import Response

    mock_db = MagicMock()
    mock_db.execute.return_value = None
    response = Response()

    with patch("services.general_disease_model.get_model", side_effect=Exception("Model missing")):
        result = readiness_check(response=response, db=mock_db)
        assert response.status_code == 503
        assert result["status"] == "not_ready"
        assert result["model"] == "not_loaded"


def test_latency_tracker_percentiles():
    """Verify p50, p95, and p99 percentile calculation in LatencyTracker."""
    tracker = LatencyTracker(max_samples=100)
    # Add 100 measurements: 1ms to 100ms
    for i in range(1, 101):
        tracker.record(float(i), is_error=False)

    metrics = tracker.get_metrics()
    assert metrics["sample_count"] == 100
    assert metrics["total_requests"] == 100
    assert metrics["error_rate"] == 0.0
    # p50 should be around 50.5
    assert 49.0 <= metrics["p50_ms"] <= 52.0
    # p95 should be around 95
    assert 94.0 <= metrics["p95_ms"] <= 96.0
    # p99 should be around 99
    assert 98.0 <= metrics["p99_ms"] <= 100.0


def test_metrics_endpoint():
    """Verify /metrics and /api/prediction/metrics require global_admin or internal token."""
    from core.metrics_auth import get_internal_metrics_token

    valid_token = get_internal_metrics_token()

    # 1. Unauthenticated request rejected with 401
    unauth = client.get("/metrics")
    assert unauth.status_code == 401, f"Expected 401, got {unauth.status_code}"
    assert "Authentication required" in unauth.json()["detail"]

    # 2. Rotated/deprecated committed token is rejected with 401
    deprecated_res = client.get("/metrics", headers={"X-Internal-Token": "trustfed-internal-metrics-secret"})
    assert deprecated_res.status_code == 401
    assert "Invalid internal metrics token" in deprecated_res.json()["detail"]

    # 3. Access with valid internal token succeeds
    res_internal = client.get("/metrics", headers={"X-Internal-Token": valid_token})
    assert res_internal.status_code == 200
    data = res_internal.json()
    assert data["status"] == "ok"
    assert "prediction_latency" in data
    assert "p50_ms" in data["prediction_latency"]
    assert "p95_ms" in data["prediction_latency"]
    assert "p99_ms" in data["prediction_latency"]

    # 4. Non-global_admin user (e.g. doctor) is forbidden (403)
    doc_tok = auth.create_token({"sub": "doc@trustfed.ai", "role": "doctor", "user_id": 1})
    res_doctor = client.get("/metrics", headers={"Authorization": f"Bearer {doc_tok}"})
    assert res_doctor.status_code == 403
    assert "global_admin" in res_doctor.json()["detail"]

    # 5. Global admin user succeeds (200)
    admin_tok = auth.create_token({"sub": "admin@trustfed.ai", "role": "global_admin", "user_id": 99})
    res_admin = client.get("/metrics", headers={"Authorization": f"Bearer {admin_tok}"})
    assert res_admin.status_code == 200

    # 6. /api/v1/prediction/metrics route is equally restricted
    res_pred_unauth = client.get("/api/v1/prediction/metrics")
    assert res_pred_unauth.status_code == 401
    res_pred_doc = client.get("/api/v1/prediction/metrics", headers={"Authorization": f"Bearer {doc_tok}"})
    assert res_pred_doc.status_code == 403
    res_pred_tok = client.get("/api/v1/prediction/metrics", headers={"X-Internal-Token": valid_token})
    assert res_pred_tok.status_code == 200


def test_internal_metrics_token_production_startup_validation():
    """Verify backend startup refuses to run in production if INTERNAL_METRICS_TOKEN is missing or insecure."""
    from core.metrics_auth import validate_internal_metrics_token_on_startup
    import pytest

    # 1. Missing in production -> Refuse
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "INTERNAL_METRICS_TOKEN": ""}):
        with pytest.raises(RuntimeError, match="INTERNAL_METRICS_TOKEN environment variable is required in production"):
            validate_internal_metrics_token_on_startup()

    # 2. Deprecated committed default in production -> Refuse
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "INTERNAL_METRICS_TOKEN": "trustfed-internal-metrics-secret"}):
        with pytest.raises(RuntimeError, match="insecure, too short.*or matches a deprecated token"):
            validate_internal_metrics_token_on_startup()

    # 3. Too short token in production -> Refuse
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "INTERNAL_METRICS_TOKEN": "short-secret-123"}):
        with pytest.raises(RuntimeError, match="insecure, too short"):
            validate_internal_metrics_token_on_startup()

    # 4. Valid high-entropy token in production -> Passes cleanly
    valid_prod_token = "K9x_v2N7qL4wP8jZ1bC5aA3fG0dE6hI8"
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "INTERNAL_METRICS_TOKEN": valid_prod_token}):
        validate_internal_metrics_token_on_startup()  # Should not raise


def test_model_cache_avoids_repeated_disk_io():
    """Verify that get_cached_active_model caches the model in memory."""
    db = SessionLocal()
    try:
        invalidate_active_model_cache()
        s1, m1, f1 = get_cached_active_model(db)
        assert m1 is not None

        # Subsequent call should return the exact same object reference without reading disk
        s2, m2, f2 = get_cached_active_model(db)
        assert m1 is m2
        assert s1.session_id == s2.session_id
    finally:
        db.close()


def test_v3_performance_indexes_migration_up_and_down():
    """Verify that v3 indexes migrate up and down cleanly without data loss."""
    # 1. Migrate up
    applied = migrate_up(engine)
    assert len(applied) == len(INDEXES)

    # 2. Re-applying is idempotent
    applied_again = migrate_up(engine)
    assert len(applied_again) == len(INDEXES)

    # 3. Migrate down
    dropped = migrate_down(engine)
    assert len(dropped) == len(INDEXES)

    # 4. Restore indexes
    restored = migrate_up(engine)
    assert len(restored) == len(INDEXES)


def test_restore_drill_execution():
    """Verify that restore_drill logic runs cleanly and matches all tables."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
    from restore_drill import run_sqlite_restore_drill
    assert run_sqlite_restore_drill() is True
