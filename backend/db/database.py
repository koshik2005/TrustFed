import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

def _make_engine():
    """Try Supabase first, fall back to local SQLite."""
    if SUPABASE_DB_URL and SUPABASE_DB_URL.startswith("postgresql"):
        try:
            eng = create_engine(
                SUPABASE_DB_URL,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                connect_args={
                    "connect_timeout": 10,
                    "sslmode": "require",
                },
            )
            # Quick connection test
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[OK] Connected to Supabase PostgreSQL")
            return eng
        except Exception as e:
            print(f"[WARN] Supabase connection failed: {e}")
            print("[WARN] Falling back to local SQLite database...")

    # Local SQLite fallback
    SQLITE_URL = "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trustfed.db")
    eng = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    print("[INFO] Using local SQLite database: trustfed.db")
    return eng

engine = _make_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency for FastAPI to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
