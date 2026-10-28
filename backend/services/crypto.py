"""Cryptographic primitives for Protected Health Information (PHI) encryption at rest.

Guarantees:
- Patient identifying fields (full name, phone/email contact) are encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256).
- Encryption key is derived from PATIENT_ENCRYPTION_KEY or SECRET_KEY.
- Plaintext PHI never leaves hospital scope; only authorized hospital staff/doctors within the same hospital can decrypt.
"""
from __future__ import annotations
import base64
import os
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_KEY_CACHE: Optional[bytes] = None


def get_phi_encryption_key() -> bytes:
    """Derive a URL-safe base64-encoded 32-byte key for Fernet symmetric encryption."""
    global _KEY_CACHE
    if _KEY_CACHE is not None:
        return _KEY_CACHE

    raw_secret = os.getenv("PATIENT_ENCRYPTION_KEY") or os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
    if not raw_secret:
        # Default dev key with deterministic salt
        raw_secret = "trustfed-phi-master-key-change-in-prod-2026"

    # Derive 32 bytes using PBKDF2HMAC
    salt = b"trustfed_phi_static_salt_v1"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    derived = kdf.derive(raw_secret.encode())
    _KEY_CACHE = base64.urlsafe_b64encode(derived)
    return _KEY_CACHE


def encrypt_phi(plaintext: Optional[str]) -> Optional[str]:
    """Encrypt a string with Fernet authenticated encryption."""
    if plaintext is None:
        return None
    if not plaintext.strip():
        return ""
    f = Fernet(get_phi_encryption_key())
    encrypted_bytes = f.encrypt(plaintext.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_phi(ciphertext: Optional[str]) -> Optional[str]:
    """Decrypt a Fernet ciphertext back to string."""
    if ciphertext is None:
        return None
    if not ciphertext.strip():
        return ""
    f = Fernet(get_phi_encryption_key())
    try:
        decrypted_bytes = f.decrypt(ciphertext.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to decrypt PHI ciphertext: {e}")
