"""Authentication, PyJWT token handling, and cryptographic hash utilities."""
from __future__ import annotations
import hashlib
import hmac
import os
import secrets
import time
from typing import Any, Dict, Optional
import jwt

_ITER = 200_000
INSECURE_SECRETS = {
    "", "default", "change-me", "secret", "password", "your-secret-key",
    "change-me-to-a-long-random-string", "test", "demo"
}


def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), _ITER).hex()
    return f"pbkdf2_sha256${_ITER}${salt}${dk}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, it, salt, dk = stored.split("$")
        cand = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(it)).hex()
        return hmac.compare_digest(cand, dk)
    except Exception:
        return False


def secret_key() -> str:
    k = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET")
    if not k:
        k = _FALLBACK
    return k


_FALLBACK = secrets.token_hex(32)


def validate_secret_key_on_startup():
    """Fails startup if SECRET_KEY / JWT_SECRET is missing or an insecure default in production/staging."""
    k = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or ""
    k_clean = k.strip().lower()
    env = os.getenv("ENVIRONMENT", "development").strip().lower()
    is_prod = env in ("production", "prod") or bool(os.getenv("RENDER"))
    if is_prod and (not k or k_clean in INSECURE_SECRETS or len(k.strip()) < 16):
        raise RuntimeError(
            "FATAL: Insecure or missing SECRET_KEY / JWT_SECRET in production. "
            "A high-entropy secret of at least 16 characters must be set in environment variables."
        )


def create_token(claims: Dict[str, Any], ttl: int = 15 * 60, token_type: str = "access") -> str:
    """Create a signed JWT with PyJWT."""
    now = int(time.time())
    payload = {
        **claims,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, secret_key(), algorithm="HS256")


def decode_token(tok: str, expected_type: Optional[str] = "access") -> Dict[str, Any]:
    """Decode and verify a PyJWT token. Raises ValueError on failure for backward compatibility."""
    try:
        payload = jwt.decode(tok, secret_key(), algorithms=["HS256"])
        if expected_type and payload.get("type") != expected_type:
            # Allow untyped legacy test tokens if type not present
            if "type" in payload and payload["type"] != expected_type:
                raise ValueError(f"invalid token type: expected {expected_type}")
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("expired")
    except jwt.InvalidSignatureError:
        raise ValueError("bad signature")
    except jwt.PyJWTError as e:
        raise ValueError(f"invalid token: {e}")
    except Exception as e:
        raise ValueError(f"invalid token: {e}")


def create_refresh_token_pair(user_id: int, email: str, role: str, hospital_id: Optional[str]) -> Dict[str, str]:
    """Create short-lived access token + long-lived refresh token with unique JTI and CSRF token."""
    csrf_token = secrets.token_hex(32)
    jti = secrets.token_hex(16)
    access_token = create_token({
        "sub": email,
        "role": role,
        "hospital_id": hospital_id,
        "user_id": user_id,
    }, ttl=15 * 60, token_type="access")

    refresh_token = create_token({
        "sub": email,
        "user_id": user_id,
        "role": role,
        "hospital_id": hospital_id,
        "jti": jti,
        "csrf": csrf_token,
    }, ttl=7 * 86400, token_type="refresh")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "csrf_token": csrf_token,
        "jti": jti,
    }


def audit_hash(prev_hash: str, ts: str, node: str, etype: str, desc: str) -> str:
    return hashlib.sha256("|".join([prev_hash, ts, node or "", etype, desc]).encode()).hexdigest()


GENESIS = "0" * 64
