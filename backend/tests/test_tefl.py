"""Run:  python tests/test_tefl.py   (or pytest). No external services needed."""
import math, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tefl import nn, dp, secagg, explain, data, fairness, attacks
from tefl.fl import FLConfig, run_federated, aggregate


def test_gradients_match_finite_differences():
    rng = np.random.default_rng(1); th = nn.init_params(rng)
    X = rng.standard_normal((4, 13)); y = rng.integers(0, 2, 4)
    G = nn.per_example_grads(th, X, y)
    for i in rng.choice(nn.N_PARAMS, 25, replace=False):
        t = th.copy(); t[i] += 1e-6; a = nn.losses(t, X[:1], y[:1])[0]
        t[i] -= 2e-6; b = nn.losses(t, X[:1], y[:1])[0]
        assert abs((a - b) / 2e-6 - G[0, i]) < 1e-5


def test_accountant_reference_values():
    # q=1 reduces to the plain Gaussian mechanism: RDP = alpha / (2 sigma^2)
    assert abs(dp.rdp_sgm(1.0, 2.0, 8) - 1.0) < 1e-12
    # TF-Privacy MNIST benchmark (N=60000, B=256, sigma=1.1, 60 epochs, delta=1e-5): eps ~ 3.0 with the
    # classic conversion; the tight conversion used here must be a bit smaller but of the same order.
    q, T = 256 / 60000, int(60 * 60000 / 256)
    classic = min(T * dp.rdp_sgm(q, 1.1, a) + math.log(1e-5) * -1 / (a - 1) for a in dp.ORDERS)
    tight = dp.epsilon(q, 1.1, T, 1e-5)
    assert 2.8 < classic < 3.3 and 2.0 < tight < classic
    # monotonic: more noise -> less epsilon; more steps -> more epsilon
    assert dp.epsilon(0.1, 2.0, 100) < dp.epsilon(0.1, 1.0, 100) < dp.epsilon(0.1, 1.0, 400)


def test_secure_sum_is_exact_and_shares_look_random():
    rng = np.random.default_rng(0)
    vs = [rng.standard_normal(1010) * 50 for _ in range(3)]
    tot = secagg.decode(secagg.secure_sum(vs, rng))
    assert np.max(np.abs(tot - np.sum(vs, 0))) < 1e-6
    sh = secagg.share(secagg.encode(vs[0]), 3, rng)
    # a single share is uniform on the ring: top bit is ~50/50
    assert abs(((sh[0] >> np.uint64(63)).astype(float)).mean() - 0.5) < 0.06


def test_paillier_homomorphism_and_packing():
    pk = secagg.Paillier(512)
    a, b = 123456789, 987654321
    assert pk.decrypt(pk.add(pk.encrypt(a), pk.encrypt(b))) == a + b
    rng = np.random.default_rng(0)
    r1 = secagg.encode(rng.standard_normal(100) * 30); r2 = secagg.encode(rng.standard_normal(100) * 30)
    c = secagg.he_sum_ciphertexts(pk, [secagg.he_encrypt_vector(pk, r1), secagg.he_encrypt_vector(pk, r2)])
    got = secagg.he_decrypt_vector(pk, c, 100, 2)
    exp = r1.astype(np.int64) + r2.astype(np.int64)
    assert np.array_equal(got, exp)


def test_shap_efficiency_and_symmetry():
    rng = np.random.default_rng(0); th = nn.init_params(rng)
    x = rng.standard_normal(13)
    phi, delta = explain.shap_values(th, x)
    assert abs(phi.sum() - delta) < 1e-9                                  # efficiency
    assert abs(delta - (nn.logit_margin(th, x[None])[0] - nn.logit_margin(th, np.zeros((1, 13)))[0])) < 1e-9
    phi0, _ = explain.shap_values(th, np.zeros(13))
    assert np.max(np.abs(phi0)) < 1e-12                                    # x == baseline -> all zero


def test_federated_pipelines_agree():
    coh = data.make_synthetic(seed=1)
    rng = np.random.default_rng(0)
    sc = data.Standardizer().fit(coh.X); Xs = sc.transform(coh.X)
    asg, h = data.partition_train(coh.y, coh.age, 5, 1.0, 0.5, rng)
    hosp = [(Xs[h == k], coh.y[h == k]) for k in range(5)]
    base = dict(rounds=3, seed=3)
    r_plain = run_federated(hosp, Xs, coh.y, FLConfig(**base))
    r_sec = run_federated(hosp, Xs, coh.y, FLConfig(secagg=True, **base))
    r_he = run_federated(hosp, Xs, coh.y, FLConfig(secagg=True, he=True, he_bits=512, **base))
    assert np.max(np.abs(r_plain.theta - r_sec.theta)) < 1e-5
    assert np.max(np.abs(r_sec.theta - r_he.theta)) < 1e-9


def test_partition_has_both_classes_everywhere():
    coh = data.make_synthetic(seed=2); rng = np.random.default_rng(5)
    _, h = data.partition_train(coh.y, coh.age, 5, 0.5, 0.5, rng)
    for k in range(5):
        assert {0, 1} <= set(coh.y[h == k])


def test_mia_auc_is_half_for_random_model_and_high_for_memoriser():
    rng = np.random.default_rng(0)
    Xm, Xn = rng.standard_normal((200, 13)), rng.standard_normal((200, 13))
    ym, yn = rng.integers(0, 2, 200), rng.integers(0, 2, 200)
    th = nn.init_params(rng)
    assert abs(attacks.loss_threshold_mia(th, Xm, ym, Xn, yn)["auc"] - 0.5) < 0.08
    for _ in range(3000):                                                   # memorise the members
        th -= 0.1 * nn.per_example_grads(th, Xm, ym).mean(0)
    assert attacks.loss_threshold_mia(th, Xm, ym, Xn, yn)["auc"] > 0.7


def test_fairness_audit_detects_planted_bias():
    rng = np.random.default_rng(0); n = 400
    g = np.where(rng.random(n) < 0.5, "A", "B"); y = rng.integers(0, 2, n)
    pred = y.copy(); flip = (g == "B") & (rng.random(n) < 0.35); pred[flip] = 1 - pred[flip]
    S = rng.standard_normal((n, 13)); S[g == "B", 0] *= 6                  # different feature usage in B
    out = fairness.audit(y, pred, S, {"grp": g}, rng, n_perm=200)
    assert any("B" in f["subgroup"] for f in out["flags"]) and out["score"] < 0.9


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for f in fns:
        t = time.time(); f(); print(f"PASS {f.__name__} ({time.time()-t:.1f}s)")
    print(f"\n{len(fns)} tests passed")
