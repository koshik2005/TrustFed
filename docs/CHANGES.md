# Changes from the original project

## Fabricated / hard-coded behaviour replaced
* `/prediction` used a hand-written rule; SHAP values, fairness report, privacy report and comparison table were literals → now a trained model, exact SHAP, computed audits, results from `run_experiments`.
* GlobalMonitor drew `0.68 + r/total*0.17` as "accuracy"; dashboard drew invented loss curves; Fairness page, ε values (1.824, 2.847), "24.6 %" and "+16.1" claims were literals → all removed or computed.
* Login accepted anything (`demo-jwt-token`) → real PBKDF2 + JWT, role enforcement per route.
* Audit "hashes" were random → SHA-256 hash chain with `/api/audit/verify`.
* Patient IDs were fixed (#88192) → random anonymous IDs.

## Bugs fixed
1. **Global DP noise destroyed the model**: σ=√(2ln(1.25/δ))/ε≈4.8 was added to *every weight*. Removed; DP is now local DP-SGD with a proper accountant.
2. SMPC with one hub produced a single share = the plaintext update (no secrecy) and the "HE average" averaged a 1-element list. Now shares are split across hospitals in a hub; hubs are summed under HE.
3. AGPM adapted ε from gradient variance — data-dependent budgets void the DP guarantee. Removed.
4. Opacus `make_private_with_epsilon` re-wrapped the same model/loader every round (crashes / double wrapping).
5. `NUM_ROUNDS=10` vs `total_rounds=20`: sessions never reached "Completed".
6. Frontend base URL `/api/v1` vs backend `/api` (every call 404).
7. Prediction form ignored all inputs and sent out-of-range constants (cp=0, thal=2); slope/ca/thal fields were missing from the UI.
8. SQLite path relative to cwd; `subprocess "python"` instead of `sys.executable`; UTF-16 handover file; secrets committed in `.env`.
9. Dataset downloaded from UCI at every client start and standardised on the full data (test leakage) → cached; scaler fit on training fold only.

## Not done / needs you
* Run experiments on the real Cleveland file (needs internet) and rebuild the paper.
* Flower/Opacus back-ends were replaced by a self-contained numpy engine (testable offline). A Flower adapter is future work.
* FastAPI/SQLAlchemy/React were not executed in the build sandbox (no packages/network).
