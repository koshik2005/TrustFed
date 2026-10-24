# TrustFed-Health: Production Hosting & Deployment Guide

This guide details the complete architecture of the **TrustFed-Health** platform, key infrastructure requirements, and step-by-step instructions to host both the backend and frontend in production.

---

## 1. System Architecture Overview

```
                      ┌──────────────────────────────────────┐
                      │    React 19 + Vite Frontend SPA      │
                      │  (Tailwind CSS v4, Recharts, Zustand)│
                      └──────────────────┬───────────────────┘
                                         │  HTTPS / REST + JWT
                                         ▼
                      ┌──────────────────────────────────────┐
                      │        FastAPI Python Backend        │
                      │         (Uvicorn on Port 8000)       │
                      └────┬─────────────┬─────────────┬─────┘
                           │             │             │
              ┌────────────┴──┐   ┌──────┴──────┐   ┌──┴────────────────┐
              │ SQLite /      │   │ Model       │   │ In-Memory HFL     │
              │ Supabase PG   │   │ Artifacts   │   │ Training Engine   │
              │ (Audit Chain, │   │ (*.npz)     │   │ (DP-SGD, SMPC,    │
              │  Users, RBAC) │   │             │   │  Exact SHAP)      │
              └───────────────┘   └─────────────┘   └───────────────────┘
```

### Key Technical Characteristics
1. **Frontend (`/frontend`)**:
   - Single Page Application built with React 19, TypeScript, and Vite.
   - Communicates with backend endpoints via `VITE_API_URL` (defaults to `/api` or `http://localhost:8000/api`).
   - Pure client-side static assets (HTML/JS/CSS).

2. **Backend (`/backend`)**:
   - FastAPI application serving REST endpoints under `/api`.
   - **Training Jobs**: Executed as asynchronous Python daemon threads. Long-running training sessions require a persistent server environment (avoid short-lived serverless functions like standard AWS Lambda or Vercel Functions).
   - **Compute Requirements**: Exact Shapley value calculation (`tefl/explain.py`) computes all $2^{13} = 8,192$ feature subsets for every prediction. Recommended compute: **1 to 2 CPU cores** and **1 to 2 GB RAM**.
   - **Database**: Connects to Supabase PostgreSQL when `SUPABASE_DB_URL` is set; automatically falls back to local SQLite (`backend/trustfed.db`).
   - **Model Storage**: Trained model parameters are saved to `backend/artifacts/{session_id}.npz`.

---

## 2. Choosing Your Hosting Strategy

| Strategy | Best For | Complexity | Estimated Cost |
|---|---|---|---|
| **Option A: Split PaaS (Render / Railway + Vercel)** | Easiest zero-ops deployment with automatic GitHub CI/CD | Low | Free - $7/month |
| **Option B: Single VPS via Docker Compose** | Complete control, privacy compliance, lowest cost at scale | Medium | $4 - $6/month (Hetzner / DigitalOcean) |
| **Option C: GCP Cloud Run + Cloudflare Pages** | Enterprise scalable container platform | Medium | Pay-per-use |

---

## 3. Option A: Split PaaS (Render + Vercel) [Recommended]

### Step 1: Deploy Database (Supabase)
1. Create a free account at [Supabase](https://supabase.com).
2. Create a new project and navigate to **Project Settings** > **Database**.
3. Copy the **Connection URI** (e.g., `postgresql://postgres.[ref]:[pass]@aws-0-[region].pooler.supabase.com:6543/postgres`).

### Step 2: Deploy Backend (Render.com or Railway)
1. Push your repository to GitHub.
2. Sign in to [Render](https://render.com) and click **New +** > **Web Service**.
3. Select your GitHub repository.
4. Configure service parameters:
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Starter ($7/mo) or Standard (needs at least 1GB RAM).
5. Set Environment Variables:
   - `JWT_SECRET`: Generate a 64-character random string (e.g. `openssl rand -hex 32`).
   - `DEMO_PASSWORD`: Secure initial password for default demo accounts.
   - `SUPABASE_DB_URL`: Your Supabase connection string.
   - `CORS_ORIGINS`: Your Vercel frontend URL (e.g., `https://trustfed.vercel.app`).
   - `NVIDIA_API_KEY`: *(Optional)* If using NVIDIA NIM for LLM clinical summaries.
6. Copy the assigned backend URL (e.g., `https://trustfed-api.onrender.com`).

*(Alternatively, use the included `render.yaml` Blueprint for 1-click deployment).*

### Step 3: Deploy Frontend (Vercel)
1. Sign in to [Vercel](https://vercel.com) and import the same GitHub repository.
2. In the project setup:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click edit and select `frontend`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Add Environment Variable:
   - `VITE_API_URL`: Set to your backend URL with `/api` path (e.g., `https://trustfed-api.onrender.com/api`).
4. Click **Deploy**.

---

## 4. Option B: Unified Docker Compose on any VPS (DigitalOcean / EC2 / Hetzner)

A complete production stack configured with multi-stage Dockerfiles and Nginx reverse proxy.

### Prerequisites
- Any Linux VPS (Ubuntu 22.04 LTS or Debian 12 recommended, 2 vCPUs, 2GB-4GB RAM).
- Docker and Docker Compose installed.

### 1-Command Deployment
1. Clone the repository on your server:
   ```bash
   git clone https://github.com/your-org/TrustFed.git
   cd TrustFed
   ```

2. Create `.env` in the root directory:
   ```bash
   JWT_SECRET=$(openssl rand -hex 32)
   DEMO_PASSWORD=YourStrongPasswordHere
   SUPABASE_DB_URL=   # optional; leaves blank to use local persistent storage
   NVIDIA_API_KEY=    # optional
   ```

3. Launch the containers:
   ```bash
   docker compose up --build -d
   ```

4. Verify services:
   ```bash
   docker compose ps
   docker compose logs -f
   ```

Your frontend is now available on port `80`, serving the UI and proxying `/api/` calls seamlessly to the backend with zero CORS issues.

### Adding Free SSL with Certbot (Optional)
If pointing a domain to your server (e.g., `trustfed.example.com`):
```bash
sudo apt update && sudo apt install -y certbot python3-certbot-nginx
```

---

## 5. Production Environment Variables Reference

| Variable | Scope | Description | Default / Example |
|---|---|---|---|
| `VITE_API_URL` | Frontend | Target API endpoint URL | `/api` or `https://api.example.com/api` |
| `JWT_SECRET` | Backend | Key used to sign HS256 auth tokens | Random 64-hex string |
| `DEMO_PASSWORD` | Backend | Default password for seeded demo accounts | `password123` |
| `CORS_ORIGINS` | Backend | Comma-separated list of allowed frontend origins | `https://your-frontend.com` |
| `SUPABASE_DB_URL` | Backend | PostgreSQL connection URL with SSL | `postgresql://user:pass@host:5432/db` |
| `RESULTS_DIR` | Backend | Path to benchmark JSON results | `/app/results` |
| `NVIDIA_API_KEY` | Backend | API key for LLM-powered clinical explanations | `nvapi-...` *(Optional)* |
| `NVIDIA_MODEL` | Backend | Model slug for explanations | `meta/llama-3.1-70b-instruct` |

---

## 6. Seeded Accounts & Roles

Once deployed, the database automatically initializes the following default users:

| Email | Role | Capabilities |
|---|---|---|
| `admin@trustfed.ai` | `global_admin` | Trigger training runs, view all regional metrics, audit logs, and predictions |
| `regional@trustfed.ai` | `regional_admin` | Access regional aggregation views, fairness audits, and benchmark comparisons |
| `hospital@trustfed.ai` | `hospital_staff` | Run patient inference, inspect exact SHAP values, and view hospital status |

*(Initial password equals the value of `DEMO_PASSWORD` in your `.env`, defaulting to `password123`).*
