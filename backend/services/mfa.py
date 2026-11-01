"""Multi-Factor Authentication (MFA / TOTP) Engine.

Implements RFC 6238 TOTP with:
- Encrypted TOTP secrets at rest via MultiFernet.
- One-time backup recovery codes (hashed with SHA-256 at rest).
- Audited administrative MFA reset workflow.
"""
from __future__ import annotations
import hashlib
import json
import secrets
from typing import Any, Dict, List, Optional, Tuple
import pyotp

from . import crypto


def generate_mfa_secret() -> str:
    """Generate a high-entropy 32-character base32 secret for TOTP."""
    return pyotp.random_base32()


def generate_provisioning_uri(user_email: str, secret: str, issuer_name: str = "TrustFed-Health") -> str:
    """Generate otpauth:// URI suitable for standard authenticator apps."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=user_email, issuer_name=issuer_name)


def verify_totp_code(secret: str, code: str, valid_window: int = 1) -> bool:
    """Verify a 6-digit TOTP code against the base32 secret with drift tolerance."""
    if not secret or not code:
        return False
    clean_code = str(code).strip().replace(" ", "").replace("-", "")
    if len(clean_code) != 6 or not clean_code.isdigit():
        return False
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(clean_code, valid_window=valid_window))


def generate_recovery_codes(count: int = 8) -> Tuple[List[str], str]:
    """Generate plaintext recovery codes for user display and a JSON array of SHA-256 hashes for storage."""
    plaintext_codes = []
    hashed_codes = []
    for _ in range(count):
        # Format: XXXX-XXXX (alphanumeric uppercase)
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        code = f"{part1}-{part2}"
        plaintext_codes.append(code)
        h = hashlib.sha256(code.encode("utf-8")).hexdigest()
        hashed_codes.append(h)
    return plaintext_codes, json.dumps(hashed_codes)


def verify_and_consume_recovery_code(hashed_codes_json: Optional[str], submitted_code: str) -> Tuple[bool, Optional[str]]:
    """Check submitted recovery code against stored hashes; if matched, burn/remove it and return updated JSON."""
    if not hashed_codes_json or not submitted_code:
        return False, hashed_codes_json

    clean_code = submitted_code.strip().upper()
    submitted_hash = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()

    try:
        codes = json.loads(hashed_codes_json)
        if not isinstance(codes, list):
            return False, hashed_codes_json
    except Exception:
        return False, hashed_codes_json

    if submitted_hash in codes:
        codes.remove(submitted_hash)
        return True, json.dumps(codes)

    return False, hashed_codes_json


def encrypt_mfa_secret(secret: str) -> str:
    """Encrypt TOTP secret with field-level encryption before persisting to database."""
    return crypto.encrypt_phi(secret) or ""


def decrypt_mfa_secret(encrypted_secret: Optional[str]) -> Optional[str]:
    """Decrypt TOTP secret using active or secondary keys in keyring."""
    if not encrypted_secret:
        return None
    try:
        return crypto.decrypt_phi(encrypted_secret)
    except Exception:
        return None
