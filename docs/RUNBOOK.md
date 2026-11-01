# TrustFed-Health Operations Runbook

**System Version:** 2.0.0  
**Effective Date:** November 2026  
**Classification:** Operational Runbook (HIPAA / SOC 2 / GDPR Aligned)  
**Security Contact:** security@trustfed.ai  
**DevOps On-Call:** devops@trustfed.ai  

---

## Table of Contents

1. [Emergency Contacts & Incident Escalation Matrix](#1-emergency-contacts--incident-escalation-matrix)
2. [First 24-Hour Post-Launch Checklist](#2-first-24-hour-post-launch-checklist)
3. [Outage & Incident Response Procedure](#3-outage--incident-response-procedure)
4. [Database Backup & Disaster Recovery Drill](#4-database-backup--disaster-recovery-drill)
5. [Cryptographic Key Rotation Runbook](#5-cryptographic-key-rotation-runbook)
6. [Model Rollback Procedure](#6-model-rollback-procedure)
7. [Deployment Rollback Procedure](#7-deployment-rollback-procedure)
8. [Uptime & Model Drift Monitoring Runbook](#8-uptime--model-drift-monitoring-runbook)

---

## 1. Emergency Contacts & Incident Escalation Matrix

| Role | Contact Email | Escalation Responsibility | Response SLA |
|---|---|---|---|
| **Incident Commander** | `incident-lead@trustfed.ai` | Overall coordination, status communications | < 15 minutes |
| **Security Officer** | `security@trustfed.ai` | Breach investigation, key rotation, PHI containment | < 15 minutes |
| **DevOps / Infra Lead** | `devops@trustfed.ai` | Render hosting, PostgreSQL DB, rollback operations | < 15 minutes |
| **Clinical Lead / ML** | `clinical-ml@trustfed.ai` | Model drift, red-flag override audit, algorithm safety | < 1 hour |
| **Hospital Node Liaison**| `regional-ops@trustfed.ai`| Hospital tenant coordination, federation schedules | < 2 hours |

---

## 2. First 24-Hour Post-Launch Checklist

Execute this checklist immediately following any production deployment or major version upgrade:

- [ ] **T+0 min (Sanity Verification)**:
  - Run `curl -I https://trustfed-backend.onrender.com/health` (Confirm `200 OK`, `Strict-Transport-Security`, `mode: "informational"`).
  - Run `curl https://trustfed-backend.onrender.com/ready` (Confirm `status: "ready"`, `database: "connected"`, `model: "loaded"`).
  - Check `/.well-known/security.txt` resolves with `text/plain`.
- [ ] **T+30 min (Telemetry & Uptime Verification)**:
  - Verify UptimeRobot / Better Stack checks on `/health` and `/ready` report green status (p95 latency < 500ms).
  - Verify Sentry error tracking receives zero unhandled exceptions.
  - Query `/api/metrics` to ensure inference p95 latency is tracked.
- [ ] **T+2 hours (Log Redaction Audit)**:
  - Inspect Render real-time log stream: verify zero patient names, zero phone numbers, and zero unredacted bearer tokens appear.
  - Verify request IDs are present on every log entry (`[req:<uuid>]`).
- [ ] **T+6 hours (Model Monitoring & Safety Check)**:
  - Query `GET /api/v1/model/monitoring`:
    - Confirm mean top-1 confidence is $\ge 50\%$.
    - Confirm red-flag override share is $\le 30\%$.
    - Confirm zero active drift alerts.
- [ ] **T+12 hours (Disaster Recovery Verification)**:
  - Run `scripts/restore_drill.sh` against database backup to confirm snapshot integrity across all 16 tables.
- [ ] **T+24 hours (Sign-off & Stabilization)**:
  - Incident Commander and Clinical ML Lead sign off on system health and transition to standard on-call rotation.

---

## 3. Outage & Incident Response Procedure

### Severity Levels
- **SEV-1 (Critical)**: Complete outage (HTTP 5xx on `/health` or `/ready`), data corruption, or suspected PHI breach. Immediate escalation to Incident Commander.
- **SEV-2 (Major)**: Partial degradation (latency > 1500ms, fallback model invoked continuously, failed logins spiking).
- **SEV-3 (Minor)**: Non-blocking bug, single tenant issue, UI rendering glitch.

### Incident Workflow
```
[ALERT TRIGGERED] 
       │
       ▼
1. Triage & Acknowledge (< 15 min)
   - Check /health and /ready response codes.
   - Inspect Render logs for stack traces or OOM events.
       │
       ▼
2. Containment (< 30 min)
   - If suspected breach: Revoke tokens via `POST /api/admin/purge-deleted` or rotate JWT keys.
   - If bad deploy: Rollback commit immediately (Section 7).
   - If DB failure: Trigger PITR or restore drill backup (Section 4).
       │
       ▼
3. Resolution & Post-Mortem (< 48 hrs)
   - Re-verify cryptographic audit chain (`services.store.verify_chain()`).
   - Publish incident post-mortem documenting root cause, timeline, and remediation.
```

---

## 4. Database Backup & Disaster Recovery Drill

### Automated Daily Snapshots
TrustFed executes daily automated cryptographic snapshots storing full DB state in `backups/trustfed_backup_YYYYMMDD_HHMMSS.db` or managed PostgreSQL WAL archives.

### Executing the Disaster Recovery Drill
To test restore capability against any copy:
```bash
# 1. Execute automated restore drill script
python scripts/restore_drill.py

# Expected Output:
# [STEP 1] Generating atomic database backup snapshot...
# [SUCCESS] Snapshot generated: backups/trustfed_backup_YYYYMMDD_HHMMSS.db
# [STEP 2] Simulating disaster recovery: Restoring snapshot into target copy...
# [SUCCESS] Target copy initialized: backups/trustfed_restored_YYYYMMDD_HHMMSS.db
# [STEP 3] Comparing row counts across all 16 tenant & clinical tables...
# regional_hubs         | MATCH
# hospitals             | MATCH
# users                 | MATCH
# patients              | MATCH
# encounters            | MATCH
# audit_logs            | MATCH
# [DRILL RESULT: PASS] 100% data integrity confirmed.
```

### Manual Emergency Database Restore (PostgreSQL / Render)
1. Open Render Dashboard $\to$ PostgreSQL Instance $\to$ **Backups**.
2. Select the desired Point-In-Time recovery point or automated snapshot.
3. Click **Restore to New Database**.
4. Update `DATABASE_URL` in the Web Service Environment Variables with the restored connection string.
5. Service restarts automatically; verify `/ready` returns `200 OK`.

---

## 5. Cryptographic Key Rotation Runbook

TrustFed supports zero-downtime key rotation for both symmetric data encryption and token signatures.

### MultiFernet PHI Key Rotation
1. Generate new 32-byte URL-safe base64 Fernet key:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
2. Update `ENCRYPTION_KEY_RING` environment variable on the host:
   ```text
   # Format: "<new_primary_key>,<old_secondary_key>"
   ENCRYPTION_KEY_RING="v2_new_key...,v1_old_key..."
   ```
3. Restart backend or redeploy. MultiFernet decrypts legacy records using `v1_old_key` and encrypts all new records using `v2_new_key`.
4. Run re-encryption drill:
   ```bash
   python scripts/rotation_drill.py
   ```

### JWT Signing Key (`kid`) Rotation
1. Define a new Key ID (e.g. `key-2026-v2`) and high-entropy secret.
2. Update environment variables:
   ```text
   JWT_KEY_RING='{"key-2026-v2": "new_secret_key_string...", "key-2026-v1": "old_secret_key_string..."}'
   JWT_ACTIVE_KID="key-2026-v2"
   ```
3. Tokens signed under `key-2026-v1` remain valid until expiration (15 minutes). All new tokens are signed with `key-2026-v2`.

---

## 6. Model Rollback Procedure

When model drift is detected, top-1 confidence drops below 50%, or a bad federated weight update occurs:

### Immediate In-Memory Rollback to Pretrained Baseline
1. Trigger fallback model activation via environment variable or API:
   - Set `FORCE_MODEL_FALLBACK=true` in Render environment variables.
   - Or restart backend (`backend/services/general_disease_model.py` falls back automatically if model corruption is detected).
2. The system serves curated remedies and pre-trained baseline weights (`pretrained_cleveland.npz`).
3. Verify `/ready` returns `model: "loaded"`.

### Reverting to Previous Federated Session
1. Connect to DB or API as `global_admin`.
2. Inspect model versions: `GET /api/v1/fl/sessions`.
3. Rollback active session pointer:
   ```python
   # Via Python shell or admin endpoint:
   from db.database import SessionLocal
   from db import models
   db = SessionLocal()
   # Mark failing session as failed
   bad_session = db.query(models.FLSession).filter_by(session_id="FL-2026-XXX").first()
   bad_session.status = "reverted"
   db.commit()
   ```

---

## 7. Deployment Rollback Procedure

### Render Backend Instant Rollback
1. Navigate to **Render Dashboard** $\to$ `trustfed-backend` $\to$ **Events**.
2. Locate the last known healthy deployment commit hash.
3. Click the three dots menu ($\dots$) $\to$ **Rollback to this deploy**.
4. Rollback takes ~45 seconds (zero downtime container switch).
5. Verify `/health` and `/ready` probes return `200 OK`.

### Vercel Frontend Instant Rollback
1. Navigate to **Vercel Dashboard** $\to$ `frontend-3qgo` $\to$ **Deployments**.
2. Find the previous green deployment.
3. Click ($\dots$) $\to$ **Instant Rollback**.
4. Traffic is routed instantly to the previous build.

### Git Revert (Permanent Fix)
```bash
git revert HEAD -m "revert: rollback bad deploy"
git push origin main
```

---

## 8. Uptime & Model Drift Monitoring Runbook

### Uptime Monitoring Setup (UptimeRobot / Better Stack)
1. Configure HTTP Monitor 1:
   - **URL**: `https://trustfed-backend.onrender.com/health`
   - **Interval**: 5 minutes
   - **Keyword Assertion**: `"status":"healthy"`
2. Configure HTTP Monitor 2:
   - **URL**: `https://trustfed-backend.onrender.com/ready`
   - **Interval**: 5 minutes
   - **Keyword Assertion**: `"status":"ready"`
3. Alert Contacts: `ops-alerts@trustfed.ai`, Slack webhook `#trustfed-alerts`.

### Sentry Error Tracking Setup
1. Create project on Sentry: `trustfed-backend`.
2. Add environment variable to Render:
   `SENTRY_DSN="https://<public_key>@o<org>.ingest.sentry.io/<project_id>"`
3. Trigger test event to verify PHI scrubber:
   ```bash
   curl -s https://trustfed-backend.onrender.com/api/v1/monitoring/sentry-test
   ```

### Responding to Model Drift Alerts
When `GET /api/v1/model/monitoring` returns `drift_status.has_alerts = true`:
1. Check alerting metric:
   - **`top1_mean_confidence < 0.50`**: Check for unexpected input values or out-of-distribution symptom descriptions. Consider retraining or activating baseline fallback.
   - **`red_flag_override_share > 0.30`**: Clinical review required. Check if automated emergency red-flag triggers are generating false alarms.
2. Export daily metrics for clinical review team via `GET /api/v1/model/monitoring`.
