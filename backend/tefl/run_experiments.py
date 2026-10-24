"""Reproduce every number/figure in the paper.

    python -m tefl.run_experiments --data cleveland      # real UCI data (needs internet once)
    python -m tefl.run_experiments --data synthetic      # offline smoke run (NOT real patients)
"""
from __future__ import annotations
import argparse, json, os, time
import numpy as np
from sklearn.model_selection import StratifiedKFold
from . import data as D, nn, fl, attacks, explain, fairness, secagg
from .fl import FLConfig
from .metrics import accuracy, auc_score, f1

K, ALPHA, SKEW = 5, 0.5, 0.5
BASE = dict(rounds=20, local_epochs=1, batch=8, lr=0.1)
SIGMAS = [1.0, 2.0, 4.0, 8.0]
CLIP = 1.0


def evaluate(theta, Xte, yte):
    p = nn.predict_proba(theta, Xte)
    return {"acc": accuracy(yte, p.argmax(1)), "auc": auc_score(yte, p[:, 1]), "f1": f1(yte, p.argmax(1))}


def configs():
    c = {
        "FedAvg (IID)":                dict(cfg=FLConfig(**BASE), alpha=None),
        "FedAvg (non-IID)":            dict(cfg=FLConfig(**BASE), alpha=ALPHA),
        "FedAvg + SMPC":               dict(cfg=FLConfig(secagg=True, **BASE), alpha=ALPHA),
        "FedAvg (extended training)":  dict(cfg=FLConfig(**{**BASE, "rounds": 150}), alpha=ALPHA),
    }
    for s in SIGMAS:
        c[f"TEFL (sigma={s:g})"] = dict(cfg=FLConfig(secagg=True, clip=CLIP, sigma=s, **BASE), alpha=ALPHA)
    return c


def run(args):
    coh = D.load_cohort(args.data, seed=0)
    print(f"dataset={coh.name} n={len(coh.y)} prevalence={coh.y.mean():.3f}")
    cfgs = configs()
    records, curves = [], {k: [] for k in cfgs}
    audit_store = {"FedAvg (non-IID)": [], f"TEFL (sigma={args.audit_sigma:g})": []}
    hospital_sizes = []
    t_all = time.time()
    for rep in range(args.reps):
        skf = StratifiedKFold(5, shuffle=True, random_state=100 + rep)
        for fold, (tr, te) in enumerate(skf.split(coh.X, coh.y)):
            seed = 1000 * rep + 10 * fold
            sc = D.Standardizer().fit(coh.X[tr])
            Xtr, Xte, ytr, yte = sc.transform(coh.X[tr]), sc.transform(coh.X[te]), coh.y[tr], coh.y[te]
            age_tr, age_te, sex_te = coh.age[tr], coh.age[te], coh.sex[te]
            parts = {}
            for name, c in cfgs.items():
                a = c["alpha"]
                if a not in parts:
                    rng = np.random.default_rng(seed + (7 if a is None else 3))
                    asg, h = D.partition_train(ytr, age_tr, K, a, SKEW, rng)
                    parts[a] = (asg, h, rng)
                asg, h, prng = parts[a]
                hosp = [(Xtr[h == k], ytr[h == k]) for k in range(K)]
                cfg = FLConfig(**{**c["cfg"].__dict__, "seed": seed + 1})
                res = fl.run_federated(hosp, Xte, yte, cfg)
                m = evaluate(res.theta, Xte, yte)
                mia = attacks.loss_threshold_mia(res.theta, Xtr, ytr, Xte, yte)
                records.append({"method": name, "rep": rep, "fold": fold, **m,
                                "mia_auc": mia["auc"], "mia_adv": mia["advantage"],
                                "epsilon": None if not np.isfinite(res.epsilon) else res.epsilon,
                                "seconds": res.seconds, "agg_seconds": res.agg_seconds})
                if rep == 0:
                    curves[name].append([hh["accuracy"] for hh in res.history])
                if rep == 0 and name in audit_store:
                    te_h = asg.assign(yte, age_te, np.random.default_rng(seed + 99))
                    S = explain.shap_matrix(res.theta, Xte)
                    audit_store[name].append({"y": yte, "pred": nn.predict_proba(res.theta, Xte).argmax(1),
                                              "S": S, "age": age_te, "sex": sex_te, "site": te_h})
                if rep == 0 and name == "FedAvg (non-IID)":
                    hospital_sizes.append([int((h == k).sum()) for k in range(K)])
            # baselines on the non-IID partition
            asg, h, _ = parts[ALPHA]
            hosp = [(Xtr[h == k], ytr[h == k]) for k in range(K)]
            cfg = FLConfig(**{**BASE, "seed": seed + 1})
            r = fl.run_centralized(Xtr, ytr, Xte, yte, cfg, K)
            m = evaluate(r.theta, Xte, yte); mia = attacks.loss_threshold_mia(r.theta, Xtr, ytr, Xte, yte)
            records.append({"method": "Centralized (pooled)", "rep": rep, "fold": fold, **m,
                            "mia_auc": mia["auc"], "mia_adv": mia["advantage"], "epsilon": None,
                            "seconds": 0, "agg_seconds": 0})
            loc = [evaluate(t, Xte, yte) for t in fl.run_local_only(hosp, cfg)]
            records.append({"method": "Local-only (mean of sites)", "rep": rep, "fold": fold,
                            **{k: float(np.mean([l[k] for l in loc])) for k in ("acc", "auc", "f1")},
                            "mia_auc": None, "mia_adv": None, "epsilon": None, "seconds": 0, "agg_seconds": 0})
        print(f"rep {rep+1}/{args.reps} done  ({time.time()-t_all:.0f}s)")

    # ---- fairness audit on pooled out-of-fold predictions (rep 0) ----
    audits, shap_global = {}, {}
    for name, items in audit_store.items():
        y = np.concatenate([i["y"] for i in items]); pred = np.concatenate([i["pred"] for i in items])
        S = np.vstack([i["S"] for i in items]); age = np.concatenate([i["age"] for i in items])
        sex = np.concatenate([i["sex"] for i in items]); site = np.concatenate([i["site"] for i in items])
        attrs = {"Sex": np.where(sex == 1, "Male", "Female"), "Age": fairness.age_group(age),
                 "Site": np.array([f"Hospital {s+1}" for s in site])}
        audits[name] = fairness.audit(y, pred, S, attrs, np.random.default_rng(0), n_perm=args.perm)
        imp = np.abs(S).mean(0)
        shap_global[name] = {f: float(v) for f, v in zip(D.FEATURES, imp)}

    # ---- HE / SMPC overhead micro-benchmark (one aggregation round, 5 hospitals, 1010 params) ----
    rng = np.random.default_rng(0)
    vecs = [rng.standard_normal(nn.N_PARAMS + 1) * 20 for _ in range(K)]
    hubs = fl.default_hubs(K)
    bench = {}
    for label, kw in [("plain sum", {}), ("SMPC (additive shares)", dict(secagg=True))]:
        t = time.time(); [fl.aggregate(vecs, FLConfig(**kw), hubs, rng) for _ in range(20)]
        bench[label] = (time.time() - t) / 20
    for bits in args.he_bits:
        t = time.time(); pk = secagg.Paillier(bits); kg = time.time() - t
        t = time.time(); out = fl.aggregate(vecs, FLConfig(secagg=True, he=True, he_bits=bits), hubs, rng, pk)
        bench[f"SMPC + Paillier-{bits}"] = time.time() - t
        bench[f"Paillier-{bits} keygen"] = kg
        assert np.max(np.abs(out - np.sum(vecs, 0))) < 1e-5
    # ---- aggregate ----
    methods = list(dict.fromkeys(r["method"] for r in records))
    def stat(vals):
        v = [x for x in vals if x is not None]
        return None if not v else {"mean": float(np.mean(v)), "std": float(np.std(v, ddof=1)) if len(v) > 1 else 0.0}
    summary = {m: {k: stat([r[k] for r in records if r["method"] == m])
                   for k in ("acc", "auc", "f1", "mia_auc", "mia_adv", "epsilon", "seconds")} for m in methods}
    out = {"dataset": coh.name, "n": int(len(coh.y)), "prevalence": float(coh.y.mean()),
           "setup": {"K": K, "alpha": ALPHA, "skew": SKEW, "clip": CLIP, "sigmas": SIGMAS, **BASE,
                     "hubs": fl.default_hubs(K), "folds": 5, "reps": args.reps, "delta": 1e-5,
                     "hospital_sizes_mean": np.mean(hospital_sizes, 0).tolist(),
                     "n_params": nn.N_PARAMS},
           "summary": summary, "records": records, "audits": audits, "shap_global": shap_global,
           "he_benchmark_seconds": bench,
           "curves": {k: {"mean": np.mean(v, 0).tolist(), "std": np.std(v, 0).tolist()} for k, v in curves.items() if v}}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1, default=float)
    print(f"saved {args.out}  total {time.time()-t_all:.0f}s")
    for m in methods:
        s = summary[m]
        print(f"{m:34s} acc {s['acc']['mean']:.3f}±{s['acc']['std']:.3f} auc {s['auc']['mean']:.3f} "
              f"mia {s['mia_auc']['mean'] if s['mia_auc'] else float('nan'):.3f} "
              f"eps {s['epsilon']['mean'] if s['epsilon'] else float('nan'):.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="auto", choices=["auto", "cleveland", "synthetic"])
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--perm", type=int, default=500)
    ap.add_argument("--audit-sigma", type=float, default=2.0)
    ap.add_argument("--he-bits", type=int, nargs="+", default=[1024, 2048])
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "results", "results.json"))
    run(ap.parse_args())
