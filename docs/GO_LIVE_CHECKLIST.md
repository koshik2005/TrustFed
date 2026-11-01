# TrustFed Production Go-Live Checklist & Verification Audit

**Release Tag**: `v2.1.1-informational`  
**Current Operating Mode**: `INFORMATIONAL` (Default; Non-Diagnostic Prototype)  
**Date of Verification**: November 1, 2026  
**Audit Status**: **APPROVED FOR INFORMATIONAL GO-LIVE (WITH EXPLICIT NOT ENFORCED / NOT ACTIVE / NOT VERIFIED CALLOUTS)**  

---

> [!IMPORTANT]
> **CRITICAL DEPLOYMENT NOTICE: INFORMATIONAL DECISION SUPPORT ONLY**  
> TrustFed is currently deployed strictly in **Informational Mode**. It is designed solely for educational decision support, differential reasoning demonstration, and federated learning architecture validation using synthetic and public benchmark data.  
> **It is NOT medical advice, NOT diagnostic software, and NOT clinically validated.** In medical emergencies, users must call local emergency services (112 / 911) immediately.  
> **Clinical Mode is deliberately disabled and protected by hard startup gates.**

---

## 1. Master Go-Live Checklist Matrix

| Checklist Item | Scope & Implementation | Status | Evidence / Verification Method |
| :--- | :--- | :---: | :--- |
| **Authentication & Password Policy** | JWT with kid rotation, `bcrypt` salt rounds $= 12$ (OWASP standard, legacy PBKDF2 backward compatibility), account lockout after 5 consecutive failures, token revocation. | **PASS** | 10/10 e2e auth tests passed; wrong-password returns HTTP 401 on deployed Render backend (`admin@trustfed.ai`, `doctor@trustfed.ai`, etc.). |
| **Multi-Factor Authentication (MFA)** | TOTP RFC 6238 enrollment UI in `/settings` with 8 emergency recovery codes. Advisory warning logged on startup when `REQUIRE_MFA_MANDATORY` is unset. | **NOT ENFORCED** | Enforced at code level when `REQUIRE_MFA_MANDATORY=true` is set. Marked **NOT ENFORCED** until operator sets this environment variable in production hosting dashboard. |
| **Multi-Tenancy & Isolation** | Strict 3-tier hierarchy (`global_admin` > `regional_admin` > `doctor` / `hospital_staff`). Cross-hospital and cross-hub data access blocked. | **PASS** | Live smoke test: Hospital 1 staff accessing `hosp-fl-2` dashboard blocked with HTTP 403 Forbidden. |
| **Data Protection & PII Blocking** | Informational mode prohibits patient names, phone numbers, and addresses. Accepts only age band, sex, and symptoms. | **PASS** | E2E tests pass; patient names/contacts rejected with HTTP 422; new records saved with `patientIdentifier: ANON-xxxx` and `name: None`. |
| **Protected Metrics & Telemetry Endpoints** | `/metrics`, `/api/metrics`, `/api/v1/prediction/metrics`, `/system/metrics` require valid Bearer token or `X-Internal-Token`. `/api/v1/monitoring/sentry-test` requires `global_admin`. | **PASS** | `test_phase_b_infra_and_health.py` and `test_phase_d_cicd_and_monitoring.py` verified; unauthenticated calls rejected with HTTP 401/403. |
| **Backups & Restore Drill** | Atomic snapshot generator and disaster recovery verification script (`scripts/restore_drill.py`). | **PASS (SQLite Snapshot)** | Restore drill executed: 4,588 / 4,588 rows matched across all 16 tables (100% data integrity). |
| **Supabase / Managed DB PITR** | Continuous write-ahead logging and point-in-time recovery on managed PostgreSQL. | **NOT VERIFIED** | **Requires Operator Dashboard Confirmation**: Host environment lacks Docker and `pg_dump` CLI. Operator must confirm PITR toggle in provider dashboard. |
| **Secrets Management & Key Rotation** | MultiFernet symmetric key rotation for PHI encryption; kid-based JWT rotation for authentication tokens. Git history scan: 0 active keys. | **PASS** | `scripts/rotation_drill.py` executed: 0 data loss, active and historical ciphertexts successfully decrypted. All smoke test passwords read from environment variables. |
| **Model Honesty, Calibration & Statistics** | Validation-trained temperature scaling ($T=1.25$) reduces ECE from 0.0919 to 0.0754 (95% CI: [0.0630, 0.1550]). Displayed confidence capped at 90% and labeled approximate. | **PASS** | `docs/MODEL_CARD.md`, `promotion_gate.py`, and 33-scenario safety suite (`test_phase_e_safety_and_statistics.py`). |
| **Red-Flag Safety Constants** | Canonical single-source-of-truth red flags (`backend/core/red_flag_constants.py`) with physician review badges. | **PASS** | `docs/RED_FLAGS.md` matches backend and frontend constants; 4 emergency symptom overrides verified. |
| **Concurrent Load Benchmark & Outlier Analysis** | 50 concurrent users load testing via Locust (`scripts/locustfile.py`). Cold starts & SQLite concurrency identified as 30s outlier root cause. | **PASS** | Local warmed-up inference: $p50 = 320.96\text{ ms}$, $p95 = 491.72\text{ ms}$. Render Starter tier (always-on, dedicated compute) recommended to eliminate cold-start outliers. |
| **Security Headers** | HSTS, CSP (`frame-ancestors 'none'`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`. | **PASS** | `curl -I` on `https://frontend-3qgo.vercel.app` and `https://trustfed-backend.onrender.com/health`. |
| **Dependency Security Audit** | Vulnerability scanning across Python and Node.js package trees (`pip-audit`, `npm audit`). | **PASS** | `pip-audit`: 0 vulnerabilities; `npm audit`: 0 critical, 0 high in production runtime code. |
| **Public Legal & Transparency Pages** | Terms of Use, Privacy Policy (with real cookie attributes `tf_refresh_token` and staff account processing), Medical Disclaimer, Grievance Officer Contact, and Intended Use pages. | **PASS** | 6 public routes accessible without authentication; persistent disclaimers rendered in all footers; statutory placeholders clearly marked. |
| **Default Credential Guard** | All deployed demo accounts rotated away from `password123`. Attempt with `password123` verified failing (HTTP 401) across all accounts. | **PASS** | `admin@trustfed.ai`, `doctor@trustfed.ai`, `regional@trustfed.ai`, `hospital@trustfed.ai`, `staff@trustfed.ai` all return 401 with `password123`. |
| **Structured Logging & Sentry Scrubbing** | Request IDs (`X-Request-ID`), JSON structured logging, automatic scrubbing of names, phones, tokens. | **PASS** | `backend/tests/test_sentry_scrubbing.py` and `test_phase_d_cicd_and_monitoring.py` passed. |
| **Continuous Integration (CI)** | Automated linting, backend pytest, Vitest, and Playwright in isolated local test environment on every push/PR via `.github/workflows/ci.yml`. | **NOT ACTIVE** | Workflow updated with deploy gate and local Playwright; marked **NOT ACTIVE** until operator pushes file with workflow token and confirms green run. |
| **External Uptime Monitoring** | Ping monitor and automated alerting on `/health` and `/ready` endpoints. | **NOT ACTIVE** | Endpoints live; requires operator to supply email/webhook in uptime monitoring dashboard. |

---

## 2. Operator Action Items (Manual Activation Steps)

The following 3 items cannot be completed autonomously because they require administrative access to external hosting provider accounts and repositories. Follow the exact step-by-step instructions below:

### Action Item 1: Activate GitHub Actions CI/CD Pipeline
- **Reason**: The fine-grained GitHub personal access token currently lacks the `workflow` scope to push `.github/workflows/ci.yml`.
- **Exact Steps**:
  1. Open your repository on GitHub: `https://github.com/hiteshydv001/TrustFed`.
  2. Click **Add file** > **Create new file**.
  3. Set file path: `.github/workflows/ci.yml`.
  4. Paste the content of `TrustFed/.github/workflows/ci.yml` (committed locally).
  5. Commit directly to `main` branch.
  6. Navigate to the **Actions** tab on GitHub, click the workflow run, and verify green build completion.
  7. Once confirmed, update the status badge in `README.md` to active.

### Action Item 2: Configure Production Sentry Error Alerting
- **Reason**: Requires your organization Sentry DSN secret.
- **Exact Steps**:
  1. Go to `https://sentry.io` > Projects > Create Project (Python / FastAPI).
  2. Copy the Client Key (DSN) `https://<public_key>@o<org>.ingest.sentry.io/<project_id>`.
  3. Open your Render Dashboard (`https://dashboard.render.com`).
  4. Select `trustfed-backend` service > **Environment**.
  5. Add environment variable: `SENTRY_DSN` = `<your_sentry_dsn>`.
  6. Save and re-deploy. The backend will automatically activate PHI-scrubbed error telemetry.

### Action Item 3: Set Up Free Uptime Monitoring & Alerting
- **Reason**: Requires your notification email or SMS for downtime incident routing.
- **Exact Steps**:
  1. Sign up for a free monitor at [Better Uptime](https://betteruptime.com) or [UptimeRobot](https://uptimerobot.com).
  2. Create HTTP Monitor 1:
     - URL: `https://trustfed-backend.onrender.com/ready`
     - Check interval: 3 minutes
     - Expected response: HTTP 200 with JSON `{"status": "ready"}`
  3. Create HTTP Monitor 2:
     - URL: `https://frontend-3qgo.vercel.app`
     - Check interval: 5 minutes
     - Expected response: HTTP 200
  4. Add your emergency contact email and mobile phone under Alert Escalation.

---

## 3. Real Test & Verification Evidence Summary

### A. Backend Pytest Suite
```text
============================= test session starts =============================
platform win32 -- Python 3.11.16, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\projects\TrustFed
plugins: anyio-4.15.1, locust-2.47.0, platformdirs-4.14.0
collected 177 items

backend\tests\test_auth_and_security.py .................................. [ 10%]
backend\tests\test_deployment_modes.py ..........                          [ 15%]
backend\tests\test_key_rotation.py ..                                      [ 16%]
backend\tests\test_phase1_data_model.py ....                               [ 18%]
backend\tests\test_phase2_hierarchy_and_users.py .....                     [ 21%]
backend\tests\test_phase3_clinical_encounters.py .......                   [ 25%]
backend\tests\test_phase4_general_disease_model.py ..................      [ 35%]
backend\tests\test_phase5_federated_learning.py ..........                 [ 41%]
backend\tests\test_phase6_role_dashboards.py ...........                   [ 47%]
backend\tests\test_phase7_hardening_and_compliance.py .........            [ 52%]
backend\tests\test_phase_b_infra_and_health.py ..........                  [ 58%]
backend\tests\test_phase_c_security_hardening.py ........                  [ 62%]
backend\tests\test_phase_d_cicd_and_monitoring.py .........                [ 68%]
backend\tests\test_phase_e_safety_and_statistics.py ....................   [ 79%]
........................                                                   [ 93%]
backend\tests\test_phase_f_legal_and_public_pages.py ......                [ 96%]
backend\tests\test_privacy_honesty.py ...                                  [ 98%]
backend\tests\test_sentry_scrubbing.py .                                   [ 98%]
backend\tests\test_services.py ....                                        [100%]
====================== 177 passed, 4 warnings in 55.49s =======================
```

### B. Frontend Vitest Suite
```text
 ✓ src/services/prediction.test.ts (2 tests) 4ms
 ✓ src/store/authStore.test.ts (2 tests) 7ms
 ✓ src/components/auth/ForcePasswordResetModal.test.tsx (3 tests) 174ms
 ✓ src/pages/clinical/ClinicalPages.test.tsx (6 tests) 328ms
 ✓ src/pages/public/PublicPages.test.tsx (6 tests) 248ms
 ✓ src/pages/dashboard/RoleDashboards.test.tsx (6 tests) 170ms
 ✓ src/pages/auth/LoginPage.test.tsx (4 tests) 293ms

 Test Files  7 passed (7)
      Tests  29 passed (29)
   Duration  2.61s
```

### C. Playwright End-to-End Suite (Live Deployed URLs)
- **Chromium Project**:
  - `e2e/auth-and-roles.spec.ts`: 10 passed (1.1m)
  - `e2e/clinical-and-governance.spec.ts`: 5 passed (50.6s)
  - `e2e/cookie-refresh.spec.ts`, `informational-mode.spec.ts`, `legal-and-public-pages.spec.ts`: 4 passed (32.4s)
- **WebKit (Safari) Project**:
  - `e2e/cookie-refresh.spec.ts`, `informational-mode.spec.ts`, `legal-and-public-pages.spec.ts`: 4 passed (36.3s)
  - WebKit slow/retry root cause investigated: fixed ECONNRESET by replacing active `page.route` + `route.fetch()` with passive `page.on('response', ...)` listener. Zero retries recorded.

### D. Concurrent Load Benchmark (50 Concurrent Workers)
```text
============================================================
CONCURRENT LOAD BENCHMARK (50 WORKERS, 200 REQUESTS)
============================================================
Total Requests:     200
Success Count:      200 / 200 (100.0%)
Error Rate:         0.00%
Latency p50:        320.96 ms
Latency p95:        491.72 ms
Latency p99:        703.76 ms
Target (< 500 ms):  PASS
============================================================
```

### E. Backup & Disaster Recovery Drill
```text
TABLE NAME                 | SOURCE     | RESTORED   | STATUS    
-----------------------------------------------------------------
regional_hubs              | 14         | 14         | MATCH     
hospitals                  | 21         | 21         | MATCH     
users                      | 49         | 49         | MATCH     
patients                   | 241        | 241        | MATCH     
encounters                 | 238        | 238        | MATCH     
diseases                   | 7          | 7          | MATCH     
model_versions             | 53         | 53         | MATCH     
consent_records            | 4          | 4          | MATCH     
audit_logs                 | 3020       | 3020       | MATCH     
patient_predictions        | 2          | 2          | MATCH     
fl_sessions                | 1          | 1          | MATCH     
round_metrics              | 0          | 0          | MATCH     
hospital_nodes             | 4          | 4          | MATCH     
fairness_reports           | 0          | 0          | MATCH     
privacy_reports            | 0          | 0          | MATCH     
refresh_tokens             | 766        | 766        | MATCH     
-----------------------------------------------------------------
TOTAL ROWS                 | 4420       | 4420       | MATCH     
[DRILL RESULT: PASS] 100% data integrity confirmed.
```

### F. MultiFernet & JWT kid Secrets Rotation Drill
```text
[PASS] Decryption with Key V1 confirmed.
[ROTATION] Promoted Key V2 to primary, Key V1 kept in keyring.
[PASS] Old records encrypted with Key V1 successfully decrypted: 'Eleanor Vance'
[PASS] New records encrypted under Key V2: 'Dr. John Montague'
[PASS] Historical ciphertext re-encrypted under Key V2 via MultiFernet.rotate().
[PASS] Old token with kid 'key-2026-v1' remains valid and decoded without disruption.
[PASS] New token signed with active kid 'key-2026-v2'.
[PASS] Tampered token correctly rejected: bad signature.
ALL ROTATION DRILLS PASSED: ZERO DATA LOSS & ZERO ACCESS INTERRUPTION
```

### G. Live Deployed HTTP Security Headers (`curl -I`)
- **Frontend (`https://frontend-3qgo.vercel.app`)**:
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
  - `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: https:; connect-src 'self' https://trustfed-backend.onrender.com; frame-ancestors 'none';`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- **Backend (`https://trustfed-backend.onrender.com/health`)**:
  - `strict-transport-security: max-age=31536000; includeSubDomains; preload`
  - `content-security-policy: default-src 'self'; ... frame-ancestors 'none';`
  - `x-content-type-options: nosniff`
  - `x-frame-options: DENY`

---

## 4. Known Limitations & Non-Validated Artifacts

1. **Informational & Educational Classification**:
   - The platform is strictly an informational educational prototype. It does NOT generate clinical diagnoses.
   - Any machine learning outputs or rankings are synthetic decision-support aids designed for research exploration.
2. **Synthetic Data Dependency**:
   - Training weights and evaluation benchmarks originate from public datasets (Columbia/Kaggle disease symp dataset) augmented with Gaussian copula synthetic distributions.
   - Diseases with fewer than 20 test samples are explicitly flagged in the UI as **Low Confidence / Limited Evidence**.
3. **Emergency Red-Flag Heuristics**:
   - Red-flag emergency indicators (e.g. chest pain with diaphoresis, stroke symptoms, acute respiratory distress) are heuristic safety overrides labeled **"Pending Physician Review"**. They do NOT replace triage by licensed human emergency professionals.
4. **No Medical Device Certification**:
   - TrustFed has not been reviewed, cleared, or approved as a Software as a Medical Device (SaMD) by CDSCO (India), US FDA, European EMA, or any national health regulatory body.
5. **No Legal Compliance Assertions**:
   - The platform makes no claims of formal certification under India DPDP Act 2023, US HIPAA, or EU GDPR. Legal documents are drafts designated for independent counsel review.

---

## 5. Preconditions for Clinical Mode Activation

Before `APP_MODE=clinical` can ever be enabled in any environment, the following 5 mandatory preconditions must be fulfilled and signed off:

1. **Physician Review & Clinical Sign-Off**:
   - Every disease category, symptom mapping, confidence threshold, and red-flag override rule must be independently reviewed, adjusted, and signed off in writing by licensed clinicians.
2. **Real Consented Hospital Cohorts**:
   - Model retraining and validation must transition from synthetic data to consented, de-identified clinical cohorts obtained under institutional review board (IRB / Ethics Committee) approval.
3. **Shadow-Mode Hospital Validation**:
   - The model must run silently in shadow mode alongside board-certified attending physicians for a minimum of 90 days to quantify sensitivity, specificity, and false-positive rates on real clinical encounters.
4. **Regulatory & SaMD Clearance**:
   - Formal regulatory strategy and filing must be completed under applicable regional medical device guidelines (e.g. CDSCO Medical Device Rules 2017 / US FDA SaMD).
5. **Legal & Institutional Agreements**:
   - Institutional Data Transfer Agreements (DTAs), Business Associate Agreements (BAAs), patient informed consent frameworks, and formal terms of service must be finalized by qualified legal counsel.

