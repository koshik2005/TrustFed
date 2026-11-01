"""Phase F Test Suite: Public Legal Pages & Regulatory Compliance Verification.

Tests:
1. Public Accessibility: Endpoints accessible without authentication tokens (crawlable/public).
2. All documents marked 'DRAFT, pending legal review'.
3. Privacy policy reflects informational mode (anonymous metrics only), essential cookies only,
   and clinical mode clearly marked 'not active'.
4. Medical disclaimer contains emergency guidance (112, 911, 999) and 'pending physician review' labels.
5. Contact / Grievance endpoint returns Indian Nodal Grievance Officer details and 15-day resolution timeline.
6. Intended use endpoint details who it is for, what it is not for, and emergency instructions.
7. Verification that NO DPDP, HIPAA, or medical-device compliance claims are made.
"""
from __future__ import annotations
import os
import sys
import pytest
from fastapi.testclient import TestClient

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestPublicLegalEndpoints:
    """Verifies that legal and transparency endpoints are publicly available and compliant with Phase F."""

    def test_terms_of_use_public_endpoint(self, client):
        resp = client.get("/api/v1/legal/terms")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["document"] == "Terms of Use"
        assert "DRAFT, pending legal review" in data["review_status"]
        assert "Educational decision support" in data["disclaimer"]
        assert "Non-Diagnostic Prototype" in data["content"]
        assert "Acceptance of Terms" in data["content"]

    def test_privacy_policy_public_endpoint(self, client):
        resp = client.get("/api/v1/legal/privacy")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["document"] == "Privacy Policy"
        assert "DRAFT, pending legal review" in data["review_status"]
        # Essential cookies only statement
        assert "essential" in data["cookie_policy"].lower()
        assert "zero tracking" in data["cookie_policy"].lower()
        # Content checks
        content = data["content"]
        assert "Informational Mode" in content
        assert "What We Collect" in content
        assert "What We Do NOT Collect" in content
        assert "NO Patient Names" in content
        assert "NOT ACTIVE" in content
        assert "Clinical Mode: Planned Architecture" in content

    def test_medical_disclaimer_public_endpoint(self, client):
        resp = client.get("/api/v1/legal/disclaimer")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["document"] == "Medical Disclaimer"
        assert "DRAFT, pending legal review" in data["review_status"]
        content = data["content"]
        assert "112" in content
        assert "911" in content
        assert "999" in content
        assert "Pending Physician Review" in content
        assert "No Doctor-Patient Relationship" in content or "No Patient-Physician Relationship" in content

    def test_grievance_policy_public_endpoint(self, client):
        resp = client.get("/api/v1/legal/grievance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "Grievance" in data["document"]
        assert "DRAFT, pending legal review" in data["review_status"]
        officer = data["grievance_officer"]
        assert "Rajesh V. Sharma" in officer["name"]
        assert "Nodal Grievance Redressal" in officer["designation"]
        assert officer["email"] == "grievance-officer@trustfed.ai"
        assert "Bengaluru, Karnataka" in officer["address"]
        assert officer["acknowledgment_hours"] <= 48
        assert officer["resolution_days"] <= 15

    def test_intended_use_public_endpoint(self, client):
        resp = client.get("/api/v1/legal/intended-use")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["document"] == "Intended Use Specification"
        assert "DRAFT, pending legal review" in data["review_status"]
        content = data["content"]
        assert "Who It Is For" in content
        assert "What It Is NOT For" in content
        assert "112" in content
        assert "NOT for Primary Diagnosis" in content or "NOT for Primary Medical Diagnosis" in content

    def test_no_unsupported_statutory_compliance_claims(self, client):
        """Phase F rule: Do NOT claim DPDP, HIPAA, or medical-device compliance anywhere."""
        for endpoint in ["/api/v1/legal/terms", "/api/v1/legal/privacy", "/api/v1/legal/disclaimer", "/api/v1/legal/intended-use"]:
            resp = client.get(endpoint)
            content = resp.json()["content"]
            # Ensure it does NOT claim "HIPAA compliant", "DPDP compliant", or "certified medical device"
            assert "HIPAA compliant" not in content
            assert "DPDP compliant" not in content
            assert "certified medical device" not in content.lower()

