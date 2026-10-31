# Changelog

All notable changes to the **TrustFed-Health** platform are documented in this file.
The project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] — 2026-10-31

### Phase 1: Data Model & Tenancy Architecture
- **Added**: Three-tier organizational schema (`regional_hubs`, `hospitals`, `users`, `patients`, `encounters`, `consent_records`, `audit_ledger`).
- **Added**: Authenticated symmetric AES-128 Fernet encryption for patient names and contact information at rest.
- **Added**: Strict multi-tenant row-level authorization preventing cross-hospital and cross-hub data leakage.
- **Added**: Cryptographically hash-chained SHA-256 audit ledger recording all clinical, authentication, and training transactions.

### Phase 2: Hierarchy & User Management
- **Added**: Global Admin controls to create, edit, suspend, reactivate, and delete regional hubs and issue hub administrator credentials.
- **Added**: Regional Admin controls to manage jurisdictional hospitals strictly within their assigned hub and issue staff/doctor credentials.
- **Added**: Ephemeral one-time temporary passwords with mandatory forced reset on first login (`must_reset_password`).
- **Added**: Immediate JWT access and refresh token revocation upon suspension or removal of any user, hospital, or hub.
- **Added**: Elimination of all self-registration endpoints to prevent unauthorized ingress.

### Phase 3: Clinical Encounters & Doctor Confirmation Workflow
- **Added**: Comprehensive patient intake registration supporting 35 searchable clinical symptoms, duration, physiological vitals, ECG findings, and optional laboratory values.
- **Added**: Server-side clinical validation bounds rejecting impossible vitals (e.g. Systolic BP <= Diastolic BP, SpO2 outside 50-100%, body temperature outside 30-45°C).
- **Added**: Doctor review and confirmation queue (`POST /hospital/encounters/{id}/confirm`). Only doctor-confirmed records receive `is_trainable = true`. Staff accounts strictly barred from confirmation.
- **Added**: Zero-egress privacy guarantee ensuring direct PHI never leaves hospital boundary.

### Phase 4: General Disease Differential AI Inference Engine
- **Added**: Multi-class diagnostic engine covering 18 common outpatient and emergency conditions (`TF-GenDisease-v1.0`).
- **Added**: Native missing value handling using continuous feature indicators paired with binary missingness masks (`is_missing_<feature>`).
- **Added**: Expected Information Gain (EIG) adaptive questioning suggesting the single most decisive observation when diagnostic confidence is low.
- **Added**: Deterministic clinical safety guardrails ([red_flags.py](file:///d:/projects/TrustFed/backend/services/red_flags.py)) for immediate emergency triage (ACS, acute stroke FAST, severe hypoxia, suspected meningitis, infant high fever, hypovolemic shock).
- **Added**: Prominent clinical decision support disclaimer and verification notices on all diagnostic predictions and suggested remedies.

### Phase 5: Multi-Tier Hierarchical Federated Learning
- **Added**: On-node training strictly over doctor-confirmed, trainable clinical encounters using local DP-SGD.
- **Added**: Eligibility gate requiring configurable minimum confirmed encounters (default 10); automatically excludes suspended or removed hospitals.
- **Added**: Regional SMPC aggregation using additive secret sharing across hospital nodes and Paillier homomorphic summation across regional hubs.
- **Added**: Automated model promotion gate requiring overall Macro-F1 improvement, zero disease regression beyond tolerance ($\le 0.05$), and fairness subgroup parity.
- **Added**: One-click instant model rollback (`POST /federated/models/{version}/rollback`).
- **Added**: Exact Rényi Differential Privacy (RDP) Moments Accountant enforcing an honest privacy ceiling.

### Phase 6: Role-Based Clinical & Governance Dashboards
- **Added**: Dedicated Hospital Dashboard displaying today's patient volume, pending doctor confirmations, local accuracy, and FL contribution eligibility.
- **Added**: Dedicated Regional Hub Dashboard displaying jurisdictional hospital nodes, consent toggles, regional volume, and regional model performance.
- **Added**: Dedicated Global Admin Dashboard displaying consortium metrics, round orchestration controls, 1-click rollback, and cryptographic audit verification.
- **Added**: Role-aware navigation dispatcher routing authenticated users directly to their designated tier.

### Phase 7: Security Hardening, DPDP Act 2023 Controls & E2E Testing
- **Added**: Strict security response headers injected by FastAPI middleware and Vercel configuration (`Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`).
- **Added**: First-party API proxy rewrite in `vercel.json` enforcing `SameSite=Lax` refresh cookies.
- **Added**: System health check endpoints (`/health`, `/api/health`, `/api/v1/health`) with live database ping.
- **Added**: India's Digital Personal Data Protection (DPDP) Act 2023 technical alignment controls:
  - Right to Erasure (`DELETE /hospital/patients/{patient_id}`)
  - Institutional & patient consent management (`POST /consent/manage`)
  - Automated data retention pruning (`POST /data-retention/prune`)
- **Added**: Structured logging with `PHIRedactionFilter` masking patient identifiers, phone numbers, emails, and tokens.
- **Added**: Sentry error monitoring integration with automatic PII scrubber.
- **Added**: Full CI workflow specification ([ci-workflow.yml](file:///d:/projects/TrustFed/docs/ci-workflow.yml)).
- **Added**: Playwright E2E test suites covering full security RBAC and clinical federated workflows with 100% pass rate.

### Phase 8: Documentation & Production-Readiness Review
- **Added**: Comprehensive root `.env.example` defining development vs. production settings.
- **Added**: Exhaustive REST API reference ([docs/API.md](file:///d:/projects/TrustFed/docs/API.md)).
- **Added**: Production-readiness audit checklist ([docs/PRODUCTION_READINESS.md](file:///d:/projects/TrustFed/docs/PRODUCTION_READINESS.md)) with pass/fail evaluation across 10 security and clinical dimensions.
- **Added**: Prominent clinical safety, CDS boundaries, and physician review requirements across all documentation.
