#!/usr/bin/env python3
"""Secrets & Key Rotation Drill for TrustFed.

Demonstrates and verifies:
1. MultiFernet PHI Encryption Key Rotation:
   - Data encrypted with old key(s) remains readable after rotation.
   - New data is encrypted with the newest primary key.
   - MultiFernet.rotate() can re-encrypt historical records to the new key.
2. JWT kid-based Key Rotation:
   - Old tokens issued under previous kid validate until expiration.
   - New tokens are signed with the active kid.
"""
from __future__ import annotations
import os
import sys
from cryptography.fernet import Fernet

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from services import crypto, auth


def run_fernet_rotation_drill():
    print("=" * 70)
    print("1. RUNNING MULTIFERNET PHI ENCRYPTION KEY ROTATION DRILL")
    print("=" * 70)

    # Step 1: Generate initial key (Key V1)
    key_v1 = Fernet.generate_key().decode()
    os.environ["PATIENT_ENCRYPTION_KEY"] = key_v1
    crypto.reset_key_cache()

    plaintext_name = "Eleanor Vance"
    plaintext_contact = "eleanor.vance@hillhouse.org"

    ct_name_v1 = crypto.encrypt_phi(plaintext_name)
    ct_contact_v1 = crypto.encrypt_phi(plaintext_contact)

    print(f"[Key V1 Active] Encrypted name: {ct_name_v1[:30]}...")
    print(f"[Key V1 Active] Encrypted contact: {ct_contact_v1[:30]}...")

    # Verify decrypt on V1
    assert crypto.decrypt_phi(ct_name_v1) == plaintext_name
    assert crypto.decrypt_phi(ct_contact_v1) == plaintext_contact
    print("[PASS] Decryption with Key V1 confirmed.")

    # Step 2: Key rotation - Generate Key V2 and set as Primary, V1 as Fallback
    key_v2 = Fernet.generate_key().decode()
    os.environ["PATIENT_ENCRYPTION_KEY"] = f"{key_v2},{key_v1}"
    crypto.reset_key_cache()
    print(f"\n[ROTATION] Promoted Key V2 to primary, Key V1 kept in keyring.")

    # Step 3: Verify old data encrypted with Key V1 is STILL READABLE
    decrypted_old_name = crypto.decrypt_phi(ct_name_v1)
    decrypted_old_contact = crypto.decrypt_phi(ct_contact_v1)
    assert decrypted_old_name == plaintext_name
    assert decrypted_old_contact == plaintext_contact
    print(f"[PASS] Old records encrypted with Key V1 successfully decrypted: '{decrypted_old_name}'")

    # Step 4: Verify new data is encrypted using Key V2
    new_patient_name = "Dr. John Montague"
    ct_name_v2 = crypto.encrypt_phi(new_patient_name)
    assert crypto.decrypt_phi(ct_name_v2) == new_patient_name
    # Verify that a Fernet instance using ONLY key_v2 can decrypt ct_name_v2
    assert Fernet(key_v2.encode()).decrypt(ct_name_v2.encode()).decode() == new_patient_name
    print(f"[PASS] New records encrypted under Key V2: '{new_patient_name}'")

    # Step 5: Perform in-place rotation upgrade on old ciphertext
    rotated_ct_name = crypto.rotate_phi(ct_name_v1)
    # The rotated ciphertext should now be decryptable with Key V2 alone!
    assert Fernet(key_v2.encode()).decrypt(rotated_ct_name.encode()).decode() == plaintext_name
    print(f"[PASS] Historical ciphertext re-encrypted under Key V2 via MultiFernet.rotate().")


def run_jwt_kid_rotation_drill():
    print("\n" + "=" * 70)
    print("2. RUNNING JWT KID-BASED KEY ROTATION DRILL")
    print("=" * 70)

    secret_v1 = "trustfed-high-entropy-jwt-secret-2026-v1-alpha"
    secret_v2 = "trustfed-high-entropy-jwt-secret-2026-v2-beta-rotated"

    # Step 1: Active kid = "key-2026-v1"
    os.environ["JWT_KEY_RING"] = f"key-2026-v1:{secret_v1}"
    os.environ["JWT_ACTIVE_KID"] = "key-2026-v1"
    auth.reset_auth_key_cache()

    claims = {"sub": "dr.patel@hospital1.org", "role": "doctor", "hospital_id": "1"}
    token_v1 = auth.create_token(claims, ttl=300)

    import jwt
    unverified_header_v1 = jwt.get_unverified_header(token_v1)
    assert unverified_header_v1.get("kid") == "key-2026-v1"
    payload_v1 = auth.decode_token(token_v1)
    assert payload_v1["sub"] == "dr.patel@hospital1.org"
    print(f"[Key V1 Active] Token generated with kid '{unverified_header_v1.get('kid')}'. Successfully decoded.")

    # Step 2: Rotate active kid to "key-2026-v2", keep "key-2026-v1" in keyring
    os.environ["JWT_KEY_RING"] = f"key-2026-v2:{secret_v2},key-2026-v1:{secret_v1}"
    os.environ["JWT_ACTIVE_KID"] = "key-2026-v2"
    auth.reset_auth_key_cache()
    print(f"\n[ROTATION] Promoted 'key-2026-v2' to active, 'key-2026-v1' retained in keyring.")

    # Step 3: Verify old token issued under key-2026-v1 is STILL VALID
    decoded_old_token = auth.decode_token(token_v1)
    assert decoded_old_token["sub"] == "dr.patel@hospital1.org"
    print(f"[PASS] Old token with kid 'key-2026-v1' remains valid and decoded without disruption.")

    # Step 4: Verify newly issued token has kid 'key-2026-v2'
    token_v2 = auth.create_token({"sub": "admin@trustfed.org", "role": "global_admin"}, ttl=300)
    unverified_header_v2 = jwt.get_unverified_header(token_v2)
    assert unverified_header_v2.get("kid") == "key-2026-v2"
    decoded_new_token = auth.decode_token(token_v2)
    assert decoded_new_token["sub"] == "admin@trustfed.org"
    print(f"[PASS] New token signed with active kid '{unverified_header_v2.get('kid')}'.")

    # Step 5: Verify tampering or forged signature is rejected
    tampered = token_v2[:-4] + "AAAA"
    try:
        auth.decode_token(tampered)
        raise AssertionError("Tampered token should have been rejected!")
    except ValueError as e:
        assert "signature" in str(e).lower()
        print(f"[PASS] Tampered token correctly rejected: {e}")

    print("\n" + "=" * 70)
    print("ALL ROTATION DRILLS PASSED: ZERO DATA LOSS & ZERO ACCESS INTERRUPTION")
    print("=" * 70)


if __name__ == "__main__":
    run_fernet_rotation_drill()
    run_jwt_kid_rotation_drill()

