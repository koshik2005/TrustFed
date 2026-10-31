# TrustFed AI — Comprehensive API Specification (v2.0)

**Protocol**: REST / JSON over HTTPS  
**Authentication**: Bearer JWT in `Authorization` header (`Bearer <access_token>`)  
**Session Rotation**: Refresh Token held in `httpOnly`, `SameSite=Lax`, `Secure` cookie (`tf_refresh_token`) with CSRF double-submit protection (`X-CSRF-Token`).  
**API Base URL**:
- Local Development: `http://localhost:8000/api/v1`
- Production (Vercel Proxy): `https://frontend-3qgo.vercel.app/api/v1`
- Production (Direct Render Backend): `https://trustfed-backend.onrender.com/api/v1`

---

## 1. Authentication & Session Management

### 1.1. User Sign In
- **Endpoint**: `POST /auth/login`
- **Access**: Public (Subject to SlowAPI rate limiting: 5 failed attempts per 15 min)
- **Request Body**:
  ```json
  {
    "email": "hospital@trustfed.ai",
    "password": "password123"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "csrf_token": "4a7f29b18c6e4e9a8f1b2c3d4e5f6a7b",
    "user": {
      "id": "1",
      "name": "Nurse Sarah Chen",
      "email": "hospital@trustfed.ai",
      "role": "hospital_staff",
      "hospitalId": "1",
      "hubId": null,
      "mustResetPassword": false,
      "status": "active"
    }
  }
  ```
- **Set-Cookie**: `tf_refresh_token=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth/refresh`
- **Errors**: `401 Unauthorized` (Invalid credentials), `429 Too Many Requests` (Rate limit exceeded).

### 1.2. Token Refresh & Rotation
- **Endpoint**: `POST /auth/refresh`
- **Access**: Public with valid `tf_refresh_token` cookie and `X-CSRF-Token` header.
- **Request Headers**:
  - `Cookie: tf_refresh_token=<token>`
  - `X-CSRF-Token: <csrf_token>`
- **Response** (`200 OK`):
  ```json
  {
    "token": "<new_jwt_access_token>",
    "csrf_token": "<new_csrf_token>",
    "user": { ... }
  }
  ```
- **Errors**: `401 Unauthorized` (Revoked or expired token), `403 Forbidden` (CSRF token mismatch).

### 1.3. User Logout
- **Endpoint**: `POST /auth/logout`
- **Access**: Authenticated (`hospital_staff`, `doctor`, `regional_admin`, `global_admin`)
- **Behavior**: Invalidates the active refresh token `jti` in database and clears the `tf_refresh_token` cookie.
- **Response** (`200 OK`): `{"message": "Logged out successfully"}`

### 1.4. Mandatory Password Reset
- **Endpoint**: `POST /auth/reset-password`
- **Access**: Authenticated (User flagged with `mustResetPassword: true`)
- **Request Body**:
  ```json
  {
    "current_password": "tempPassword123!",
    "new_password": "NewStrongPassword2026!"
  }
  ```
- **Response** (`200 OK`): `{"message": "Password updated successfully"}`

---

## 2. Clinical Encounters & Differential Diagnosis

### 2.1. Symptom Dictionary
- **Endpoint**: `GET /clinical/symptoms`
- **Access**: Authenticated
- **Response** (`200 OK`):
  ```json
  {
    "symptoms": [
      { "id": "fever", "name": "Fever / Pyrexia", "category": "General", "severity": 2 },
      { "id": "cough", "name": "Cough", "category": "Respiratory", "severity": 1 }
    ],
    "ecgFindings": [
      "Normal Sinus Rhythm",
      "ST Segment Elevation / Depression",
      "Arrhythmia / Ectopic beats",
      "Sinus Tachycardia",
      "Other Abnormality"
    ]
  }
  ```

### 2.2. Patient Intake Registration
- **Endpoint**: `POST /hospital/patients`
- **Access**: `hospital_staff`, `doctor`, `global_admin` (Scoped to hospital tenancy)
- **Request Body**:
  ```json
  {
    "name": "John Doe",
    "contact": "+1-555-0199",
    "age": 45,
    "sex": "M",
    "weight": 78.5,
    "height": 175.0,
    "symptoms": ["chest_pain", "dyspnea", "fatigue"],
    "symptom_duration_days": 2,
    "vitals": {
      "temp_c": 37.2,
      "bp_sys": 138,
      "bp_dia": 88,
      "hr": 92,
      "spo2": 96.5,
      "resp_rate": 18,
      "blood_sugar": 115
    },
    "structured_ecg_finding": "Normal Sinus Rhythm",
    "optional_labs": {
      "platelets": 240,
      "wbc": 7.8
    }
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "patient": {
      "id": 14,
      "patient_identifier": "PT-A98B7C6D",
      "age": 45,
      "sex": "M",
      "hospital_id": "1",
      "created_at": "2026-10-31T08:15:00Z"
    },
    "encounter": {
      "id": 22,
      "encounter_identifier": "ENC-F1E2D3C4",
      "patient_id": 14,
      "symptoms": ["chest_pain", "dyspnea", "fatigue"],
      "ai_predicted_condition": "heart_disease",
      "ai_confidence": 0.784,
      "is_doctor_confirmed": false,
      "is_trainable": false
    }
  }
  ```

### 2.3. Right to Erasure / DPDP Act Patient Deletion
- **Endpoint**: `DELETE /hospital/patients/{patient_id}`
- **Access**: `hospital_staff`, `doctor`, `global_admin` (Strict hospital isolation)
- **Behavior**: Permanently purges patient demographics and associated clinical encounters. Writes an immutable erasure entry to the hash-chained audit ledger.
- **Response** (`200 OK`):
  ```json
  {
    "message": "Patient PT-A98B7C6D and 3 associated encounters permanently purged.",
    "audit_event_id": 892
  }
  ```
- **Errors**: `403 Forbidden` (Attempting cross-hospital erasure), `404 Not Found`.

### 2.4. Doctor Review & Diagnosis Confirmation
- **Endpoint**: `POST /hospital/encounters/{encounter_id}/confirm`
- **Access**: `doctor`, `global_admin` (Only licensed doctors can mark encounters trainable)
- **Request Body**:
  ```json
  {
    "confirmed_diagnosis": "heart_disease",
    "cause": "Ischemic coronary artery disease with exertional angina.",
    "treatment": "Aspirin 81mg daily, Atorvastatin 40mg, sublingual Nitroglycerin PRN, urgent cardiology referral."
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "id": 22,
    "confirmed_diagnosis": "heart_disease",
    "is_doctor_confirmed": true,
    "is_trainable": true,
    "doctor_confirmed_at": "2026-10-31T08:20:00Z"
  }
  ```
- **Errors**: `403 Forbidden` (`hospital_staff` attempting confirmation is rejected).

### 2.5. Clinical Differential AI Assessment
- **Endpoint**: `POST /clinical/predict`
- **Access**: Authenticated
- **Request Body**: Same clinical symptom and vitals payload as intake.
- **Response** (`200 OK`):
  ```json
  {
    "top_3": [
      {
        "condition_id": "heart_disease",
        "name": "Coronary Artery Disease (CAD)",
        "probability": 0.784,
        "suggested_cause": "Atherosclerotic plaque stenosis.",
        "suggested_remedy": "Clinical ECG, cardiac enzymes (Troponin I), cardiology consultation.",
        "remedy_disclaimer": "Suggested, clinician must verify."
      },
      {
        "condition_id": "hypertension",
        "name": "Essential Hypertension",
        "probability": 0.128,
        "suggested_cause": "Systemic vascular resistance.",
        "suggested_remedy": "Serial BP measurement, dietary DASH protocol.",
        "remedy_disclaimer": "Suggested, clinician must verify."
      },
      {
        "condition_id": "asthma",
        "name": "Bronchial Asthma Exacerbation",
        "probability": 0.088,
        "suggested_cause": "Hyperreactive airway bronchospasm.",
        "suggested_remedy": "Inhaled short-acting beta-2 agonist (Salbutamol).",
        "remedy_disclaimer": "Suggested, clinician must verify."
      }
    ],
    "red_flags": [],
    "model_version": "TF-GenDisease-v1.0",
    "mandatory_disclaimer": "TrustFed Clinical AI is a decision-support aid. It does not replace professional medical diagnosis."
  }
  ```

---

## 3. Tiered Role Dashboards

### 3.1. Hospital Node Dashboard
- **Endpoint**: `GET /dashboard/hospital?hospital_id=1`
- **Access**: `hospital_staff` (own hospital), `doctor` (own hospital), `global_admin` (any)
- **Response** (`200 OK`):
  ```json
  {
    "hospital": { "id": "1", "name": "Boston General Hospital", "status": "active" },
    "activeModelVersion": "TF-GenDisease-v1.0",
    "todayEncounters": 18,
    "pendingConfirmations": 4,
    "confirmedEncounters": 14,
    "trainableRecords": 14,
    "eligibility": {
      "isEligible": true,
      "confirmedCount": 14,
      "minimumRequired": 10,
      "contributionStatus": "eligible"
    },
    "localAccuracy": 0.857
  }
  ```

### 3.2. Regional Hub Dashboard
- **Endpoint**: `GET /dashboard/regional?hub_id=hub-east`
- **Access**: `regional_admin` (assigned hub only), `global_admin` (any hub)
- **Response** (`200 OK`):
  ```json
  {
    "hub": { "id": "hub-east", "name": "East Coast Regional Hub", "region": "East" },
    "totalHospitals": 3,
    "eligibleHospitalsCount": 2,
    "ineligibleHospitalsCount": 1,
    "regionalRecordVolume": 142,
    "regionalModelPerformance": { "macroF1": 0.742, "accuracy": 0.789 }
  }
  ```

### 3.3. Global Consortium Dashboard
- **Endpoint**: `GET /dashboard/global`
- **Access**: `global_admin` strictly (403 for all other roles)
- **Response** (`200 OK`):
  ```json
  {
    "currentModel": { "version": "TF-GenDisease-v1.0", "accuracy": 0.812, "macroF1": 0.764 },
    "recordVolume": { "totalEncounters": 384, "confirmedEncounters": 312, "pendingEncounters": 72 },
    "activeHubs": 2,
    "activeHospitals": 4,
    "privacySummary": { "actualEpsilon": 1.84, "delta": 1e-5 },
    "fairnessSummary": { "maxSubgroupDivergence": 0.042, "status": "fair" },
    "auditVerification": { "isLedgerIntact": true, "totalAuditRecords": 1840 }
  }
  ```

---

## 4. Federated Learning & Governance

### 4.1. Trigger Multi-Tier Federated Round
- **Endpoint**: `POST /federated/trigger-round`
- **Access**: `global_admin`
- **Request Body**:
  ```json
  {
    "min_records": 10,
    "epochs": 2,
    "learning_rate": 0.05,
    "noise_multiplier": 1.0,
    "clip": 1.0,
    "target_epsilon": 2.5
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "round_id": 4,
    "candidate_version": "TF-GenDisease-v1.1",
    "participating_hospitals": ["1", "2"],
    "excluded_hospitals": ["3"],
    "metrics": { "candidate_macro_f1": 0.792, "previous_macro_f1": 0.764 },
    "promoted": true,
    "reason": "Overall macro-F1 improved (+0.028) with zero per-disease regression beyond 0.05."
  }
  ```

### 4.2. One-Click Model Rollback
- **Endpoint**: `POST /federated/models/{version}/rollback`
- **Access**: `global_admin`
- **Request Body**: `{"reason": "Clinical regression observed in field reports"}`
- **Response** (`200 OK`):
  ```json
  {
    "message": "Model rolled back to TF-GenDisease-v1.0 successfully.",
    "active_version": "TF-GenDisease-v1.0"
  }
  ```

---

## 5. Privacy, Consent & Retention Endpoints

### 5.1. Consent Management
- **Endpoint**: `POST /consent/manage`
- **Access**: `hospital_staff`, `doctor`, `regional_admin`, `global_admin`
- **Request Body**:
  ```json
  {
    "hospital_id": "1",
    "consent_type": "federated_training",
    "granted": true,
    "terms_version": "v2.0"
  }
  ```
- **Response** (`200 OK`): `{"status": "success", "consent_record_id": 44}`

### 5.2. Automated Data Retention Pruning
- **Endpoint**: `POST /data-retention/prune`
- **Access**: `global_admin`
- **Request Body**: `{"max_unconfirmed_age_days": 90, "purge_revoked_consent": true}`
- **Response** (`200 OK`):
  ```json
  {
    "purged_unconfirmed_encounters": 12,
    "purged_revoked_consent_records": 1,
    "audit_event_id": 893
  }
  ```

---

## 6. System Health & Readiness

### 6.1. Health Check
- **Endpoint**: `GET /health` or `GET /api/v1/health`
- **Access**: Public
- **Response** (`200 OK`):
  ```json
  {
    "status": "healthy",
    "version": "2.0.0",
    "database": "connected",
    "allow_demo_users": true,
    "environment": "development"
  }
  ```
