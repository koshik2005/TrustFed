"""Phase D: CI/CD, Monitoring, and PHI Log Scrubbing Test Suite.

Verifies:
1. Structured logs include correlation request IDs matching X-Request-ID headers.
2. PHI log redaction scrubs patient names, phone numbers, patient identifiers, and tokens.
3. Model monitoring tracks active versions, top-3 confidence distribution, and red-flag override share.
4. Drift detection triggers alerts when top-1 confidence drops or red-flag overrides exceed thresholds.
5. Sentry pre-send scrubber sanitizes events prior to ingestion.
"""
from __future__ import annotations
import datetime
import io
import json
import logging
import pytest
from fastapi.testclient import TestClient

from db.database import SessionLocal, engine
from db import models
from services import auth
from core.logging_config import (
    redact_phi_text,
    PHIRedactionFilter,
    JSONLogFormatter,
    before_send_scrubber,
    request_id_ctx
)
from core.model_monitoring import ModelMonitoringService
from main import app

client = TestClient(app)


def _get_admin_headers():
    db = SessionLocal()
    try:
        u = db.query(models.User).filter_by(email="admin_phased@trustfed.ai").first()
        if not u:
            u = models.User(
                email="admin_phased@trustfed.ai",
                name="Admin Phase D",
                role="global_admin",
                password_hash=auth.hash_password("Pass123!SecurePhaseD"),
                status="active"
            )
            db.add(u)
            db.commit()
    finally:
        db.close()

    res = client.post("/api/v1/auth/login", json={"email": "admin_phased@trustfed.ai", "password": "Pass123!SecurePhaseD"})
    return {"Authorization": f"Bearer {res.json()['token']}"}


# ── 1. Structured Logging with Request IDs & Zero PHI ────────────────────────

def test_request_id_header_and_correlation():
    """Verify that requests receive an X-Request-ID header and propagate into request context."""
    # Custom request ID
    custom_id = "req-custom-audit-12345"
    res1 = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res1.status_code == 200
    assert res1.headers.get("X-Request-ID") == custom_id

    # Auto-generated request ID (UUID)
    res2 = client.get("/health")
    assert res2.status_code == 200
    generated_id = res2.headers.get("X-Request-ID")
    assert generated_id is not None
    assert len(generated_id) >= 16


def test_phi_log_redaction_scrubs_all_identifiers():
    """Verify that redact_phi_text removes patient identifiers, phone numbers, and bearer tokens."""
    raw_log = (
        "Encounter created for patient_name='Eleanor Vance' with ID PT-88291, "
        "contact phone +1-555-0199 or 415-555-2671. "
        "Authorization header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.secret_sig"
    )

    scrubbed = redact_phi_text(raw_log)

    # Assert all sensitive elements are redacted
    assert "Eleanor Vance" not in scrubbed
    assert "[REDACTED_NAME]" in scrubbed
    assert "PT-88291" not in scrubbed
    assert "[REDACTED_PATIENT_ID]" in scrubbed
    assert "+1-555-0199" not in scrubbed
    assert "415-555-2671" not in scrubbed
    assert "[REDACTED_PHONE]" in scrubbed
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in scrubbed
    assert "Bearer [REDACTED_TOKEN]" in scrubbed or "[REDACTED_JWT]" in scrubbed


def test_json_formatter_includes_request_id_and_sanitizes():
    """Verify JSONLogFormatter outputs valid JSON containing request_id and sanitized message."""
    formatter = JSONLogFormatter()
    logger = logging.getLogger("test_phi_logger")
    logger.setLevel(logging.INFO)

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)
    handler.addFilter(PHIRedactionFilter())
    logger.addHandler(handler)

    try:
        # Set request_id in context
        token = request_id_ctx.set("corr-id-998877")
        try:
            logger.info("Patient PT-99123 called phone 555-883-9921 with token Bearer secret-token-xyz")
        finally:
            request_id_ctx.reset(token)

        output_line = stream.getvalue().strip()
        data = json.loads(output_line)

        assert data["request_id"] == "corr-id-998877"
        assert data["level"] == "INFO"
        assert "PT-99123" not in data["message"]
        assert "555-883-9921" not in data["message"]
        assert "secret-token-xyz" not in data["message"]
        assert "[REDACTED_PATIENT_ID]" in data["message"]
        assert "[REDACTED_PHONE]" in data["message"]
    finally:
        logger.removeHandler(handler)


# ── 2. Model Monitoring & Distribution Drift Alerts ──────────────────────────

def test_model_monitoring_report_structure():
    """Verify GET /api/v1/model/monitoring returns complete distribution and drift structure."""
    res = client.get("/api/v1/model/monitoring")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "summary" in data
    assert "confidence_distribution" in data
    assert "daily_metrics" in data
    assert "drift_status" in data
    assert "thresholds" in data["drift_status"]


def test_model_monitoring_service_records_inferences_and_bins():
    """Verify that ModelMonitoringService records top-3 confidences and updates histogram bins."""
    svc = ModelMonitoringService()

    # Record 4 inferences with varying confidences
    svc.record_inference(model_version="v2.0", top3_confidences=[0.95, 0.04, 0.01], has_red_flag=False)
    svc.record_inference(model_version="v2.0", top3_confidences=[0.82, 0.12, 0.06], has_red_flag=False)
    svc.record_inference(model_version="v2.0", top3_confidences=[0.61, 0.25, 0.14], has_red_flag=True, is_red_flag_overridden=True)
    svc.record_inference(model_version="v2.0", top3_confidences=[0.38, 0.35, 0.27], has_red_flag=True, is_red_flag_overridden=False)

    report = svc.get_monitoring_report()
    summary = report["summary"]

    assert summary["total_inferences"] == 4
    assert summary["total_red_flags"] == 2
    assert summary["red_flag_overrides"] == 1
    assert summary["red_flag_override_share"] == 0.50

    bins = report["confidence_distribution"]
    assert bins["very_high (>=0.90)"] == 1
    assert bins["high (0.70-0.90)"] == 1
    assert bins["medium (0.50-0.70)"] == 1
    assert bins["low (<0.50)"] == 1


def test_model_monitoring_drift_alert_triggers_on_low_confidence():
    """Verify that drift detection triggers a CRITICAL alert when mean top-1 confidence collapses."""
    svc = ModelMonitoringService(thresholds={"min_top1_mean_confidence": 0.50, "min_inferences_for_alert": 5})

    # Simulate 6 low confidence inferences (mean = 0.35 < 0.50)
    for _ in range(6):
        svc.record_inference(model_version="v2.0", top3_confidences=[0.35, 0.33, 0.32])

    report = svc.get_monitoring_report()
    drift = report["drift_status"]

    assert drift["has_alerts"] is True
    assert drift["alert_count"] >= 1
    crit_alert = next((a for a in drift["alerts"] if a["metric"] == "top1_mean_confidence"), None)
    assert crit_alert is not None
    assert crit_alert["severity"] == "CRITICAL"
    assert "dropped below safety threshold" in crit_alert["message"]


def test_model_monitoring_drift_alert_triggers_on_excessive_red_flag_overrides():
    """Verify that drift detection triggers a WARNING when red-flag override rate exceeds 30%."""
    svc = ModelMonitoringService(thresholds={"max_red_flag_override_share": 0.30, "min_inferences_for_alert": 5})

    # Simulate 10 red flags where 5 are overridden (50% > 30% threshold)
    for i in range(10):
        svc.record_inference(
            model_version="v2.0",
            top3_confidences=[0.85, 0.10, 0.05],
            has_red_flag=True,
            is_red_flag_overridden=(i < 5)
        )

    report = svc.get_monitoring_report()
    drift = report["drift_status"]

    assert drift["has_alerts"] is True
    rf_alert = next((a for a in drift["alerts"] if a["metric"] == "red_flag_override_share"), None)
    assert rf_alert is not None
    assert rf_alert["severity"] == "WARNING"
    assert "exceeded safety threshold" in rf_alert["message"]


# ── 3. Sentry PHI Scrubber Event Ingestion ───────────────────────────────────

def test_sentry_before_send_scrubber_sanitizes_events():
    """Verify that before_send_scrubber scrubs URLs, headers, and breadcrumbs before sending to Sentry."""
    raw_event = {
        "logentry": {"message": "Database query failed for patient PT-10022 and phone 555-444-2222"},
        "request": {
            "url": "https://api.trustfed.ai/patients/PT-10022",
            "headers": {
                "Authorization": "Bearer secret-token-abcdef",
                "Cookie": "tf_refresh_token=secret-cookie-xyz",
                "Accept": "application/json"
            }
        },
        "breadcrumbs": {
            "values": [
                {"message": "Encounter created with name='Dr. Sarah' and patient PT-10022"}
            ]
        }
    }

    scrubbed = before_send_scrubber(raw_event, {})

    # Check request URL
    assert "PT-10022" not in scrubbed["request"]["url"]
    assert "[REDACTED_PATIENT_ID]" in scrubbed["request"]["url"]

    # Check sensitive headers
    assert scrubbed["request"]["headers"]["Authorization"] == "[REDACTED_HEADER]"
    assert scrubbed["request"]["headers"]["Cookie"] == "[REDACTED_HEADER]"
    assert scrubbed["request"]["headers"]["Accept"] == "application/json"

    # Check log message
    assert "PT-10022" not in scrubbed["logentry"]["message"]
    assert "555-444-2222" not in scrubbed["logentry"]["message"]

    # Check breadcrumbs
    assert "PT-10022" not in scrubbed["breadcrumbs"]["values"][0]["message"]


def test_sentry_test_endpoint_serves_scrubbed_sample():
    """Verify GET /api/v1/monitoring/sentry-test returns 200 with scrubbed verification payload."""
    res = client.get("/api/v1/monitoring/sentry-test")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "sentry_dsn_configured" in data
    assert "scrubbed_sample" in data
    sample = data["scrubbed_sample"]
    assert "[REDACTED_PATIENT_ID]" in sample["request"]["url"]
    assert sample["request"]["headers"]["Authorization"] == "[REDACTED_HEADER]"

