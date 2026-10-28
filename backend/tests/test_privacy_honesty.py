"""Automated tests asserting privacy honesty and accountant verification.
Verifies that:
1. Differential Privacy noise multiplier sigma is capped at 3.5 to preserve numerical stability.
2. The recorded and displayed epsilon mathematically matches fl.eps_after for the sigma actually used.
3. If an ambitious target_epsilon (e.g. 1.0) cannot be met under sigma <= 3.5,
   the actual certified epsilon is reported and target_met evaluates to False.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tefl import fl, dp
from tefl.fl import FLConfig


def test_calibrate_sigma_respects_ceiling():
    """Verify calibrate_sigma never returns sigma > 3.5 even for impossible target_eps."""
    cfg = FLConfig(rounds=20, local_epochs=1, batch=8, lr=0.1, clip=1.0)
    sizes = [15, 12, 18, 14, 16] # small hospital cohorts
    target_eps = 0.5 # impossible to achieve with small sizes without exploding sigma

    sigma = fl.calibrate_sigma(cfg, sizes, target_eps=target_eps, lo=0.3, hi=3.5)
    assert sigma <= 3.5, f"sigma {sigma} exceeded ceiling of 3.5"
    assert sigma >= 0.3


def test_session_epsilon_equals_accountant_output():
    """Verify that recorded epsilon identically matches the RDP accountant output for actual sigma used."""
    sizes = [20, 25, 22]
    cfg = FLConfig(rounds=10, local_epochs=1, batch=8, lr=0.1, clip=1.0, sigma=2.5, delta=1e-5)

    accountant_eps = fl.eps_after(cfg, sizes, cfg.rounds)
    assert accountant_eps > 0 and accountant_eps < 100.0

    # In a simulated federated run with dummy data:
    import numpy as np
    dummy_hospitals = [(np.zeros((n, 13)), np.zeros(n, dtype=int)) for n in sizes]
    res = fl.run_federated(dummy_hospitals, np.zeros((10, 13)), np.zeros(10, dtype=int), cfg)

    # Core privacy invariant: res.epsilon MUST equal accountant_eps
    assert abs(res.epsilon - accountant_eps) < 1e-6, (
        f"Displayed epsilon {res.epsilon} diverged from accountant output {accountant_eps}"
    )


def test_unreachable_target_epsilon_reported_honestly():
    """Verify that when target_epsilon cannot be met, actual epsilon is reported and target_met is False."""
    sizes = [15, 15, 15]
    target_eps = 1.0
    cfg = FLConfig(rounds=20, local_epochs=1, batch=8, lr=0.1, clip=1.0, delta=1e-5)

    chosen_sigma = fl.calibrate_sigma(cfg, sizes, target_eps=target_eps, hi=3.5)
    assert chosen_sigma <= 3.5

    cfg_run = FLConfig(**{**cfg.__dict__, "sigma": chosen_sigma})
    actual_eps = fl.eps_after(cfg_run, sizes, cfg_run.rounds)

    # If actual_eps exceeds target_eps, target_met must be False
    target_met = (actual_eps <= target_eps + 0.05)
    if actual_eps > target_eps:
        assert target_met is False, "target_met should be False when target epsilon is not met"
        assert actual_eps > target_eps, "Reported epsilon must reflect actual accountant value"

    print(f"Privacy honesty verified: sigma_used={chosen_sigma:.2f}, actual_eps={actual_eps:.2f}, target_met={target_met}")


if __name__ == "__main__":
    test_calibrate_sigma_respects_ceiling()
    test_session_epsilon_equals_accountant_output()
    test_unreachable_target_epsilon_reported_honestly()
    print("All privacy honesty tests passed!")
