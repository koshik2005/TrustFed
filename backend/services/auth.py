"""Authentication, PyJWT token handling, key rotation (kid), and cryptographic hash utilities."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Optional
import bcrypt
import jwt

_ITER = 200_000
BCRYPT_ROUNDS = 12
INSECURE_SECRETS = {
    "", "default", "change-me", "secret", "password", "your-secret-key",
    "change-me-to-a-long-random-string", "test", "demo"
}

_FALLBACK = secrets.token_hex(32)
_KEYRING_CACHE: Optional[Dict[str, str]] = None


def hash_password(pw: str) -> str:
    """Hash password using bcrypt with work factor 12 (OWASP recommended standard)."""
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(pw.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(pw: str, stored: str) -> bool:
    """Verify password against stored hash supporting bcrypt (cost >= 12) and legacy PBKDF2."""
    if not stored or not pw:
        return False
    try:
        # 1. Bcrypt hash format ($2a$, $2b$, $2y$)
        if stored.startswith(("$2a$", "$2b$", "$2y$")):
            return bcrypt.checkpw(pw.encode("utf-8"), stored.encode("utf-8"))
        # 2. Legacy PBKDF2 fallback
        if stored.startswith("pbkdf2_sha256$"):
            _, it, salt, dk = stored.split("$")
            cand = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(it)).hex()
            return hmac.compare_digest(cand, dk)
        return False
    except Exception:
        return False


def secret_key() -> str:
    k = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET")
    if not k:
        k = _FALLBACK
    return k


def reset_auth_key_cache() -> None:
    """Clear cached keyring for testing and dynamic key rotation."""
    global _KEYRING_CACHE
    _KEYRING_CACHE = None


def get_jwt_keyring() -> Dict[str, str]:
    """Retrieve mapping of kid -> secret from JWT_KEY_RING or default secret."""
    global _KEYRING_CACHE
    if _KEYRING_CACHE is not None:
        return _KEYRING_CACHE

    raw = os.getenv("JWT_KEY_RING", "").strip()
    keyring: Dict[str, str] = {}
    if raw:
        # Try JSON format first: {"v2": "secret2", "v1": "secret1"}
        if raw.startswith("{"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    keyring = {str(k).strip(): str(v).strip() for k, v in parsed.items() if str(v).strip()}
            except Exception:
                keyring = {}
        # Try comma-delimited pairs: "v2:secret2,v1:secret1"
        if not keyring:
            for pair in raw.split(","):
                if ":" in pair:
                    kid, sec = pair.split(":", 1)
                    if kid.strip() and sec.strip():
                        keyring[kid.strip()] = sec.strip()

    if not keyring:
        active_kid = os.getenv("JWT_ACTIVE_KID", "v1").strip() or "v1"
        keyring[active_kid] = secret_key()

    _KEYRING_CACHE = keyring
    return _KEYRING_CACHE


def get_active_jwt_kid() -> str:
    """Return the active Key ID (kid) used for signing new tokens."""
    env_kid = os.getenv("JWT_ACTIVE_KID", "").strip()
    keyring = get_jwt_keyring()
    if env_kid and env_kid in keyring:
        return env_kid
    # Default to first configured kid in keyring
    return next(iter(keyring.keys()), "v1")


def get_active_jwt_secret() -> str:
    """Return the secret string associated with the active kid."""
    keyring = get_jwt_keyring()
    kid = get_active_jwt_kid()
    return keyring.get(kid, secret_key())


def validate_secret_key_on_startup():
    """Fails startup if SECRET_KEY / JWT_SECRET is missing or an insecure default in production/staging."""
    reset_auth_key_cache()
    env = os.getenv("ENVIRONMENT", "development").strip().lower()
    is_prod = env in ("production", "prod") or bool(os.getenv("RENDER"))
    if not is_prod:
        return

    # 1. Direct environment variable check
    raw_env_sec = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or ""
    k_clean = raw_env_sec.strip().lower()
    if not raw_env_sec or k_clean in INSECURE_SECRETS or len(raw_env_sec.strip()) < 16:
        raise RuntimeError(
            "FATAL: Insecure or missing SECRET_KEY / JWT_SECRET in production. "
            "A high-entropy secret of at least 16 characters must be set in environment variables."
        )

    # 2. Keyring active secret check
    active_sec = get_active_jwt_secret()
    active_clean = active_sec.strip().lower()
    if not active_sec or active_clean in INSECURE_SECRETS or len(active_sec.strip()) < 16:
        raise RuntimeError(
            "FATAL: Insecure or missing SECRET_KEY / JWT_SECRET in production. "
            "A high-entropy secret of at least 16 characters must be set in environment variables."
        )


def create_token(claims: Dict[str, Any], ttl: int = 15 * 60, token_type: str = "access") -> str:
    """Create a signed JWT with PyJWT including Key ID (kid) in header."""
    now = int(time.time())
    payload = {
        **claims,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
    }
    kid = get_active_jwt_kid()
    secret = get_active_jwt_secret()
    return jwt.encode(payload, secret, algorithm="HS256", headers={"kid": kid})


def decode_token(tok: str, expected_type: Optional[str] = "access") -> Dict[str, Any]:
    """Decode and verify a PyJWT token using header kid lookup with fallback across keyring."""
    keyring = get_jwt_keyring()

    # 1. Attempt to extract kid from unverified token header
    target_secret = None
    try:
        header = jwt.get_unverified_header(tok)
        kid = header.get("kid")
        if kid and kid in keyring:
            target_secret = keyring[kid]
    except Exception:
        pass

    # 2. If kid is known, verify directly with corresponding secret
    if target_secret:
        try:
            payload = jwt.decode(tok, target_secret, algorithms=["HS256"])
            if expected_type and payload.get("type") != expected_type:
                if "type" in payload and payload["type"] != expected_type:
                    raise ValueError(f"invalid token type: expected {expected_type}")
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("expired")
        except jwt.InvalidSignatureError:
            raise ValueError("bad signature")
        except jwt.PyJWTError as e:
            raise ValueError(f"invalid token: {e}")

    # 3. Fallback across all secrets in keyring (supports legacy untyped tokens and rotation)
    secrets_to_try = [get_active_jwt_secret()] + [s for s in keyring.values() if s != get_active_jwt_secret()]
    last_err: Optional[Exception] = None

    for sec in secrets_to_try:
        try:
            payload = jwt.decode(tok, sec, algorithms=["HS256"])
            if expected_type and payload.get("type") != expected_type:
                if "type" in payload and payload["type"] != expected_type:
                    raise ValueError(f"invalid token type: expected {expected_type}")
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("expired")
        except jwt.InvalidSignatureError as e:
            last_err = e
            continue
        except jwt.PyJWTError as e:
            last_err = e
            continue

    if last_err and "Signature verification failed" in str(last_err):
        raise ValueError("bad signature")
    raise ValueError(f"invalid token: {last_err or 'unknown error'}")


def validate_password_strength(password: str) -> None:
    """Enforces high-security enterprise password requirements."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one number")
    specials = "!@#$%^&*()-_=+[]{}|;:,.<>?"
    if not any(c in specials for c in password):
        raise ValueError("Password must contain at least one special character")


def generate_temp_password(length: int = 14) -> str:
    """Generate a high-entropy one-time temporary password meeting all policy criteria."""
    import string
    specials = "!@#$%^&*()-_=+"
    p = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(specials),
    ]
    all_chars = string.ascii_letters + string.digits + specials
    for _ in range(max(0, length - 4)):
        p.append(secrets.choice(all_chars))
    secrets.SystemRandom().shuffle(p)
    return "".join(p)


def create_refresh_token_pair(
    user_id: int, email: str, role: str, hospital_id: Optional[str], hub_id: Optional[str] = None
) -> Dict[str, str]:
    """Create short-lived access token + long-lived refresh token with unique JTI and CSRF token."""
    csrf_token = secrets.token_hex(32)
    jti = secrets.token_hex(16)
    access_token = create_token({
        "sub": email,
        "role": role,
        "hospital_id": hospital_id,
        "hub_id": hub_id,
        "user_id": user_id,
    }, ttl=15 * 60, token_type="access")

    refresh_token = create_token({
        "sub": email,
        "user_id": user_id,
        "role": role,
        "hospital_id": hospital_id,
        "hub_id": hub_id,
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
