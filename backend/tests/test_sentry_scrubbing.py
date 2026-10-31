"""Test suite & live demonstration for Sentry Error Monitoring PHI Scrubber."""
import pytest
from core.logging_config import before_send_scrubber, redact_phi_text


def test_sentry_phi_scrubber_removes_identifiers():
    """Verify that sensitive patient identifiers, tokens, and headers are thoroughly scrubbed
    before an event could ever be transmitted to Sentry."""
    raw_event = {
        "event_id": "9ec0d381b1624b9da88b1f7e91234567",
        "level": "error",
        "logentry": {
            "message": "Error processing patient PT-847291 (contact: +1-555-019-2831, email: patient.doe@hospital.org) with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token"
        },
        "request": {
            "url": "https://trustfed-backend.onrender.com/api/v1/hospital/patients/PT-847291/records",
            "headers": {
                "Authorization": "Bearer sensitive_token_xyz_123",
                "Cookie": "tf_refresh_token=sensitive_cookie_abc_456",
                "X-CSRF-Token": "csrf_secret_789",
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        },
        "breadcrumbs": {
            "values": [
                {
                    "category": "auth",
                    "message": "Authenticated user initiated clinical intake for PT-847291 (phone: +91 98765 43210)"
                },
                {
                    "category": "query",
                    "message": "Fetched encrypted encounter records for patient PT-847291"
                }
            ]
        }
    }

    scrubbed = before_send_scrubber(raw_event, {})

    # 1. Verify logentry message is scrubbed
    msg = scrubbed["logentry"]["message"]
    assert "PT-847291" not in msg
    assert "[REDACTED_PATIENT_ID]" in msg
    assert "+1-555-019-2831" not in msg
    assert "[REDACTED_PHONE]" in msg
    assert "Bearer [REDACTED_TOKEN]" in msg

    # 2. Verify URL is scrubbed
    url = scrubbed["request"]["url"]
    assert "PT-847291" not in url
    assert "[REDACTED_PATIENT_ID]" in url

    # 3. Verify sensitive headers are scrubbed
    headers = scrubbed["request"]["headers"]
    assert headers["Authorization"] == "[REDACTED_HEADER]"
    assert headers["Cookie"] == "[REDACTED_HEADER]"
    assert headers["X-CSRF-Token"] == "[REDACTED_HEADER]"
    assert headers["Accept"] == "application/json"

    # 4. Verify breadcrumbs are scrubbed
    for bc in scrubbed["breadcrumbs"]["values"]:
        assert "PT-847291" not in bc["message"]
        assert "[REDACTED_PATIENT_ID]" in bc["message"]


if __name__ == "__main__":
    test_sentry_phi_scrubber_removes_identifiers()
    print("Sentry PHI Scrubber test passed successfully!")

