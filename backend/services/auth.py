"""Password hashing (PBKDF2-SHA256) and HS256 JWT using only the standard library."""
import base64, hashlib, hmac, json, os, time, secrets

_ITER = 200_000


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


def _b64(b: bytes) -> str: return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def _unb64(s: str) -> bytes: return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def secret_key() -> str:
    k = os.getenv("JWT_SECRET")
    if not k:
        k = _FALLBACK
    return k


_FALLBACK = secrets.token_hex(32)       # per-process random: tokens die on restart unless JWT_SECRET is set


def create_token(claims: dict, ttl: int = 8 * 3600) -> str:
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64(json.dumps({**claims, "exp": int(time.time()) + ttl}).encode())
    sig = _b64(hmac.new(secret_key().encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"


def decode_token(tok: str) -> dict:
    try:
        head, body, sig = tok.split(".")
        good = _b64(hmac.new(secret_key().encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            raise ValueError("bad signature")
        claims = json.loads(_unb64(body))
        if claims["exp"] < time.time():
            raise ValueError("expired")
        return claims
    except Exception as e:
        raise ValueError(f"invalid token: {e}")


def audit_hash(prev_hash: str, ts: str, node: str, etype: str, desc: str) -> str:
    return hashlib.sha256("|".join([prev_hash, ts, node or "", etype, desc]).encode()).hexdigest()


GENESIS = "0" * 64
