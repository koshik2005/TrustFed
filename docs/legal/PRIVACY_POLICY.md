# Privacy Policy

> [!CAUTION]
> **DRAFT, pending legal review.**  
> This Privacy Policy is a draft operational document prepared for prototype service review. It outlines current informational practices and planned clinical architectures. It does NOT claim certified statutory compliance (e.g., DPDP or HIPAA).

**Last Updated**: November 2026  
**Current Operating Mode**: **Informational Mode (Active)**  
**Clinical Mode**: **Not Active (Disabled)**

---

## 1. Operating Mode Overview

TrustFed operates in two distinct operational architectures:
1. **Informational Mode (CURRENTLY ACTIVE)**: Designed for educational decision support using non-identifiable parameters. Does NOT collect, store, or process personal health records or direct personal identifiers.
2. **Clinical Mode (NOT ACTIVE — FUTURE ARCHITECTURE)**: Completely disabled in production until signed hospital consortium agreements, ethical approvals, and formal regulatory review are finalized.

---

## 2. Informational Mode: Data Practices (ACTIVE)

### 2.1 What We Collect
In Informational Mode, TrustFed collects only non-linkable, non-identifiable usage metrics necessary to compute algorithmic differential triage:
- **Demographic Bands**: Broad age integer and biological sex indicator (e.g. Male / Female / Other).
- **Presenting Symptoms**: Selected symptom token identifiers (e.g. `fever`, `cough`, `chest_pain`).
- **Clinical Parameter Readings**: Optional physiological vitals (e.g. temperature, heart rate, blood pressure, oxygen saturation).
- **System Telemetry**: Ephemeral anonymized request IDs, API response latency, and aggregate top-1 confidence distribution statistics for drift monitoring.

### 2.2 What We Do NOT Collect
Informational Mode strictly rejects and enforces the omission of all direct personal identifiers:
- **NO Patient Names**: Patient names, initials, or family names are not accepted.
- **NO Contact Information**: No phone numbers, email addresses, or residential street addresses.
- **NO National Identifiers**: No government identity numbers (e.g. Aadhaar, Social Security, National Health IDs).
- **NO Real Patient Identifiers**: No unredacted hospital medical record numbers (MRNs) or longitudinal electronic medical records.

### 2.3 Data Retention & Purging
- **Ephemeral Processing**: Symptom inputs and vital parameters are processed in-memory during HTTP requests and discarded upon response delivery.
- **Aggregated Model Telemetry**: Only aggregate daily counts (e.g. number of inferences, mean confidence, red-flag trigger counts) are persisted in operational monitoring logs.
- **Structured Logs**: Server logs use cryptographic redaction filters ensuring no personal identifiers or authentication secrets are logged.

### 2.4 User Rights (Informational Mode)
Because no personal health records or identifiable personal data are collected in Informational Mode, we do not maintain profiles linkable to individuals. If you hold an administrative or test login account:
- You have the right to inspect account credential metadata.
- You have the right to request deletion or rotation of administrative account credentials.

---

## 3. Essential Cookies Only Notice

> [!NOTE]
> **No Non-Essential or Tracking Cookies Used.**  
> TrustFed uses **ONLY strictly essential** cookies required for secure user authentication:
> - **Refresh Token Cookie**: An `HttpOnly`, `SameSite=Strict`, `Secure` cryptographic token used solely to maintain authenticated staff sessions.
> - **CSRF Protection Cookie / Header**: Used to prevent cross-site request forgery attacks.
> 
> TrustFed uses **ZERO advertising, tracking, marketing, or third-party analytics cookies**. Because no non-essential cookies are placed on user devices, no cookie consent banner is legally required under standard electronic privacy regulations.

---

## 4. Clinical Mode: Planned Architecture (NOT ACTIVE)

> [!IMPORTANT]
> **SECTION STATUS: NOT ACTIVE.**  
> Clinical Mode is disabled in the production codebase until all legal, clinical, and regulatory preconditions are met.

When Clinical Mode is activated in future phases, the following data governance protections are designed into the platform architecture:
- **Tenancy Boundary**: Data resides strictly within the originating hospital node. No raw patient records or patient identifiers are transmitted to external servers.
- **Local Differential Privacy (DP-SGD)**: Federated model weight updates apply DP-SGD with mathematically bounded privacy budgets ($\varepsilon \le 1.84$) preventing membership inference and reconstruction.
- **Patient Consent Architecture**: Encounters require explicit digital consent records linked to patient identifier hashes before any eligibility for local model training.
- **Immutable Audit Trail**: All data access, consent modifications, and prediction confirmations are logged to append-only cryptographically hashed audit ledgers.

---

## 5. Security Safeguards

TrustFed implements technical security safeguards:
- **Transport Security**: Mandatory TLS 1.3 encryption for all data in transit.
- **At-Rest Protection**: MultiFernet cryptographic encryption for persisted secrets and database backups.
- **Access Control**: Role-based access control (RBAC) with enforced multi-factor authentication (MFA/TOTP) for administrative personnel.

---

## 6. Grievance Redressal & Contact

For any inquiries, feedback, or privacy-related concerns, please contact our designated Grievance Officer as outlined in [`GRIEVANCE_POLICY.md`](file:///d:/projects/TrustFed/docs/legal/GRIEVANCE_POLICY.md):
- **Email**: `grievance-officer@trustfed.ai` (Security/Privacy: `security@trustfed.ai`)
- **Designation**: Nodal Grievance Redressal Officer

