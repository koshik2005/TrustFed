import datetime, json, os, uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db import models
from services import auth, inference, store
from services.explanation import generate_clinical_explanation

router = APIRouter()
RESULTS_DIR = os.getenv(
    "RESULTS_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "results")
)
if not os.path.exists(RESULTS_DIR):
    _local_results = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "results")
    if os.path.exists(_local_results):
        RESULTS_DIR = _local_results


# ── auth ────────────────────────────────────────────────────────────────────
def current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> models.User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    try:
        claims = auth.decode_token(authorization.split(" ", 1)[1])
    except ValueError as e:
        raise HTTPException(401, str(e))
    u = db.query(models.User).filter_by(email=claims.get("sub")).first()
    if not u:
        raise HTTPException(401, "Unknown user")
    return u


def require(*roles: str):
    def dep(u: models.User = Depends(current_user)):
        if u.role not in roles:
            raise HTTPException(403, f"Role '{u.role}' may not access this resource")
        return u
    return dep

ANY = ("hospital_staff", "regional_admin", "global_admin")
ADMINS = ("regional_admin", "global_admin")


class LoginBody(BaseModel):
    email: str
    password: str


def _user_json(u):
    return {"id": str(u.id), "name": u.name, "email": u.email, "role": u.role, "hospitalId": u.hospital_id}


@router.post("/auth/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    u = db.query(models.User).filter_by(email=body.email.strip().lower()).first()
    if not u or not auth.verify_password(body.password, u.password_hash):
        store.add_audit(db, None, body.email[:60], "auth", "Failed login attempt")
        raise HTTPException(401, "Invalid email or password")
    store.add_audit(db, None, u.email, "auth", f"Login ({u.role})")
    return {"token": auth.create_token({"sub": u.email, "role": u.role}), "user": _user_json(u)}


@router.get("/auth/me")
def me(u: models.User = Depends(current_user)):
    return _user_json(u)

# ── training ────────────────────────────────────────────────────────────────
def _session_json(db, s: models.FLSession):
    metrics = db.query(models.RoundMetric).filter_by(session_id=s.session_id).order_by(models.RoundMetric.round).all()
    hospitals = db.query(models.HospitalNode).all()
    return {"sessionId": s.session_id, "status": s.status, "currentRound": s.current_round or 0,
            "totalRounds": s.total_rounds, "startedAt": str(s.started_at), "globalAccuracy": s.global_accuracy,
            "privacyBudget": s.epsilon, "dataset": s.dataset, "error": s.error,
            "metrics": [{"round": m.round, "accuracy": m.accuracy, "loss": m.loss, "epsilon": m.epsilon or 0,
                         "timestamp": str(m.timestamp)} for m in metrics],
            "hospitals": [_hosp_json(h) for h in hospitals]}


def _hosp_json(n):
    return {"id": n.id, "name": n.name, "region": n.region, "status": n.status,
            "localDatasetSize": n.dataset_size, "currentEpoch": n.current_epoch, "totalEpochs": n.total_epochs}


@router.get("/training/sessions/latest")
def latest_session(db: Session = Depends(get_db), u=Depends(require(*ANY))):
    s = db.query(models.FLSession).order_by(models.FLSession.id.desc()).first()
    if not s:
        return {"sessionId": "none", "status": "idle", "currentRound": 0, "totalRounds": 0,
                "startedAt": str(datetime.datetime.now()), "metrics": [], "hospitals": []}
    return _session_json(db, s)


@router.get("/training/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db), u=Depends(require(*ANY))):
    s = db.query(models.FLSession).filter_by(session_id=session_id).first()
    if not s:
        raise HTTPException(404, "Session not found")
    return _session_json(db, s)


@router.get("/training/sessions/{session_id}/metrics")
def session_metrics(session_id: str, db: Session = Depends(get_db), u=Depends(require(*ANY))):
    s = db.query(models.FLSession).filter_by(session_id=session_id).first()
    if not s:
        raise HTTPException(404, "Session not found")
    return _session_json(db, s)["metrics"]


@router.post("/training/sessions")
def start_training(config: Dict[str, Any], db: Session = Depends(get_db), u=Depends(require("global_admin"))):
    running = db.query(models.FLSession).filter_by(status="running").first()
    if running:
        raise HTTPException(409, f"Session {running.session_id} is already running")
    s = store.new_session(db, config)
    store.start_job(s.session_id, json.loads(s.config_json))
    return _session_json(db, s)


@router.get("/training/hospitals")
def hospitals(db: Session = Depends(get_db), u=Depends(require(*ANY))):
    return [_hosp_json(h) for h in db.query(models.HospitalNode).order_by(models.HospitalNode.id).all()]


def _load_results():
    for name in ("results.json", "results_cleveland.json", "results_synthetic.json"):
        p = os.path.join(RESULTS_DIR, name)
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    return None


@router.get("/training/comparison")
def comparison(u=Depends(require("global_admin", "regional_admin"))):
    """Benchmark table computed by `python -m tefl.run_experiments` (real measurements, not literals)."""
    R = _load_results()
    if not R:
        return []
    fair = {k: v["score"] for k, v in R["audits"].items()}
    rows = []
    for name, s in R["summary"].items():
        mia = s["mia_auc"]["mean"] if s.get("mia_auc") else None
        status = "—" if mia is None else ("LOW" if mia < 0.54 else "MEDIUM" if mia < 0.58 else "HIGH")
        fkey = {"FedAvg (non-IID)": "FedAvg (non-IID)", "TEFL (sigma=2)": "TEFL (sigma=2)"}.get(name)
        rows.append({"name": name, "acc": f"{s['acc']['mean']:.1%}", "mia": "—" if mia is None else f"{mia:.3f}",
                     "miaStatus": status, "fairness": f"{fair[fkey]:.1%}" if fkey in fair else "—",
                     "time": f"{s['seconds']['mean']:.1f}s", "epsilon": None if not s.get("epsilon") else round(s["epsilon"]["mean"], 2),
                     "he": "Paillier" if "TEFL" in name else "—", "special": name == "TEFL (sigma=2)",
                     "dataset": R["dataset"]})
    return rows

# ── prediction ──────────────────────────────────────────────────────────────
def _active_model(db):
    s = (db.query(models.FLSession).filter(models.FLSession.status == "Completed")
         .order_by(models.FLSession.id.desc()).first())
    if not s or not s.model_path or not os.path.exists(s.model_path):
        raise HTTPException(409, "No trained model yet. A global admin must run a training session first.")
    return s, inference.load_model(s.model_path)


def _pred_json(p: models.PatientPrediction):
    return {"patientId": p.patient_identifier, "riskScore": p.risk_score,
            "riskLabel": inference.risk_label(p.risk_score), "confidence": p.confidence,
            "nlpExplanation": p.explanation_text, "shapValues": json.loads(p.shap_values or "[]"),
            "predictedAt": str(p.created_at)}


@router.post("/prediction/predict")
def predict(vitals: Dict[str, Any], db: Session = Depends(get_db), u=Depends(require(*ANY))):
    s, model = _active_model(db)
    try:
        r = inference.predict(model, vitals)
    except ValueError as e:
        raise HTTPException(422, str(e))
    text = generate_clinical_explanation(vitals, r["riskScore"], r["shapValues"])
    pid = uuid.uuid4().hex[:8].upper()                  # anonymised identifier, never a real MRN
    row = models.PatientPrediction(patient_identifier=pid, session_id=s.session_id, age=int(float(vitals["age"])),
                                   risk_score=r["riskScore"], confidence=r["confidence"], explanation_text=text,
                                   shap_values=json.dumps(r["shapValues"]))
    db.add(row); db.commit(); db.refresh(row)
    store.add_audit(db, s.session_id, u.email, "prediction", f"Risk prediction {pid}: {r['riskLabel']} ({r['riskScore']:.2f})")
    return _pred_json(row)


@router.get("/prediction/history")
def history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
            db: Session = Depends(get_db), u=Depends(require(*ANY))):
    q = db.query(models.PatientPrediction).order_by(models.PatientPrediction.id.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_pred_json(p) for p in items], "total": total, "page": page, "pageSize": page_size,
            "totalPages": max(1, -(-total // page_size))}


@router.get("/prediction/{patient_id}")
def prediction_by_id(patient_id: str, db: Session = Depends(get_db), u=Depends(require(*ANY))):
    p = db.query(models.PatientPrediction).filter_by(patient_identifier=patient_id).first()
    if not p:
        raise HTTPException(404, "Prediction not found")
    return _pred_json(p)

# ── TEFL reports ────────────────────────────────────────────────────────────
def _resolve_sid(db, sid):
    if sid in ("latest", "none"):
        s = db.query(models.FLSession).filter_by(status="Completed").order_by(models.FLSession.id.desc()).first()
        return s.session_id if s else sid
    return sid


@router.get("/tefl/fairness/{session_id}")
def fairness_report(session_id: str, db: Session = Depends(get_db), u=Depends(require(*ADMINS))):
    r = db.query(models.FairnessReport).filter_by(session_id=_resolve_sid(db, session_id)).first()
    if not r:
        raise HTTPException(404, "No fairness report: the session has not finished (or does not exist).")
    return {"sessionId": r.session_id, "overallScore": r.overall_score, "subgroupResults": json.loads(r.subgroup_data),
            "flaggedIssues": json.loads(r.flagged_issues), "generatedAt": str(r.generated_at)}


@router.get("/tefl/privacy/{session_id}")
def privacy_report(session_id: str, db: Session = Depends(get_db), u=Depends(require(*ADMINS))):
    r = db.query(models.PrivacyReport).filter_by(session_id=_resolve_sid(db, session_id)).first()
    if not r:
        raise HTTPException(404, "No privacy report: the session has not finished (or does not exist).")
    return {"sessionId": r.session_id, "attackSuccessWithDP": r.attack_success_with_dp,
            "attackSuccessWithoutDP": r.attack_success_without_dp, "privacyResistance": r.privacy_resistance,
            "epsilon": r.epsilon, "delta": r.delta, "heKeySize": r.he_key_size,
            "paillierEnabled": r.paillier_enabled, "generatedAt": str(r.generated_at)}

# ── audit ───────────────────────────────────────────────────────────────────
@router.get("/audit/logs")
def audit_logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200), eventType: Optional[str] = None,
               db: Session = Depends(get_db), u=Depends(require(*ADMINS))):
    q = db.query(models.AuditLog)
    if eventType:
        q = q.filter(models.AuditLog.event_type == eventType)
    q = q.order_by(models.AuditLog.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [{"id": str(r.id), "timestamp": r.timestamp_iso, "nodeId": r.node_id or "—", "eventType": r.event_type,
                       "description": r.description, "hash": r.hash} for r in rows],
            "total": total, "page": page, "pageSize": page_size, "totalPages": max(1, -(-total // page_size))}


@router.get("/audit/verify")
def audit_verify(db: Session = Depends(get_db), u=Depends(require(*ADMINS))):
    return store.verify_chain(db)
