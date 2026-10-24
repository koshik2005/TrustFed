# TrustFed-Health (v2)

Privacy-preserving, explainable, fairness-audited **hierarchical federated learning** for multi-hospital
heart-disease risk prediction (hospital → regional hub → global server).

## What is real now
| Component | Implementation | Verified by |
|---|---|---|
| FedAvg over non-IID hospitals | `backend/tefl/fl.py` (numpy MLP 13-32-16-2) | `tests/test_tefl.py` |
| Local record-level DP-SGD | per-example clip + Gaussian noise, Poisson sampling (`tefl/dp.py`) | gradient check vs finite differences |
| Privacy accountant | RDP of the sampled Gaussian mechanism → (ε, δ) | reproduces ε≈2.6 on the MNIST benchmark |
| Secure aggregation | additive secret sharing over Z_2^64 + packed Paillier tier (`tefl/secagg.py`) | sum equals plain sum (<1e-6) |
| Explanations | exact Shapley values, all 2^13 coalitions (`tefl/explain.py`) | efficiency property test |
| Fairness audit | subgroup metrics + SHAP-profile JS divergence with permutation test (`tefl/fairness.py`) | planted-bias test |
| Privacy audit | loss-threshold membership-inference attack (`tefl/attacks.py`) | random vs memoriser test |
| API | FastAPI, JWT roles, hash-chained audit log, background training | **syntax-checked only** (see below) |
| UI | React: real login, real prediction form, real charts | **syntax-checked only** |

## Run
```bash
# 1) engine tests (no web deps needed)
cd backend && python tests/test_tefl.py && python tests/test_services.py

# 2) reproduce all paper numbers (downloads UCI Cleveland once)
python -m tefl.run_experiments --data cleveland --reps 10 --out ../results/results.json

# 3) rebuild the paper from those numbers
cd ../paper && python make_figures.py ../results/results.json && python build_paper.py ../results/results.json

# 4) web app
cd ../backend && pip install -r requirements.txt && cp .env.example .env   # edit secrets
uvicorn main:app --reload --port 8000
cd ../frontend && cp .env.example .env && npm install && npm run dev
# 5) Docker deployment (production / single-command)
docker compose up --build -d
# See docs/DEPLOYMENT_GUIDE.md for cloud hosting (Render, Vercel, Supabase, VPS)
```
Demo logins (password = `DEMO_PASSWORD`, default `password123`): `hospital@trustfed.ai`, `regional@trustfed.ai`, `admin@trustfed.ai`.
Only the global admin can start training. **Delete any old `trustfed.db`** — the schema changed.
Detailed hosting blueprints are in [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md).

## Security
The original archive contained a `.env` with live-looking NVIDIA and Supabase credentials. They were removed here;
**rotate them**. Never commit `.env`.
