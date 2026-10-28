# TrustFed AI — Data Dictionary & Privacy Classification Specification

**Version:** 2.0 (General Multi-Disease Federated Learning Platform)  
**Classification Standard:** HIPAA Safe Harbor & GDPR Privacy-by-Design  
**Date:** October 2026  

---

## 1. Overview & Architectural Hierarchy

TrustFed AI implements a strict three-tier organizational hierarchy designed to ensure patient confidentiality while enabling collaborative federated machine learning:

$$\text{Global Admin} \longrightarrow \text{Regional Hubs (Aggregators)} \longrightarrow \text{Hospital Nodes} \longrightarrow \text{Encounters (De-identified)}$$

### Core Privacy Guarantees
1. **Zero Egress for Direct PHI:** Patient Names and Contact Details are **encrypted at rest** using authenticated symmetric encryption (Fernet: AES-128-CBC + HMAC-SHA256). They **never leave the hospital's boundary** under any circumstances.
2. **Federated Model Learning:** Models train locally on hospital cohorts. Only clipped, differentially-private gradients ($\sigma \le 3.5$) and encrypted model shares (Paillier Cryptosystem) are transmitted to Regional Hubs.
3. **Immutable Audit Ledger:** All clinical inferences, training sessions, and consent updates are recorded in a cryptographically hash-chained tamper-evident ledger ($\text{hash}_n = \text{SHA256}(\text{hash}_{n-1} \parallel \text{timestamp} \parallel \text{node} \parallel \text{type} \parallel \text{desc})$).

---

## 2. Privacy Classifications

Every field in the TrustFed AI data model is categorized into one of four privacy classifications:

| Classification | Definition | Storage & Sharing Policy |
| :--- | :--- | :--- |
| **`[DIRECT-PHI]`** | Directly identifying information (e.g., patient name, phone number, email address). | **ENCRYPTED AT REST** via Fernet. Decryptable **only** by authorized clinical staff within the originating hospital. Never transmitted over federated protocols. |
| **`[INDIRECT-PHI]`** | Quasi-identifiers (e.g., age, sex, hospital ID, encounter timestamps). | Stored in hospital database. Subject to Differential Privacy ($\varepsilon, \delta$) and non-IID Dirichlet partitioning prior to aggregation. |
| **`[DE-IDENTIFIED]`**| Clinical symptoms, laboratory measurements, vitals, and model predictions. | Safe for local training and de-identified federated model parameter calculation once institutional consent is granted. |
| **`[SYSTEM-METADATA]`**| Platform governance, security tokens, cryptographic hashes, model versions, and hub configurations. | Accessible according to Role-Based Access Control (RBAC). |

---

## 3. Entity Data Dictionary

### 3.1. `regional_hubs`
Coordinates regional secure multi-party computation (SMPC) and homomorphic aggregation.

| Field Name | Type | Constraints | Privacy Class | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(64)` | PK, Index | `[SYSTEM-METADATA]` | Unique hub identifier (e.g., `"hub-east"`, `"hub-west"`). |
| `name` | `VARCHAR(255)` | NOT NULL | `[SYSTEM-METADATA]` | Hub display name (e.g., `"East Coast Regional Hub"`). |
| `region` | `VARCHAR(64)` | NOT NULL | `[SYSTEM-METADATA]` | Geographical/jurisdictional zone (e.g., `"East"`, `"West"`). |
| `status` | `VARCHAR(32)` | DEFAULT `'active'` | `[SYSTEM-METADATA]` | Operational state: `'active'`, `'suspended'`. |
| `created_by` | `INTEGER` | Nullable, FK `users.id` | `[SYSTEM-METADATA]` | Global admin user ID who registered the hub. |
| `created_at` | `TIMESTAMPTZ` | DEFAULT `NOW()` | `[SYSTEM-METADATA]` | Timestamp of hub creation. |

---

### 3.2. `hospitals`
Participating medical centers and federated edge training nodes.

| Field Name | Type | Constraints | Privacy Class | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(64)` | PK, Index | `[INDIRECT-PHI]` | Hospital node identifier (e.g., `"1"`, `"hospital-boston"`). |
| `name` | `VARCHAR(255)` | NOT NULL | `[SYSTEM-METADATA]` | Institutional name (e.g., `"Boston General Hospital"`). |
| `hub_id` | `VARCHAR(64)` | FK `regional_hubs.id` | `[SYSTEM-METADATA]` | Designated regional aggregator hub. |
| `status` | `VARCHAR(32)` | DEFAULT `'active'` | `[SYSTEM-METADATA]` | Node status: `'active'`, `'idle'`, `'training'`, `'offline'`. |
| `share_deidentified`| `BOOLEAN` | DEFAULT `FALSE` | `[SYSTEM-METADATA]` | Institutional consent toggle for federated model training. |
| `consent_record_fields` | `TEXT` | Nullable (JSON) | `[SYSTEM-METADATA]` | Terms version, DPA agreement, and institutional sign-off metadata. |
| `dataset_size` | `INTEGER` | DEFAULT `0` | `[SYSTEM-METADATA]` | Count of local validated clinical training encounters. |
| `created_at` | `TIMESTAMPTZ` | DEFAULT `NOW()` | `[SYSTEM-METADATA]` | Institutional onboarding timestamp. |

---

### 3.3. `users`
Authenticated healthcare providers, regional supervisors, and global administrators.

| Field Name | Type | Constraints | Privacy Class | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PK, Index | `[SYSTEM-METADATA]` | Internal user sequence identifier. |
| `email` | `VARCHAR(255)` | UNIQUE, Index, NOT NULL | `[DIRECT-PHI]` | Work email address used for login and audit logging. |
| `name` | `VARCHAR(255)` | NOT NULL | `[DIRECT-PHI]` | Full name of clinical personnel or administrator. |
| `role` | `VARCHAR(32)` | NOT NULL | `[SYSTEM-METADATA]` | RBAC role: `'global_admin'`, `'regional_admin'`, `'hospital_staff'`, `'doctor'`. |
| `hub_id` | `VARCHAR(64)` | Nullable, FK `regional_hubs.id` | `[SYSTEM-METADATA]` | Regional hub assignment (required for `regional_admin`). |
| `hospital_id` | `VARCHAR(64)` | Nullable, FK `hospitals.id` | `[INDIRECT-PHI]` | Hospital tenancy scope (strictly isolates staff/doctors). |
| `must_reset_password` | `BOOLEAN` | DEFAULT `FALSE` | `[SYSTEM-METADATA]` | Flag requiring credential rotation upon next login. |
| `status` | `VARCHAR(32)` | DEFAULT `'active'` | `[SYSTEM-METADATA]` | Account status: `'active'`, `'suspended'`. |
| `password_hash` | `VARCHAR(255)` | NOT NULL | `[SYSTEM-METADATA]` | PBKDF2-SHA256 salted password hash ($100{,}000$ iterations). |
| `created_at` | `TIMESTAMPTZ` | DEFAULT `NOW()` | `[SYSTEM-METADATA]` | Account creation timestamp. |

---

### 3.4. `patients`
Hospital-scoped clinical patient registry.

| Field Name | Type | Constraints | Privacy Class | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PK, Index | `[SYSTEM-METADATA]` | Internal surrogate primary key. |
| `patient_identifier`| `VARCHAR(64)` | UNIQUE, Index, NOT NULL | `[INDIRECT-PHI]` | Pseudonymous Medical Record Number (MRN) (e.g., `"PT-892401"`). |
| `hospital_id` | `VARCHAR(64)` | Index, NOT NULL | `[INDIRECT-PHI]` | Hospital tenancy boundary (patient never leaves this hospital). |
| `name_encrypted` | `TEXT` | NOT NULL | **`[DIRECT-PHI]`** | **ENCRYPTED AT REST** (Fernet AES-128-CBC + HMAC-SHA256). Full legal patient name. |
| `contact_encrypted`| `TEXT` | NOT NULL | **`[DIRECT-PHI]`** | **ENCRYPTED AT REST** (Fernet AES-128-CBC + HMAC-SHA256). Phone number and/or personal email. |
| `age` | `INTEGER` | NOT NULL | `[INDIRECT-PHI]` | Patient age in years. Capped at 89 for HIPAA Safe Harbor compliance. |
| `sex` | `INTEGER` | NOT NULL | `[INDIRECT-PHI]` | Biological sex ($0 = \text{Female}$, $1 = \text{Male}$, $2 = \text{Other}$). |
| `weight` | `FLOAT` | Nullable | `[DE-IDENTIFIED]` | Weight in kilograms (kg). |
| `height` | `FLOAT` | Nullable | `[DE-IDENTIFIED]` | Height in centimeters (cm). |
| `created_at` | `TIMESTAMPTZ` | DEFAULT `NOW()` | `[INDIRECT-PHI]` | Patient registration timestamp. |

---

### 3.5. `encounters`
Clinical evaluation encounters representing general disease assessments (fever, cold, dengue, typhoid, UTI, etc.).

| Field Name | Type | Constraints | Privacy Class | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PK, Index | `[SYSTEM-METADATA]` | Internal primary key. |
| `encounter_identifier`| `VARCHAR(64)`| UNIQUE, Index, NOT NULL | `[INDIRECT-PHI]` | Pseudonymous encounter identifier (e.g., `"ENC-2026-0041"`). |
| `patient_id` | `INTEGER` | Index, FK `patients.id` | `[INDIRECT-PHI]` | Associated patient primary key. |
| `hospital_id` | `VARCHAR(64)` | Index, FK `hospitals.id` | `[INDIRECT-PHI]` | Hospital tenancy scope. |
| `symptoms` | `TEXT` | NOT NULL (JSON) | `[DE-IDENTIFIED]` | List of presenting symptoms (e.g., `["high_fever", "retro_orbital_pain", "arthralgia"]`). |
| `symptom_duration_days`| `INTEGER` | DEFAULT `1` | `[DE-IDENTIFIED]` | Duration of symptoms in days prior to evaluation. |
| `vitals` | `TEXT` | NOT NULL (JSON) | `[DE-IDENTIFIED]` | Clinical vitals: `{"bp_sys": 110, "bp_dia": 72, "hr": 98, "temp_c": 39.4, "spo2": 97, "resp_rate": 19}`. |
| `structured_ecg_finding`| `VARCHAR(64)`| Nullable | `[DE-IDENTIFIED]` | Standardized finding: `'normal'`, `'st_depression'`, `'arrhythmia'`, `'tachycardia'`. |
| `optional_labs` | `TEXT` | Nullable (JSON) | `[DE-IDENTIFIED]` | Diagnostic labs: `{"wbc": 3.8, "platelets": 88, "crp": 32, "urine_leukocytes": "negative"}`. |
| `model_version` | `VARCHAR(64)`| Nullable | `[SYSTEM-METADATA]` | Version of the model used for differential inference (e.g., `"TF-GenDisease-v1.0"`). |
| `predicted_top3` | `TEXT` | Nullable (JSON) | `[DE-IDENTIFIED]` | Top-3 ranked diseases with probabilities: `[{"disease": "Dengue Fever", "probability": 0.81}, ...]`. |
| `doctor_confirmed_diagnosis`| `VARCHAR(64)`| Nullable | `[DE-IDENTIFIED]` | Attending physician's verified diagnosis code (e.g., `"DENGUE"`, `"TYPHOID"`). |
| `cause` | `TEXT` | Nullable | `[DE-IDENTIFIED]` | Clinical etiology and risk factor summary. |
| `treatment` | `TEXT` | Nullable | `[DE-IDENTIFIED]` | Prescribed clinical regimen / therapeutic plan. |
| `confirmed_by` | `INTEGER` | Nullable, FK `users.id` | `[SYSTEM-METADATA]` | User ID of the confirming physician. |
| `confirmed_at` | `TIMESTAMPTZ` | Nullable | `[SYSTEM-METADATA]` | Verification timestamp. |
| `trainable` | `BOOLEAN` | DEFAULT `FALSE` | `[SYSTEM-METADATA]` | Eligible for federated training ($\text{Confirmed} \land \text{Consent} = \text{True}$). |
| `created_at` | `TIMESTAMPTZ` | DEFAULT `NOW()` | `[INDIRECT-PHI]` | Encounter creation timestamp. |

---

### 3.6. `diseases`
Extensible taxonomy of clinical conditions managed by Global Administrators.

| Field Name | Type | Constraints | Privacy Class | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PK, Index | `[SYSTEM-METADATA]` | Disease identifier sequence. |
| `code` | `VARCHAR(64)` | UNIQUE, Index, NOT NULL | `[SYSTEM-METADATA]` | Standard machine code: `'COLD'`, `'FLU'`, `'VIRAL_FEVER'`, `'DENGUE'`, `'TYPHOID'`, `'UTI'`, `'CARDIAC_CAD'`. |
| `name` | `VARCHAR(255)` | NOT NULL | `[SYSTEM-METADATA]` | Clinical name (e.g., `"Dengue Fever (Breakbone Fever)"`). |
| `category` | `VARCHAR(128)` | NOT NULL | `[SYSTEM-METADATA]` | Disease classification: `'Infectious'`, `'Respiratory'`, `'Urinary'`, `'Cardiovascular'`. |
| `common_symptoms`| `TEXT` | Nullable (JSON) | `[SYSTEM-METADATA]` | Canonical symptom array for differential guidance. |
| `is_active` | `BOOLEAN` | DEFAULT `TRUE` | `[SYSTEM-METADATA]` | Active state in diagnosis and federated training pipelines. |
| `created_at` | `TIMESTAMPTZ` | DEFAULT `NOW()` | `[SYSTEM-METADATA]` | Disease registration timestamp. |

---

### 3.7. `model_versions`
Audit ledger of trained federated model checkpoints across global, regional, and hospital tiers.

| Field Name | Type | Constraints | Privacy Class | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PK, Index | `[SYSTEM-METADATA]` | Sequence ID. |
| `version` | `VARCHAR(64)` | UNIQUE, Index, NOT NULL | `[SYSTEM-METADATA]` | Semantic model version (e.g., `"TF-GenDisease-v1.0"`, `"TF-HeartNet-v2"`). |
| `scope` | `VARCHAR(32)` | NOT NULL | `[SYSTEM-METADATA]` | Deployment tier: `'global'`, `'regional'`, `'hospital'`. |
| `scope_id` | `VARCHAR(64)` | Nullable | `[SYSTEM-METADATA]` | Hub ID or Hospital ID when scope is localized. |
| `disease_category`| `VARCHAR(128)`| Nullable | `[SYSTEM-METADATA]` | Domain category: `"General Multi-Condition"`, `"Cardiovascular Risk"`. |
| `metrics` | `TEXT` | Nullable (JSON) | `[SYSTEM-METADATA]` | Validation metrics: `{"accuracy": 0.864, "top3_accuracy": 0.912, "macro_f1": 0.851, "epsilon": 1.84}`. |
| `model_path` | `VARCHAR(512)`| Nullable | `[SYSTEM-METADATA]` | Storage artifact path for neural network weights (.npz). |
| `status` | `VARCHAR(32)` | DEFAULT `'active'` | `[SYSTEM-METADATA]` | State: `'active'`, `'training'`, `'archived'`, `'evaluating'`. |
| `created_at` | `TIMESTAMPTZ` | DEFAULT `NOW()` | `[SYSTEM-METADATA]` | Model checkpoint creation timestamp. |

---

### 3.8. `consent_records` & `audit_logs`

#### `consent_records`
Institutional and patient-level opt-in/opt-out authorizations.
- `id` (PK), `hospital_id` (Index), `patient_id` (Nullable Index)
- `consent_type`: `'FEDERATED_TRAINING_DEIDENTIFIED'` | `'CLINICAL_RESEARCH'`
- `status`: `'granted'` | `'revoked'`
- `granted_at`, `revoked_at`, `hash` (Chained cryptographic hash)

#### `audit_logs`
Hash-chained immutable audit log.
- `id` (PK), `session_id` (Index), `node_id`
- `event_type`: `'training'` | `'prediction'` | `'encounter'` | `'auth'` | `'config'` | `'consent'`
- `description`: Human-readable audit narrative.
- `timestamp_iso`: Exact UTC timestamp incorporated into SHA256 digest.
- `prev_hash`: $\text{hash}_{n-1}$ (or 64 zeros for genesis block).
- `hash`: $\text{SHA256}(\text{prev\_hash} \parallel \text{timestamp\_iso} \parallel \text{node\_id} \parallel \text{event\_type} \parallel \text{description})$.

---

## 4. Cryptographic PHI Encryption Specification

Direct patient identifying information (Name and Contact details) is encrypted at the application boundary prior to insertion into the database storage layer.

```
+-------------------------------------------------------------+
|                      Hospital Scope                         |
|                                                             |
|  [Plaintext Name: "Jane Doe"]  [Phone: "+1-555-0144"]       |
|                  |                         |                |
|                  v                         v                |
|       +-----------------------------------------+           |
|       | Fernet AES-128-CBC + HMAC-SHA256 Engine |           |
|       | (Derived from PATIENT_ENCRYPTION_KEY)   |           |
|       +-----------------------------------------+           |
|                  |                         |                |
|                  v                         v                |
|  [name_encrypted]               [contact_encrypted]         |
|  "gAAAAABq4WKGfAfIse..."         "gAAAAABq4WKHkLt8..."      |
|                  |                         |                |
+------------------|-------------------------|----------------+
                   v                         v
       +-------------------------------------------------+
       |         PostgreSQL / SQLite Database            |
       |  (Stored purely as ciphertext at rest)          |
       +-------------------------------------------------+
```

### Decryption Governance
- Decryption is **only** performed in response to authorized `GET /api/patients/{id}` requests initiated by an authenticated user with role `doctor` or `hospital_staff` whose `hospital_id` strictly matches the patient's `hospital_id`.
- Regional Admins and Global Admins **never receive decrypted PHI**; endpoints exposed to those roles return solely aggregated metrics or de-identified encounters.
