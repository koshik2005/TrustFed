# Disaster Recovery, Automated Backups & Restore Verification Drill

This document outlines the backup policies, Point-In-Time Recovery (PITR) procedures, and recovery verification drills for the **TrustFed** platform.

---

## 1. Backup Strategy Overview

TrustFed employs a defense-in-depth backup strategy to protect institutional patient data, consent records, and immutable audit logs:

| Level | Mechanism | Frequency | Retention | RPO / RTO Target |
| :--- | :--- | :--- | :--- | :--- |
| **PITR (Continuous)** | PostgreSQL Write-Ahead Log (WAL) streaming | Continuous | 7 to 14 days | RPO: < 1 minute<br>RTO: < 15 minutes |
| **Automated Snapshots** | Managed Cloud DB Daily Snapshots (Supabase / RDS) | Daily at 02:00 UTC | 30 days | RPO: < 24 hours<br>RTO: < 30 minutes |
| **Audit Ledger Verification** | Cryptographic hash-chain integrity verification | On every transaction & startup | Permanent | Zero tampering permitted |
| **Automated Restore Drill** | `scripts/restore_drill.sh` executed against copy database | Automated test & deployment pipeline | Verified per drill | Proves 100% restoration |

---

## 2. Point-In-Time Recovery (PITR)

### Supported Cloud Environments:
- **Supabase (AWS Mumbai `ap-south-1` / `ap-northeast-2`)**:
  - Uses `WAL-G` for continuous archiving of PostgreSQL WAL segments to encrypted S3 storage.
  - Recovery to any second within the retention window via Supabase Dashboard -> **Database** -> **Backups** -> **Restore to Point in Time**.
- **AWS RDS / Aurora**:
  - Continuous snapshotting + transaction log archiving.
  - Point-in-time recovery via AWS Console or CLI:
    ```bash
    aws rds restore-db-instance-to-point-in-time \
      --source-db-instance-identifier trustfed-prod \
      --target-db-instance-identifier trustfed-restored-copy \
      --restore-time 2026-11-01T10:00:00Z
    ```

---

## 3. Restore Verification Drill (`scripts/restore_drill.sh`)

To guarantee backups are not just created, but are **provably restorable**, TrustFed includes an automated drill script: [`scripts/restore_drill.sh`](file:///d:/projects/TrustFed/scripts/restore_drill.sh) (and [`scripts/restore_drill.py`](file:///d:/projects/TrustFed/scripts/restore_drill.py)).

### Procedure:
1. Takes an online atomic snapshot of the primary database.
2. Restores the snapshot into an isolated target copy database.
3. Queries row counts for all 16 tenant, clinical, and audit tables in both source and restored target.
4. Compares table-by-table to prove zero data loss.

### Command Execution:
```bash
./scripts/restore_drill.sh
```

### Verified Table Count Evidence:
```
TABLE NAME                 | SOURCE     | RESTORED   | STATUS    
-----------------------------------------------------------------
regional_hubs              | 12         | 12         | MATCH     
hospitals                  | 19         | 19         | MATCH     
users                      | 41         | 41         | MATCH     
patients                   | 185        | 185        | MATCH     
encounters                 | 182        | 182        | MATCH     
diseases                   | 7          | 7          | MATCH     
model_versions             | 45         | 45         | MATCH     
consent_records            | 4          | 4          | MATCH     
audit_logs                 | 2042       | 2042       | MATCH     
patient_predictions        | 2          | 2          | MATCH     
fl_sessions                | 1          | 1          | MATCH     
round_metrics              | 0          | 0          | MATCH     
hospital_nodes             | 4          | 4          | MATCH     
fairness_reports           | 0          | 0          | MATCH     
privacy_reports            | 0          | 0          | MATCH     
refresh_tokens             | 501        | 501        | MATCH     
-----------------------------------------------------------------
TOTAL ROWS                 | 3045       | 3045       | MATCH     
```

---

## 4. Disaster Recovery Playbook

In the event of an outage, catastrophic host failure, or data corruption:
1. **Assess Incident Time**: Identify the exact timestamp before corruption occurred.
2. **Execute PITR**: Restore the database to `T - 5 minutes` into a new cluster.
3. **Run Restore Drill**: Execute `./scripts/restore_drill.sh` to confirm integrity.
4. **Update Connection String**: Point `SUPABASE_DB_URL` in the secrets manager to the restored cluster.
5. **Verify Readiness**: Query `GET /ready` to verify database and ML models report `"ready"`.

