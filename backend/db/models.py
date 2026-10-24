from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)            # hospital_staff | regional_admin | global_admin
    hospital_id = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)   # pbkdf2_sha256$iters$salt$hash
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FLSession(Base):
    __tablename__ = "fl_sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    status = Column(String, default="running")       # running | Completed | failed
    current_round = Column(Integer, default=0)
    total_rounds = Column(Integer, default=20)
    global_accuracy = Column(Float, nullable=True)
    epsilon = Column(Float, nullable=True)           # None = no DP guarantee
    config_json = Column(Text, nullable=True)
    dataset = Column(String, nullable=True)          # cleveland | synthetic
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


class PatientPrediction(Base):
    __tablename__ = "patient_predictions"
    id = Column(Integer, primary_key=True, index=True)
    patient_identifier = Column(String, index=True)
    session_id = Column(String, nullable=True)
    age = Column(Integer)
    risk_score = Column(Float)
    confidence = Column(Float)
    explanation_text = Column(String, nullable=True)
    shap_values = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Hash-chained audit trail: hash_n = SHA256(hash_{n-1} | timestamp | node | type | description)."""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=True)
    node_id = Column(String, nullable=True)
    event_type = Column(String)                      # training | prediction | tefl | auth | config
    description = Column(String)
    timestamp_iso = Column(String)                   # exact string that was hashed
    prev_hash = Column(String)
    hash = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class HospitalNode(Base):
    __tablename__ = "hospital_nodes"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    region = Column(String)
    status = Column(String, default="idle")          # training | idle | offline
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
    attack_success_with_dp = Column(Float)           # MIA AUC, model trained with DP
    attack_success_without_dp = Column(Float)        # MIA AUC, identical run without DP
    privacy_resistance = Column(Float)               # 1 - MIA advantage (with DP)
    epsilon = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    he_key_size = Column(Integer, default=0)
    paillier_enabled = Column(Boolean, default=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
