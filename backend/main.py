import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from db.database import engine, Base, SessionLocal, get_db
from services import auth, store


def get_client_ip(request: Request) -> str:
    """Reads X-Forwarded-For correctly behind reverse proxies (like Render)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


rate_limit_enabled = os.getenv("DISABLE_RATE_LIMIT", "false").strip().lower() not in ("true", "1", "yes")
rate_limit_default = os.getenv("RATE_LIMIT_DEFAULT", "120/minute")
limiter = Limiter(key_func=get_client_ip, default_limits=[rate_limit_default], enabled=rate_limit_enabled)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from core.deployment_mode import validate_deployment_mode_on_startup
    validate_deployment_mode_on_startup()
    auth.validate_secret_key_on_startup()
    from services import crypto
    crypto.validate_encryption_key_on_startup()
    from db.migrations.v2_general_disease_migration import migrate_up
    migrate_up(engine)
    from db.migrations.v3_performance_indexes import migrate_up as migrate_v3_indexes
    migrate_v3_indexes(engine)
    from db.migrations.enable_rls import enable_row_level_security
    enable_row_level_security(engine)

    db = SessionLocal()
    try:
        from services import seed_data
        seed_data.seed_synthetic_data(db)
        store.seed_users(db)
        store.migrate_legacy_predictions(db)
        from db import models
        for s in db.query(models.FLSession).filter_by(status="running").all():
            s.status, s.error = "failed", "server restarted during training"
        db.commit()

        # Performance: Preload models once at startup and cache in memory
        from services import general_disease_model
        general_disease_model.get_model()
        general_disease_model.load_curated_remedies()
        from api.v1.routes import get_cached_active_model
        get_cached_active_model(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="TrustFed-Health API",
    version="2.0.0",
    lifespan=lifespan,
    description="Federated learning with local DP, secure aggregation, exact SHAP and fairness auditing."
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if raw.strip():
        # Disallow wildcards; require exact origins
        parsed = [o.strip() for o in raw.split(",") if o.strip() and "*" not in o]
        if parsed:
            return parsed
    return [
        "https://frontend-3qgo.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]


from fastapi.middleware.gzip import GZipMiddleware
from core.logging_config import init_monitoring_and_logging

# Initialize structured logging with PHI redaction and Sentry error monitoring
init_monitoring_and_logging()

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://trustfed-backend.onrender.com https://frontend-3qgo.vercel.app; "
        "frame-ancestors 'none';"
    )
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    # Enforce no-cache on sensitive API responses
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
    return response


from api.v1.routes import router as api_router      # noqa: E402
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")
app.include_router(api_router)


@app.get("/")
@app.head("/")
def root():
    from core.deployment_mode import get_app_mode
    return {"message": "TrustFed-Health backend is running.", "status": "ok", "version": "2.0.0", "mode": get_app_mode()}


@app.get("/health")
@app.head("/health")
@app.get("/api/health")
@app.head("/api/health")
@app.get("/api/v1/health")
@app.head("/api/v1/health")
def health(db: Session = Depends(get_db)):
    """Liveness probe: verifies basic service and DB reachability without leaking sensitive details."""
    from core.deployment_mode import get_app_mode
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False
    return {
        "status": "healthy" if db_connected else "degraded",
        "database": "connected" if db_connected else "disconnected",
        "version": "2.0.0",
        "mode": get_app_mode()
    }


@app.get("/ready")
@app.head("/ready")
@app.get("/api/ready")
@app.head("/api/ready")
@app.get("/api/v1/ready")
@app.head("/api/v1/ready")
def readiness_check(response: Response, db: Session = Depends(get_db)):
    """Readiness probe: verifies DB connectivity and cached ML model availability."""
    from core.deployment_mode import get_app_mode
    from services.general_disease_model import get_model
    from api.v1.routes import get_cached_active_model

    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    model_ok = False
    try:
        gen_model = get_model()
        _, cardiac_model, _ = get_cached_active_model(db)
        if gen_model is not None and cardiac_model is not None:
            model_ok = True
    except Exception:
        model_ok = False

    is_ready = db_ok and model_ok
    if not is_ready:
        response.status_code = 503
        return {
            "status": "not_ready",
            "database": "connected" if db_ok else "disconnected",
            "model": "loaded" if model_ok else "not_loaded",
            "mode": get_app_mode()
        }

    return {
        "status": "ready",
        "database": "connected",
        "model": "loaded",
        "version": "2.0.0",
        "mode": get_app_mode()
    }


@app.get("/metrics")
@app.head("/metrics")
@app.get("/api/metrics")
@app.head("/api/metrics")
def metrics():
    """System & latency metrics endpoint including p50, p95, p99 for /predict."""
    from core.deployment_mode import get_app_mode
    from core.metrics import predict_latency_tracker
    return {
        "status": "ok",
        "prediction_latency": predict_latency_tracker.get_metrics(),
        "mode": get_app_mode()
    }
