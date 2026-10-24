"""End-to-end training session (no web / DB dependencies, so it is unit-testable).

cohort -> train/test split -> non-IID hospitals -> hierarchical FL (SMPC [+HE], local DP-SGD)
       -> checkpoint -> privacy report (membership-inference, DP vs identical non-DP run)
       -> exact SHAP -> fairness audit.
"""
from __future__ import annotations
import os
import numpy as np
from sklearn.model_selection import train_test_split
from tefl import data as D, fl, nn, attacks, explain, fairness
from tefl.fl import FLConfig

ARTIFACT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts")
HOSPITAL_NAMES = ["General Hospital #4", "City Med Center", "Westside Clinic",
                  "Riverside Medical", "Northgate Clinic", "Lakeview Hospital", "Harbor Clinic"]

DEFAULTS = dict(rounds=20, n_hospitals=5, dp=True, noise_multiplier=2.0, clip=1.0, secure_agg=True,
                he=False, he_bits=1024, batch=8, lr=0.1, local_epochs=1, alpha=0.5, skew=0.5,
                data_source="auto", seed=0, target_epsilon=None)


def clean_config(user: dict | None) -> dict:
    c = {**DEFAULTS, **{k: v for k, v in (user or {}).items() if k in DEFAULTS}}
    c["rounds"] = int(min(max(c["rounds"], 1), 100))
    c["n_hospitals"] = int(min(max(c["n_hospitals"], 3), 7))
    c["noise_multiplier"] = float(min(max(c["noise_multiplier"], 0.3), 50))
    c["batch"] = int(min(max(c["batch"], 2), 64))
    c["lr"] = float(min(max(c["lr"], 1e-3), 1.0))
    c["clip"] = float(min(max(c["clip"], 0.1), 10.0))
    c["local_epochs"] = int(min(max(c["local_epochs"], 1), 5))
    if c.get("target_epsilon") is not None:
        c["target_epsilon"] = float(min(max(c["target_epsilon"], 0.1), 50))
    c["he_bits"] = int(c["he_bits"]) if int(c["he_bits"]) in (512, 1024, 2048) else 1024
    return c


def run_session(session_id: str, user_cfg: dict | None = None, on_round=None) -> dict:
    c = clean_config(user_cfg)
    coh = D.load_cohort(c["data_source"], seed=c["seed"])
    idx = np.arange(len(coh.y))
    tr, te = train_test_split(idx, test_size=0.2, stratify=coh.y, random_state=c["seed"])
    sc = D.Standardizer().fit(coh.X[tr])
    Xtr, Xte, ytr, yte = sc.transform(coh.X[tr]), sc.transform(coh.X[te]), coh.y[tr], coh.y[te]
    rng = np.random.default_rng(c["seed"])
    K = c["n_hospitals"]
    asg, h = D.partition_train(ytr, coh.age[tr], K, c["alpha"], c["skew"], rng)
    hosp = [(Xtr[h == k], ytr[h == k]) for k in range(K)]
    hubs = fl.default_hubs(K)
    cfg = FLConfig(rounds=c["rounds"], local_epochs=c["local_epochs"], batch=c["batch"], lr=c["lr"],
                   clip=c["clip"] if c["dp"] else None, sigma=c["noise_multiplier"] if c["dp"] else 0.0,
                   secagg=c["secure_agg"], he=c["he"] and c["secure_agg"], he_bits=c["he_bits"],
                   hubs=hubs, seed=c["seed"] + 1)
    if c["dp"] and c.get("target_epsilon"):
        from dataclasses import replace
        cfg = replace(cfg, sigma=fl.calibrate_sigma(cfg, [len(y) for _, y in hosp], float(c["target_epsilon"])))
        c["noise_multiplier"] = cfg.sigma
    res = fl.run_federated(hosp, Xte, yte, cfg, on_round=on_round)

    # privacy: identical run without DP as the comparison point
    ref_cfg = FLConfig(**{**cfg.__dict__, "clip": None, "sigma": 0.0, "secagg": False, "he": False})
    ref = fl.run_federated(hosp, Xte, yte, ref_cfg)
    mia = attacks.loss_threshold_mia(res.theta, Xtr, ytr, Xte, yte)
    mia_ref = attacks.loss_threshold_mia(ref.theta, Xtr, ytr, Xte, yte)
    privacy = {"mia_auc_model": mia["auc"], "mia_auc_reference": mia_ref["auc"],
               "mia_adv_model": mia["advantage"], "mia_adv_reference": mia_ref["advantage"],
               "epsilon": float(res.epsilon) if np.isfinite(res.epsilon) else None, "delta": cfg.delta,
               "dp_enabled": bool(c["dp"]), "he_enabled": bool(cfg.he), "he_bits": cfg.he_bits if cfg.he else 0,
               "privacy_resistance": float(1 - mia["advantage"]),
               "reference_accuracy": ref.history[-1]["accuracy"]}

    # fairness on the held-out test set
    pred = nn.predict_proba(res.theta, Xte).argmax(1)
    S = explain.shap_matrix(res.theta, Xte)
    te_site = asg.assign(yte, coh.age[te], np.random.default_rng(c["seed"] + 5))
    attrs = {"Sex": np.where(coh.sex[te] == 1, "Male", "Female"), "Age": fairness.age_group(coh.age[te]),
             "Site": np.array([f"Hospital {s + 1}" for s in te_site])}
    fair = fairness.audit(yte, pred, S, attrs, np.random.default_rng(0), n_perm=300)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    path = os.path.join(ARTIFACT_DIR, f"{session_id}.npz")
    np.savez(path, theta=res.theta, mu=sc.mu, sd=sc.sd, dataset=coh.name)

    hospitals = [{"id": str(k + 1), "name": HOSPITAL_NAMES[k], "region": "East" if k in hubs[0] else "West",
                  "dataset_size": int(len(hosp[k][1]))} for k in range(K)]
    return {"config": c, "dataset": coh.name, "history": res.history, "epsilon": privacy["epsilon"],
            "final_accuracy": res.history[-1]["accuracy"], "hospitals": hospitals, "privacy": privacy,
            "fairness": fair, "model_path": path, "seconds": res.seconds}
