import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import engine, Base, SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    from services import store
    db = SessionLocal()
    try:
        store.seed_users(db)
        # a server restart kills any in-flight training thread -> mark orphaned sessions as failed
        from db import models
        for s in db.query(models.FLSession).filter_by(status="running").all():
            s.status, s.error = "failed", "server restarted during training"
        db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title="TrustFed-Health API", version="2.0.0", lifespan=lifespan,
              description="Federated learning with local DP, secure aggregation, exact SHAP and fairness auditing.")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

from api.v1.routes import router as api_router      # noqa: E402
app.include_router(api_router, prefix="/api")
app.include_router(api_router)



@app.get("/")
def root():
    return {"message": "TrustFed-Health backend is running.", "status": "ok"}
