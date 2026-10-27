"""DB helpers: users, hash-chained audit log, background training job."""
from __future__ import annotations
import datetime, json, os, threading, traceback
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db import models
from . import auth, pipeline

DEMO_USERS = [
    ("hospital@trustfed.ai", "Dr. Hospital Staff", "hospital_staff", "1"),
    ("regional@trustfed.ai", "Regional Admin", "regional_admin", None),
    ("admin@trustfed.ai", "Global Admin", "global_admin", None),
]
_audit_lock = threading.Lock()


def seed_users(db: Session):
    env = os.getenv("ENVIRONMENT", "development").strip().lower()
    is_prod = env in ("production", "prod") or bool(os.getenv("RENDER"))
    if is_prod:
        # NEVER seed demo users in production. Disable any legacy demo accounts using default password.
        import secrets
        for email, _, _, _ in DEMO_USERS:
            existing = db.query(models.User).filter_by(email=email).first()
            if existing and auth.verify_password("password123", existing.password_hash):
                existing.password_hash = f"DISABLED${secrets.token_hex(32)}"
                db.commit()
                print(f"[SECURITY] Disabled un-rotated demo account in production: {email}")
        print("[INFO] Production mode active: demo user seeding skipped.")
        return

    pw = os.getenv("DEMO_PASSWORD", "password123")
    for email, name, role, hid in DEMO_USERS:
        if not db.query(models.User).filter_by(email=email).first():
            db.add(models.User(email=email, name=name, role=role, hospital_id=hid,
                               password_hash=auth.hash_password(pw)))
    db.commit()
    if pw == "password123":
        print("[WARN] Demo users use default password. Set DEMO_PASSWORD in .env for non-local environments.")


def add_audit(db: Session, session_id, node_id, event_type, description) -> models.AuditLog:
    with _audit_lock:                                   # keep the chain linear
        last = db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).first()
        prev = last.hash if last else auth.GENESIS
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        row = models.AuditLog(session_id=session_id, node_id=node_id, event_type=event_type,
                              description=description, timestamp_iso=ts, prev_hash=prev,
                              hash=auth.audit_hash(prev, ts, node_id or "", event_type, description))
        db.add(row); db.commit(); db.refresh(row)
        return row


def verify_chain(db: Session) -> dict:
    prev, n = auth.GENESIS, 0
    for r in db.query(models.AuditLog).order_by(models.AuditLog.id.asc()).all():
        n += 1
        if r.prev_hash != prev or r.hash != auth.audit_hash(prev, r.timestamp_iso, r.node_id or "", r.event_type, r.description):
            return {"valid": False, "checked": n, "firstBadId": r.id}
        prev = r.hash
    return {"valid": True, "checked": n, "firstBadId": None}


def new_session(db: Session, cfg: dict) -> models.FLSession:
    cfg = pipeline.clean_config(cfg)
    s = models.FLSession(session_id="pending", status="running", current_round=0,
                         total_rounds=cfg["rounds"], config_json=json.dumps(cfg))
    db.add(s); db.flush()
    s.session_id = f"FL-{datetime.date.today().year}-{s.id:03d}"
    db.commit(); db.refresh(s)
    return s


def _train_job(session_id: str, cfg: dict):
    db = SessionLocal()
    try:
        add_audit(db, session_id, "GlobalServer", "training", f"Session started: {cfg['rounds']} rounds, "
                  f"{cfg['n_hospitals']} hospitals, DP={cfg['dp']}, SMPC={cfg['secure_agg']}, HE={cfg['he']}")
        for h in db.query(models.HospitalNode).all():
            h.status = "training"
        db.commit()

        def on_round(r, m, theta):
            db.add(models.RoundMetric(session_id=session_id, round=r, accuracy=m["accuracy"],
                                      loss=m["loss"], epsilon=m["epsilon"]))
            s = db.query(models.FLSession).filter_by(session_id=session_id).first()
            s.current_round, s.global_accuracy, s.epsilon = r, m["accuracy"], m["epsilon"]
            for h in db.query(models.HospitalNode).all():
                h.current_epoch = r
            db.commit()
            if r % 5 == 0 or r == cfg["rounds"]:
                add_audit(db, session_id, "GlobalServer", "training",
                          f"Secure aggregation round {r}: acc={m['accuracy']:.3f}"
                          + (f", eps={m['epsilon']:.2f}" if m["epsilon"] else ""))

        out = pipeline.run_session(session_id, cfg, on_round=on_round)
        # hospital registry (sizes come from the real partition)
        db.query(models.HospitalNode).delete()
        for hd in out["hospitals"]:
            db.add(models.HospitalNode(id=hd["id"], name=hd["name"], region=hd["region"], status="idle",
                                       dataset_size=hd["dataset_size"], current_epoch=cfg["rounds"], total_epochs=cfg["rounds"]))
        p, f = out["privacy"], out["fairness"]
        db.add(models.PrivacyReport(session_id=session_id, attack_success_with_dp=p["mia_auc_model"],
                                    attack_success_without_dp=p["mia_auc_reference"],
                                    privacy_resistance=p["privacy_resistance"], epsilon=p["epsilon"], delta=p["delta"],
                                    he_key_size=p["he_bits"], paillier_enabled=p["he_enabled"]))
        sub = [{"subgroup": f"{r['attribute']}: {r['subgroup']}", "accuracy": r["accuracy"], "sampleSize": r["n"],
                "divergenceScore": r["shap_divergence"], "shapP": r["shap_p"], "topFeatures": r["top_features"],
                "tpr": r["tpr"], "fpr": r["fpr"]} for r in f["subgroups"]]
        db.add(models.FairnessReport(session_id=session_id, overall_score=f["score"],
                                     subgroup_data=json.dumps(sub), flagged_issues=json.dumps(f["flags"])))
        s = db.query(models.FLSession).filter_by(session_id=session_id).first()
        s.status, s.dataset, s.model_path = "Completed", out["dataset"], out["model_path"]
        s.global_accuracy, s.epsilon = out["final_accuracy"], out["epsilon"]
        s.completed_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        add_audit(db, session_id, "GlobalServer", "training", f"Session completed: acc={out['final_accuracy']:.3f}, dataset={out['dataset']}")
        add_audit(db, session_id, "GlobalServer", "tefl", f"Privacy audit: MIA AUC {p['mia_auc_model']:.3f} (model) vs {p['mia_auc_reference']:.3f} (no-DP reference)")
        add_audit(db, session_id, "GlobalServer", "tefl", f"Fairness audit: score {f['score']:.3f}, {len(f['flags'])} flag(s)")
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        s = db.query(models.FLSession).filter_by(session_id=session_id).first()
        if s:
            s.status, s.error = "failed", str(e)[:500]
            db.commit()
        add_audit(db, session_id, "GlobalServer", "training", f"Session FAILED: {str(e)[:200]}")
    finally:
        db.close()


def start_job(session_id: str, cfg: dict):
    t = threading.Thread(target=_train_job, args=(session_id, pipeline.clean_config(cfg)), daemon=True)
    t.start()
    return t
