# TrustFed-Health (v2.0 Production Release)

Privacy-preserving, explainable, fairness-audited **hierarchical federated learning** for multi-hospital cardiac disease risk prediction (`Hospital Node` → `Regional Aggregator` → `Global Coordinator`).

[![TrustFed CI](https://github.com/koshik2005/TrustFed/actions/workflows/ci.yml/badge.svg)](https://github.com/koshik2005/TrustFed/actions/workflows/ci.yml)
[![Live Frontend](https://img.shields.io/badge/Live-Vercel-black?logo=vercel)](https://frontend-3qgo.vercel.app/)
[![HIPAA Compliant](https://img.shields.io/badge/Security-HIPAA%20Compliant-emerald)]()

---

## Architecture Overview

```
                                      [ Global Coordinator (Admin) ]
                                                     ▲
                                                     │ Secure Aggregation (Z_2^64 / Paillier)
                                                     ▼
                              [ Regional Hub: East ]   [ Regional Hub: West ]
                                         ▲
                                         │ DP-SGD Gradients (ε=1.84, δ=1e-5)
                                         ▼
                 [ Boston General Hospital ]       [ Johns Hopkins Node ]
                   (Local Patient Records)           (Local Patient Records)
```

- **Frontend**: React 19, TypeScript, Vite, TailwindCSS v4, Framer Motion, Recharts, Zustand (In-memory token management).
- **Backend API**: FastAPI (Python 3.11), PyJWT, SlowAPI rate-limiting, SQLite / PostgreSQL (Supabase compatible).
- **TEFL Engine**: Custom pure NumPy MLP (13-32-16-2), Rényi DP Accountant, Paillier Homomorphic Encryption, Exact Coalition Shapley Values (SHAP), Yeom et al. Membership-Inference Auditing.

---

## Role-Based Access Control Matrix

| Feature / Endpoint | Hospital Staff (`hospital_staff`) | Regional Admin (`regional_admin`) | Global Admin (`global_admin`) | Security Enforcement |
|---|:---:|:---:|:---:|---|
| **Hospital Dashboard** (`/dashboard`) | View own hospital node only | View all regional nodes | View all consortium nodes | Tenancy scoped (`hospital_id`) |
| **Patient Risk Prediction** (`/prediction`) | Predict & view own hospital patients | Predict & view regional patients | Full consortium prediction access | Strict object-level auth |
| **Prediction History** (`/prediction/history`) | Own hospital records only | Regional records only | All hospital records | Filtered by DB tenant ID |
| **SHAP Explainability** (`/explain`) | View local patient SHAP coalitions | View regional SHAP profiles | Full global explanation access | Isolated patient scope |
| **Regional Hub** (`/regional`) | 403 Forbidden | Manage East/West aggregators | Full aggregator topology | Role guarded (`ADMINS`) |
| **Global Training** (`/training`) | 403 Forbidden | View round convergence & loss | Trigger & configure FL sessions | Role guarded (`ADMINS`) |
| **Model Comparison** (`/comparison`) | 403 Forbidden | View FL vs Centralized vs FedProx | Full benchmark comparison | Role guarded (`ADMINS`) |
| **Fairness Audit** (`/fairness`) | 403 Forbidden | 403 Forbidden | View JS-divergence subgroup audits | Admin only (`global_admin`) |
| **Differential Privacy Report** (`/privacy`) | 403 Forbidden | 403 Forbidden | Inspect Rényi accountant & MIA AUC | Admin only (`global_admin`) |
| **Tamper-Evident Audit Ledger** (`/audit`) | 403 Forbidden | 403 Forbidden | Export SHA-256 hash-chained log | Admin only (`global_admin`) |

---

## Production Security Architecture

1. **Short-Lived In-Memory Access Tokens & Refresh Cookies**:
   - Access tokens (15-min lifespan) are held **strictly in memory** via Zustand; never persisted to `localStorage` or `sessionStorage`.
   - Refresh tokens are stored in an `httpOnly`, `Secure`, `SameSite=None` cookie with unique `jti` tracking, database revocation, and automatic pair rotation on every refresh.
   - Double-submit `X-CSRF-Token` headers protect token refresh against cross-site request forgery.
2. **Exact-Origin CORS**:
   - Configured strictly to `https://frontend-3qgo.vercel.app` (and local dev `http://localhost:5173`). Wildcards are rejected on server startup.
3. **Render Proxy-Aware Rate Limiting**:
   - SlowAPI rate-limiting parses the client IP from the first entry of the `X-Forwarded-For` header behind Render's reverse proxy, preventing denial-of-service without blocking proxy peers.
4. **Cold-Start Resilience**:
   - Free-tier Render standby is automatically detected (502/503/504/timeout). The client triggers an exponential backoff auto-retry queue and displays a non-intrusive status banner.
5. **Production Seed Guard**:
   - When running with `ENVIRONMENT=production` or on Render, demo user seeding with default credentials is automatically blocked.

---

## Test Accounts (Demo Environment)

| Role | Email | Password | Permissions |
|---|---|---|---|
| **Hospital Staff** | `hospital@trustfed.ai` | `password123` | Boston General Hospital clinical workspace |
| **Regional Admin** | `regional@trustfed.ai` | `password123` | East Coast zone aggregator & training monitor |
| **Global Admin** | `admin@trustfed.ai` | `password123` | Full consortium governance, fairness, and cryptographic audit |

---

## Local Development & Testing

### 1. Run Backend Test Suite (18 Automated Tests)
```bash
# Run security, tenancy, auth, and TEFL algorithmic tests
python backend/tests/test_auth_and_security.py
python backend/tests/test_services.py
python backend/tests/test_tefl.py
```

### 2. Run Frontend Lint, Tests, and Build
```bash
cd frontend
npm run lint    # Oxlint (0 errors, 0 warnings policy)
npm run test    # Vitest in-memory auth & clinical prediction tests
npm run build   # Type-checked production bundle
```

### 3. Start Local Development Servers
```bash
# Backend (Terminal 1)
cd backend
python -m uvicorn main:app --reload --port 8000

# Frontend (Terminal 2)
cd frontend
npm run dev
```

---

## Deployment Configuration

- **Frontend (Vercel)**:
  - Framework: Vite
  - Build command: `npm run build`
  - Output directory: `dist`
  - Routes routed via `vercel.json` SPA rewrites.
- **Backend (Render)**:
  - Configuration blueprint: [`render.yaml`](render.yaml)
  - Auto-configured environment variables: `CORS_ORIGINS`, `ENVIRONMENT=production`, `SECRET_KEY`.

---

## India's Digital Personal Data Protection (DPDP) Act 2023 Considerations

> [!WARNING]
> **COMPLIANCE DISCLAIMER**: The architectural patterns and privacy controls described below are technical mechanisms designed to assist healthcare institutions in evaluating readiness against the principles of India's Digital Personal Data Protection Act, 2023 (DPDP Act 2023). **TrustFed does NOT claim formal certification, regulatory approval, or statutory compliance.** Achieving legal compliance under the DPDP Act 2023 requires legal counsel review, institutional data governance frameworks, Data Protection Officer (DPO) appointments, formal Consent Manager registrations, and operational safeguards outside the scope of software alone.

### Technical Alignment Architecture

1. **Classification of Roles (Section 2(i) & 2(k))**:
   - **Data Fiduciary**: Each participating hospital node acts as the Data Fiduciary determining the purpose and means of clinical patient data collection and intake.
   - **Data Processor**: The regional aggregation coordinators and global consortium servers act strictly as Data Processors, receiving only differentially private mathematical gradient summaries (`w_i`), never raw digital personal data.

2. **Notice and Consent Mechanism (Section 6)**:
   - Patient intake and federated model contribution require explicit, itemized institutional and clinical consent records stored in the `consent_records` ledger (`POST /api/v1/consent/manage`).
   - Consent can be granted or revoked at any time. Revocation immediately disables participation in subsequent federated learning rounds.

3. **Purpose Limitation & Data Minimization (Section 7)**:
   - Identifiable patient data (name, contact details) is strictly isolated within the local hospital boundary and encrypted at rest with AES-256-GCM.
   - Only non-identifiable, calibrated symptom vectors and model updates leave the hospital; raw records and patient identities never leave the local node.

4. **Right to Correction and Erasure (Section 12)**:
   - TrustFed provides an automated Right to Erasure endpoint (`DELETE /api/v1/hospital/patients/{patient_id}`).
   - Exercising erasure permanently deletes the patient's demographics, unlinks encounters, purges local consent tokens, and appends a tamper-evident event to the SHA-256 hash-chained audit ledger.

5. **Storage Limitation & Automated Retention Purge (Section 8(7))**:
   - The platform includes configurable data retention controls (`POST /api/v1/data-retention/prune`) enabling hospitals to automatically purge unconfirmed draft clinical encounters older than a configured threshold (default: 90 days) and remove revoked consent artifacts.

6. **Reasonable Security Safeguards (Section 8(5))**:
   - **At Rest**: AES-256-GCM symmetric encryption for patient names and contact numbers.
   - **In Transit**: Mandatory TLS 1.3, Strict Transport Security (`HSTS max-age=31536000`), Content Security Policy (`CSP`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`.
   - **Mathematical Privacy**: Differential Privacy via DP-SGD ($(\epsilon, \delta)$-differential privacy with Rényi Differential Privacy accountant) with Gaussian perturbation and $L_2$ norm gradient clipping.
   - **Accountability**: Hash-chained tamper-evident audit ledger preserving an immutable, verifiable trail of all access, consent modifications, model promotions, and data deletions.

