# TrustFed-Health Threat Model & OWASP Top 10 Verification

**Document Version:** 2.0.0  
**Last Updated:** November 2026  
**Security Contact:** security@trustfed.ai  
**Standards Alignment:** RFC 9116, STRIDE Threat Modeling, OWASP Top 10 (2021), HIPAA Security Rule (45 CFR § 164.312), GDPR Article 32.

---

## 1. System Overview & Deployment Modes

TrustFed is a federated, role-based general-disease decision-support platform operating in a multi-tenant hierarchy:
- **Global Admin**: System orchestration, model lifecycle, regional hub provisioning, audit verification.
- **Regional Hub Admin**: Hub-scoped oversight, hospital provisioning, hospital node health.
- **Doctor**: Clinical consultation, patient encounter evaluation, prediction confirmation.
- **Hospital Staff**: Patient intake, demographic/symptom registration.

### Deployment Modes
1. **Informational Mode (Default)**:
   - For educational and clinical decision-support triage only.
   - Strictly prohibits storing patient names, contacts, or linkable identifiers.
   - Enforces persistent warning on all responses and pages: *"Educational decision support. Not medical advice. Not clinically validated. In an emergency call your local emergency number."*
   - Federation workflows and doctor confirmations are disabled.
2. **Clinical Mode**:
   - Production clinical operations requiring explicit operator activation (`APP_MODE=clinical`).
   - Requires verified managed database backups, MFA enforcement, MultiFernet encryption keys from secrets store, and default credential elimination.

---

## 2. Core Assets

| Asset ID | Asset Name | Description & Sensitivity | Protection Mechanisms |
|---|---|---|---|
| **AST-01** | **Protected Health Information (PHI)** | Patient names, contact details, diagnoses, symptoms, vitals. | Disallowed in Informational Mode. MultiFernet AES-128-CBC + HMAC-SHA256 encrypted at rest in Clinical Mode. Never transmitted across tenants. |
| **AST-02** | **Cryptographic Audit Ledger** | SHA-256 hash-chained immutable sequence of all security and clinical events. | Linear hashing with `prev_hash`, HMAC-SHA256 tamper-evident verification, single-worker/row-lock concurrency protection. |
| **AST-03** | **Federated Model Weights & Gradients** | Local hospital gradient updates and global aggregated model weights. | Differential Privacy (DP-SGD / Laplace noise with clipping $\le 1.0$), Secure Aggregation, cross-hospital isolation. |
| **AST-04** | **Authentication Credentials & MFA Secrets** | Password hashes (PBKDF2-SHA256, 100,000 rounds), TOTP base32 secrets, backup recovery hashes. | Encrypted TOTP secrets via MultiFernet; recovery codes stored as SHA-256 hashes (burned on single use); default passwords strictly prohibited at startup. |
| **AST-05** | **Session Tokens & Cookies** | JWT Access tokens, rotating refresh tokens (`jti`), CSRF tokens. | Key ID (`kid`) header validation, httpOnly/Secure/SameSite cookies, immediate token invalidation on soft-delete or suspension. |

---

## 3. Threat Actors & Capabilities

1. **External Opportunistic Attacker**: Internet-based adversary probing public APIs for exposed endpoints, injection flaws, default credentials, or denial of service.
2. **Compromised Hospital Insider (Hospital Staff)**: User possessing valid credentials attempting horizontal privilege escalation across patients or cross-hospital access.
3. **Malicious Clinical Doctor**: Doctor attempting to confirm fraudulent predictions or access other hospitals' confidential patient records.
4. **Rogue Regional Hub Admin**: Regional admin attempting to access hospitals outside their assigned geographic hub or escalate to Global Admin.
5. **Untrusted Host / Co-tenant**: Adversary attempting to inspect server memory, ephemeral containers, or cold-start persistence.

---

## 4. STRIDE Threat Analysis & Mitigations

### 4.1 Spoofing (Identity Deception)
* **Threat**: Attacker creates forged JWT tokens or uses leaked refresh tokens.
* **Mitigation**:
  - `backend/services/auth.py` enforces cryptographic verification of JWTs with `kid`-based secret lookup and fallback keyring validation.
  - Refresh tokens are stored in the database (`refresh_tokens` table) with unique `jti` and strict `revoked=False` check.
  - MFA (RFC 6238 TOTP) is enforced for high-privilege roles (`global_admin`, `regional_admin`, `doctor`).

### 4.2 Tampering (Data Manipulation)
* **Threat**: Tampering with clinical predictions, audit logs, or federated training updates.
* **Mitigation**:
  - `backend/services/store.py` implements a cryptographic hash chain (`prev_hash` $\to$ `hash`) for all audit events; any modification causes `verify_chain()` to fail.
  - Model weights validate layer dimensions, gradient clipping ($\le 1.0$), and finite number validation before aggregation in `backend/services/federated.py`.
  - Soft-delete tracking (`deleted_at`, `deleted_by`) prevents unlogged record destructions.

### 4.3 Repudiation (Denial of Actions)
* **Threat**: Admin deletes a hospital or user and denies performing the destructive action.
* **Mitigation**:
  - All admin actions (`delete_hub`, `delete_hospital`, `delete_user`, `admin_reset_mfa`) write an immediate tamper-evident entry to `AuditLog`.
  - The audit record includes the actor's authenticated email, role, target resource ID, and ISO timestamp.

### 4.4 Information Disclosure (Data Leakage)
* **Threat**: Patient data leakage across hospital boundaries or in Informational Mode.
* **Mitigation**:
  - Informational Mode rejects patient names/contacts with HTTP 422 before reaching the DB layer.
  - Multi-tenant query filtering: all queries filter by `hospital_id` or `hub_id`. Cross-tenant access returns HTTP 403.
  - Row Level Security (RLS) is enabled on all PostgreSQL public tables (`backend/db/migrations/enable_rls.py`).

### 4.5 Denial of Service (Service Exhaustion)
* **Threat**: Brute-force password guessing, flood of inference requests, or heavy federated training cycles.
* **Mitigation**:
  - SlowAPI rate limiting: default 120 req/min per IP, 20 req/min on `/auth/login`.
  - Per-account failed login lockout: 5 failed attempts in 5 minutes locks the account for 5 minutes (`ACCOUNT_LOCKOUT_MAX_ATTEMPTS = 5`).
  - Cached in-memory model instances pre-warmed at startup (`backend/main.py:lifespan`).

### 4.6 Elevation of Privilege (Unauthorized Capability Expansion)
* **Threat**: Hospital staff accesses regional hub management or doctor diagnosis confirmation.
* **Mitigation**:
  - Strict FastAPI role dependency `require(*roles)` on every protected endpoint.
  - First-login forced password reset (`must_reset_password`) blocks all operational API calls until credentials are changed.
  - Soft deletion immediately rejects any user or hospital bearer token upon revocation.

---

## 5. OWASP Top 10 (2021) Verification Checklist

| OWASP Category | TrustFed Defense Mechanism | Source Code Citation | Test Suite Evidence |
|---|---|---|---|
| **A01:2021 – Broken Access Control** | Role-based access control (`require(*roles)`), cross-hospital / cross-hub boundary enforcement, instant token rejection on user/hospital soft delete. | `backend/api/v1/routes.py:require`, `current_user` | `test_phase2_hierarchy_and_users.py`, `test_phase_c_security_hardening.py` |
| **A02:2021 – Cryptographic Failures** | MultiFernet AES-128-CBC + HMAC-SHA256 for PHI and TOTP secrets; PBKDF2-SHA256 (100k rounds) for passwords; PyJWT HS256 with dynamic Key ID rotation; MultiFernet key rotation drills. | `backend/services/crypto.py`, `backend/services/auth.py`, `backend/services/mfa.py` | `test_key_rotation.py`, `scripts/rotation_drill.py` |
| **A03:2021 – Injection** | SQLAlchemy 2.0 parameterized queries and ORM models; zero raw string interpolation in SQL statements; Pydantic request validation schemas. | `backend/api/v1/routes.py`, `backend/db/models.py` | `test_auth_and_security.py:test_sql_injection_defense` |
| **A04:2021 – Insecure Design** | Separation of Informational vs Clinical modes; strict zero-PHI persistence in Informational Mode; one-time burnout recovery codes; hash-chained audit ledger. | `backend/core/deployment_mode.py`, `backend/services/mfa.py` | `test_deployment_modes.py`, `test_phase_c_security_hardening.py` |
| **A05:2021 – Security Misconfiguration** | Unconditional security response headers (`Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`); RLS enabled on all 16 DB tables; startup refuses weak secrets or missing configs. | `backend/main.py:security_headers_middleware`, `backend/db/migrations/enable_rls.py` | `test_phase7_hardening_and_compliance.py:test_security_headers_present` |
| **A06:2021 – Vulnerable and Outdated Components** | Automated dependency audits (`pip-audit`, `npm audit`); weekly Dependabot scanning configured for both `/backend` and `/frontend`. | `.github/dependabot.yml`, `backend/requirements.txt` | `pip-audit -r backend/requirements.txt` (0 vulnerabilities) |
| **A07:2021 – Identification & Authentication Failures** | RFC 6238 TOTP Multi-Factor Authentication; 8 single-use SHA-256 hashed recovery codes; per-account failed login lockout; removal and startup prohibition of default credentials (`password123`). | `backend/services/mfa.py`, `backend/services/credential_guard.py` | `test_phase_c_security_hardening.py` |
| **A08:2021 – Software & Data Integrity Failures** | Cryptographic audit ledger with genesis block verification; soft delete prevents accidental cascade destruction; model weights validation and clipping. | `backend/services/store.py:verify_chain`, `backend/services/federated.py` | `test_audit_chain_tamper_evident.py`, `test_phase5_federated_learning.py` |
| **A09:2021 – Security Logging & Monitoring Failures** | Structured JSON logging with automated PHI redaction (`core/logging_config.py`); Sentry error tracking; real-time p50/p95/p99 latency metrics on `/metrics`. | `backend/core/logging_config.py`, `backend/core/metrics.py` | `test_phase_b_performance.py`, `test_phase7_hardening_and_compliance.py` |
| **A10:2021 – Server-Side Request Forgery (SSRF)** | No user-controllable URLs fetched by backend server; external AI provider calls restricted to predefined HTTPS endpoints (e.g. NVIDIA NIM API). | `backend/services/ai_narrative.py` | Code inspection & outbound request whitelisting |

---

## 6. Vulnerability Disclosure Policy (RFC 9116)

TrustFed maintains a public `security.txt` file located at:
- `https://trustfed-backend.onrender.com/.well-known/security.txt`
- `https://frontend-3qgo.vercel.app/.well-known/security.txt`

To report security vulnerabilities, email **security@trustfed.ai**. Disclosures are acknowledged within 24 hours with remediation updates provided every 48 hours until patched.
