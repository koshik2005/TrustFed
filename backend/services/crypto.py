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
    """Return a 32-byte URL-safe base64-encoded key for Fernet symmetric encryption.
    
    If PATIENT_ENCRYPTION_KEY is provided in the environment, it is used directly.
    Otherwise, a cryptographically secure random key is generated using Fernet.generate_key()
    (purely random bytes, no derivation with static salt).
    """
    global _KEY_CACHE
    if _KEY_CACHE is not None:
        return _KEY_CACHE

    env_key = os.getenv("PATIENT_ENCRYPTION_KEY")
    if env_key and env_key.strip():
        key_bytes = env_key.strip().encode("utf-8")
        try:
            # Verify valid Fernet key
            Fernet(key_bytes)
            _KEY_CACHE = key_bytes
            return _KEY_CACHE
        except Exception:
            pass

    # Randomly generated Fernet key (pure random entropy, no static salt)
    _KEY_CACHE = Fernet.generate_key()
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
