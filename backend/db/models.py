from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from .database import Base


# ── Hierarchical Multi-Hospital Organization ───────────────────────────────────

class RegionalHub(Base):
    __tablename__ = "regional_hubs"
    id = Column(String, primary_key=True, index=True)        # e.g. "hub-east", "hub-west"
    name = Column(String, nullable=False)                    # e.g. "East Coast Regional Aggregator"
    region = Column(String, nullable=False)                  # e.g. "East", "West"
    status = Column(String, default="active")                # active | suspended
    created_by = Column(Integer, nullable=True)              # User.id of creator
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Hospital(Base):
    __tablename__ = "hospitals"
    id = Column(String, primary_key=True, index=True)        # e.g. "1", "2", "hospital-boston"
    name = Column(String, nullable=False)                    # e.g. "Boston General Hospital"
    hub_id = Column(String, index=True, nullable=True)       # references regional_hubs.id
    status = Column(String, default="active")                # active | idle | training | suspended
    share_deidentified = Column(Boolean, default=False)      # Hospital-level consent flag
    consent_record_fields = Column(Text, nullable=True)      # JSON metadata: policy version, opt-in date
    dataset_size = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Identity & Access Management ───────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)                    # global_admin | regional_admin | hospital_staff | doctor
    hub_id = Column(String, index=True, nullable=True)       # Set if regional_admin
    hospital_id = Column(String, index=True, nullable=True)  # Set if hospital_staff or doctor
    must_reset_password = Column(Boolean, default=False)
    status = Column(String, default="active")                # active | suspended
    password_hash = Column(String, nullable=False)           # pbkdf2_sha256$iters$salt$hash
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Clinical Patients & Encounters (De-identified & Encrypted) ─────────────────

class Patient(Base):
    """Hospital-scoped patient entity. Name and Contact are ENCRYPTED AT REST and never leave hospital scope."""
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    patient_identifier = Column(String, unique=True, index=True, nullable=False)  # Pseudonymous MRN e.g. PT-9A8B7C
    hospital_id = Column(String, index=True, nullable=False)
    name_encrypted = Column(Text, nullable=False)            # Encrypted via Fernet AES-128-CBC + HMAC-SHA256
    contact_encrypted = Column(Text, nullable=False)         # Encrypted via Fernet AES-128-CBC + HMAC-SHA256
    age = Column(Integer, nullable=False)                    # De-identified clinical attribute
    sex = Column(Integer, nullable=False)                    # 0=Female, 1=Male, 2=Other
    weight = Column(Float, nullable=True)                    # kg
    height = Column(Float, nullable=True)                    # cm
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Encounter(Base):
    """Clinical encounter representing an assessment for general multi-disease diagnosis."""
    __tablename__ = "encounters"
    id = Column(Integer, primary_key=True, index=True)
    encounter_identifier = Column(String, unique=True, index=True, nullable=False)
    patient_id = Column(Integer, index=True, nullable=False) # references patients.id
    hospital_id = Column(String, index=True, nullable=False) # references hospitals.id
    symptoms = Column(Text, nullable=False)                  # JSON list: ["fever", "cough", "fatigue", "nausea"]
    symptom_duration_days = Column(Integer, default=1)
    vitals = Column(Text, nullable=False)                    # JSON: {"bp_sys": 120, "bp_dia": 80, "hr": 84, "temp_c": 38.5, "spo2": 98, "resp_rate": 18}
    structured_ecg_finding = Column(String, nullable=True)   # normal | st_depression | arrhythmia | tachycardia | null
    optional_labs = Column(Text, nullable=True)              # JSON: {"wbc": 11.2, "platelets": 140, "crp": 24, "urine_leukocytes": "positive"}
    model_version = Column(String, nullable=True)            # Model version evaluated
    predicted_top3 = Column(Text, nullable=True)             # JSON: [{"disease": "Dengue", "probability": 0.72}, {"disease": "Viral Fever", "probability": 0.18}, ...]
    doctor_confirmed_diagnosis = Column(String, nullable=True) # Extensible disease code e.g. "DENGUE"
    cause = Column(Text, nullable=True)                      # Clinical etiology narrative
    treatment = Column(Text, nullable=True)                  # Prescribed treatment / medication
    confirmed_by = Column(Integer, nullable=True)            # Doctor User.id
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    trainable = Column(Boolean, default=False)               # Trainable only if confirmed & hospital consents
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Extensible Disease Registry & Model Governance ─────────────────────────────

class Disease(Base):
    """Extensible registry of conditions managed by Global Admin (cold, flu, dengue, etc.)."""
    __tablename__ = "diseases"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)  # COLD, FLU, VIRAL_FEVER, DENGUE, TYPHOID, UTI, CARDIAC_CAD
    name = Column(String, nullable=False)                          # e.g. "Dengue Fever"
    category = Column(String, nullable=False)                      # Infectious, Respiratory, Cardiovascular, Urinary
    common_symptoms = Column(Text, nullable=True)                  # JSON list of characteristic symptoms
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ModelVersion(Base):
    """Registry of trained models across hospital, regional, and global scopes."""
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, unique=True, index=True, nullable=False) # e.g. "TF-GenDisease-v1.0"
    scope = Column(String, nullable=False)                            # hospital | regional | global
    scope_id = Column(String, nullable=True)                          # hub_id or hospital_id if scoped
    disease_category = Column(String, nullable=True)                  # "General Multi-Condition" or specific
    metrics = Column(Text, nullable=True)                             # JSON: accuracy, top3_accuracy, f1, epsilon
    model_path = Column(String, nullable=True)
    status = Column(String, default="active")                         # active | training | archived | evaluating
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Privacy, Consent & Immutable Audit Logs ───────────────────────────────────

class ConsentRecord(Base):
    """Fine-grained institutional and patient consent records chained to audit logs."""
    __tablename__ = "consent_records"
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(String, index=True, nullable=False)
    patient_id = Column(Integer, index=True, nullable=True)
    consent_type = Column(String, nullable=False)            # FEDERATED_TRAINING_DEIDENTIFIED | CLINICAL_RESEARCH
    status = Column(String, default="granted")               # granted | revoked
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    hash = Column(String, nullable=True)


class AuditLog(Base):
    """Hash-chained audit trail: hash_n = SHA256(hash_{n-1} | timestamp | node | type | description)."""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=True)
    node_id = Column(String, nullable=True)
    event_type = Column(String)                              # training | prediction | encounter | auth | config | consent
    description = Column(String)
    timestamp_iso = Column(String)                           # exact string that was hashed
    prev_hash = Column(String)
    hash = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


# ── Backward-Compatibility Tables (Heart-Disease Model & Sessions Preserved) ──

class PatientPrediction(Base):
    """Existing heart disease risk predictions (preserved with zero data loss)."""
    __tablename__ = "patient_predictions"
    id = Column(Integer, primary_key=True, index=True)
    patient_identifier = Column(String, index=True)
    session_id = Column(String, nullable=True)
    hospital_id = Column(String, index=True, nullable=True)
    user_id = Column(Integer, index=True, nullable=True)
    age = Column(Integer)
    risk_score = Column(Float)
    confidence = Column(Float)
    explanation_text = Column(String, nullable=True)
    shap_values = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FLSession(Base):
    __tablename__ = "fl_sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    status = Column(String, default="running")               # running | Completed | failed
    current_round = Column(Integer, default=0)
    total_rounds = Column(Integer, default=20)
    global_accuracy = Column(Float, nullable=True)
    epsilon = Column(Float, nullable=True)                   # None = no DP guarantee
    config_json = Column(Text, nullable=True)
    dataset = Column(String, nullable=True)                  # cleveland | synthetic
    model_path = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class RoundMetric(Base):
    __tablename__ = "round_metrics"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    round = Column(Integer)
    accuracy = Column(Float)
    loss = Column(Float)
    epsilon = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class HospitalNode(Base):
    __tablename__ = "hospital_nodes"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    region = Column(String)
    status = Column(String, default="idle")                  # training | idle | offline
    dataset_size = Column(Integer, default=0)
    current_epoch = Column(Integer, default=0)
    total_epochs = Column(Integer, default=1)


class FairnessReport(Base):
    __tablename__ = "fairness_reports"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    overall_score = Column(Float)
    subgroup_data = Column(Text)
    flagged_issues = Column(Text)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())


class PrivacyReport(Base):
    __tablename__ = "privacy_reports"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    attack_success_with_dp = Column(Float)                   # MIA AUC, model trained with DP
    attack_success_without_dp = Column(Float)                # MIA AUC, identical run without DP
    privacy_resistance = Column(Float)                       # 1 - MIA advantage (with DP)
    epsilon = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    he_key_size = Column(Integer, default=0)
    paillier_enabled = Column(Boolean, default=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    jti = Column(String, unique=True, index=True, nullable=False)
    csrf_token = Column(String, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
