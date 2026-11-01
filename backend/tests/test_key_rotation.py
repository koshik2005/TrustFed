"""Automated Pytest for Secrets & Key Rotation (JWT kid and MultiFernet)."""
import os
import pytest
from cryptography.fernet import Fernet
import jwt

from services import crypto, auth


def test_multifernet_phi_key_rotation_keeps_old_data_readable():
    """Verify that after adding a new primary key, old ciphertext is still decrypted."""
    key_v1 = Fernet.generate_key().decode()
    os.environ["PATIENT_ENCRYPTION_KEY"] = key_v1
    crypto.reset_key_cache()

    plaintext = "Sensitive Health Record"
    ciphertext_v1 = crypto.encrypt_phi(plaintext)
    assert crypto.decrypt_phi(ciphertext_v1) == plaintext

    # Rotate to Key V2
    key_v2 = Fernet.generate_key().decode()
    os.environ["PATIENT_ENCRYPTION_KEY"] = f"{key_v2},{key_v1}"
    crypto.reset_key_cache()

    # Historical data must remain readable
    assert crypto.decrypt_phi(ciphertext_v1) == plaintext

    # New data must encrypt with Key V2
    new_plaintext = "Second Patient Record"
    ciphertext_v2 = crypto.encrypt_phi(new_plaintext)
    assert Fernet(key_v2.encode()).decrypt(ciphertext_v2.encode()).decode() == new_plaintext

    # Re-encrypt historical ciphertext
    upgraded_ciphertext = crypto.rotate_phi(ciphertext_v1)
    assert Fernet(key_v2.encode()).decrypt(upgraded_ciphertext.encode()).decode() == plaintext


def test_jwt_kid_rotation_and_verification():
    """Verify that JWT tokens with previous kid continue validating when a new kid is active."""
    secret_v1 = "secret-2026-v1-super-secure-key-phrase"
    secret_v2 = "secret-2026-v2-rotated-key-phrase-here"

    os.environ["JWT_KEY_RING"] = f"kid-v1:{secret_v1}"
    os.environ["JWT_ACTIVE_KID"] = "kid-v1"
    auth.reset_auth_key_cache()

    token_v1 = auth.create_token({"sub": "user@hospital.org", "role": "doctor"}, ttl=600)
    assert jwt.get_unverified_header(token_v1).get("kid") == "kid-v1"
    assert auth.decode_token(token_v1)["sub"] == "user@hospital.org"

    # Rotate to kid-v2
    os.environ["JWT_KEY_RING"] = f"kid-v2:{secret_v2},kid-v1:{secret_v1}"
    os.environ["JWT_ACTIVE_KID"] = "kid-v2"
    auth.reset_auth_key_cache()

    # Old token still valid
    assert auth.decode_token(token_v1)["sub"] == "user@hospital.org"

    # New token uses kid-v2
    token_v2 = auth.create_token({"sub": "admin@hospital.org", "role": "global_admin"}, ttl=600)
    assert jwt.get_unverified_header(token_v2).get("kid") == "kid-v2"
    assert auth.decode_token(token_v2)["sub"] == "admin@hospital.org"

    # Cleanup test env
    os.environ.pop("JWT_KEY_RING", None)
    os.environ.pop("JWT_ACTIVE_KID", None)
    auth.reset_auth_key_cache()

