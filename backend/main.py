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


limiter = Limiter(key_func=get_client_ip, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    auth.validate_secret_key_on_startup()
    from db.migrations.v2_general_disease_migration import migrate_up
    migrate_up(engine)
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
    env = os.getenv("ENVIRONMENT", "development").strip().lower()
    if env in ("production", "prod") or bool(os.getenv("RENDER")):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    return response


from api.v1.routes import router as api_router      # noqa: E402
app.include_router(api_router, prefix="/api")
app.include_router(api_router)


@app.get("/")
@app.head("/")
def root():
    return {"message": "TrustFed-Health backend is running.", "status": "ok", "version": "2.0.0"}


@app.get("/health")
@app.head("/health")
@app.get("/api/health")
@app.head("/api/health")
def health(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"degraded: {str(e)}"
    allow_demo = os.getenv("ALLOW_DEMO_USERS", "true").strip().lower() in ("true", "1", "yes")
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "allow_demo_users": allow_demo,
        "version": "2.0.0"
    }
