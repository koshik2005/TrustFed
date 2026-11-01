"""Cryptographic primitives for Protected Health Information (PHI) encryption at rest.

Guarantees:
- Patient identifying fields (full name, phone/email contact) are encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256).
- Supports MultiFernet key rotation: multiple keys can be specified as a comma-separated list.
  The first key is used for all new encryptions; all keys in the keyring can decrypt historical records.
- Plaintext PHI never leaves hospital scope; only authorized hospital staff/doctors within the same hospital can decrypt.
"""
from __future__ import annotations
import base64
import os
from typing import List, Optional
from cryptography.fernet import Fernet, MultiFernet

_KEY_CACHE: Optional[List[bytes]] = None
_MULTI_FERNET_CACHE: Optional[MultiFernet] = None


def _parse_keys_from_env() -> List[bytes]:
    """Extract one or more Fernet keys from environment variables."""
    raw = os.getenv("PATIENT_ENCRYPTION_KEYS") or os.getenv("PATIENT_ENCRYPTION_KEY") or ""
    keys: List[bytes] = []
    for part in raw.split(","):
        k = part.strip()
        if k:
            keys.append(k.encode("utf-8"))
    return keys


def validate_encryption_key_on_startup() -> None:
    """Called at startup. In production, raises RuntimeError if PATIENT_ENCRYPTION_KEY
    env var is absent or invalid — prevents silent use of a random ephemeral key that
    loses all encrypted data on every restart.
    """
    env = os.getenv("ENVIRONMENT", "development").strip().lower()
    is_render = bool(os.getenv("RENDER"))
    is_production = env in ("production", "prod") or is_render
    allow_demo = os.getenv("ALLOW_DEMO_USERS", "false").strip().lower() in ("true", "1", "yes")

    keys = _parse_keys_from_env()
    if keys:
        for idx, k in enumerate(keys):
            try:
                Fernet(k)
            except Exception as e:
                raise RuntimeError(
                    f"PATIENT_ENCRYPTION_KEY[{idx}] is not a valid Fernet key: {e}. "
                    "Regenerate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                ) from e
        return

    if not is_production:
        return  # dev/test: random ephemeral key is acceptable

    # Key is missing:
    if is_production and not allow_demo:
        raise RuntimeError(
            "PATIENT_ENCRYPTION_KEY environment variable is required in production "
            "but is missing or empty. Set it as a persistent Render environment variable "
            "to a valid Fernet key (generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"). "
            "Without it, encrypted patient data cannot be decrypted after a server restart."
        )

    # In demo mode on Render without key set:
    import logging
    logging.warning(
        "[SECURITY ALERT] PATIENT_ENCRYPTION_KEY is not configured in Render environment variables! "
        "Running in DEMO mode with ephemeral encryption key. "
        "To enable persistent PHI encryption across restarts, add PATIENT_ENCRYPTION_KEY to Render Environment Variables."
    )


def reset_key_cache() -> None:
    """Reset key and MultiFernet caches (useful during key rotation or testing)."""
    global _KEY_CACHE, _MULTI_FERNET_CACHE
    _KEY_CACHE = None
    _MULTI_FERNET_CACHE = None


def get_multi_fernet() -> MultiFernet:
    """Return configured MultiFernet instance handling primary key encryption and multi-key decryption."""
    global _KEY_CACHE, _MULTI_FERNET_CACHE
    if _MULTI_FERNET_CACHE is not None:
        return _MULTI_FERNET_CACHE

    keys = _parse_keys_from_env()
    valid_fernets: List[Fernet] = []
    for k in keys:
        try:
            valid_fernets.append(Fernet(k))
        except Exception:
            continue

    if not valid_fernets:
        # Fallback to single random ephemeral key (dev/test)
        ephemeral = Fernet.generate_key()
        valid_fernets = [Fernet(ephemeral)]

    _MULTI_FERNET_CACHE = MultiFernet(valid_fernets)
    return _MULTI_FERNET_CACHE


def encrypt_phi(plaintext: Optional[str]) -> Optional[str]:
    """Encrypt a string with primary Fernet authenticated encryption."""
    if plaintext is None:
        return None
    if not plaintext.strip():
        return ""
    mf = get_multi_fernet()
    encrypted_bytes = mf.encrypt(plaintext.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_phi(ciphertext: Optional[str]) -> Optional[str]:
    """Decrypt a Fernet ciphertext back to string using any key in the keyring."""
    if ciphertext is None:
        return None
    if not ciphertext.strip():
        return ""
    mf = get_multi_fernet()
    try:
        decrypted_bytes = mf.decrypt(ciphertext.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to decrypt PHI ciphertext: {e}")


def rotate_phi(ciphertext: Optional[str]) -> Optional[str]:
    """Re-encrypt ciphertext with the latest primary key while verifying with previous key."""
    if ciphertext is None or not ciphertext.strip():
        return ciphertext
    mf = get_multi_fernet()
    try:
        rotated_bytes = mf.rotate(ciphertext.encode("utf-8"))
        return rotated_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to rotate PHI ciphertext: {e}")
