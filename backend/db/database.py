import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

def _make_engine():
    """Try Supabase first, fall back to local SQLite."""
    if SUPABASE_DB_URL and (SUPABASE_DB_URL.startswith("postgresql") or SUPABASE_DB_URL.startswith("postgres")):
        db_url = SUPABASE_DB_URL.strip()

        # Direct Supabase URLs (db.[ref].supabase.co) resolve to IPv6 only, which fails on Render (IPv4 only).
        # Seamlessly rewrite direct Supabase host to IPv4 pooler endpoint
        if "@db.eyicbgtknkfgajnfgqmz.supabase.co" in db_url:
            db_url = db_url.replace(
                "postgres:zSTAbazbTUXHx3OQ@db.eyicbgtknkfgajnfgqmz.supabase.co:5432",
                "postgres.eyicbgtknkfgajnfgqmz:zSTAbazbTUXHx3OQ@aws-0-ap-northeast-2.pooler.supabase.com:5432"
            )

        # In SQLAlchemy 2.0+, 'postgresql://' defaults to psycopg v3 ('psycopg').
        # If psycopg v3 is not installed, rewrite prefix to psycopg2 so psycopg2-binary works seamlessly.
        try:
            import psycopg  # noqa: F401
        except ImportError:
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            elif db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

        try:
            eng = create_engine(
                db_url,
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
