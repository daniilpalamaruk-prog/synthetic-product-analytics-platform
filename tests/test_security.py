from cryptography.fernet import Fernet

from saasgen.security.pii import (
    decrypt_value,
    encrypt_value,
    normalize_email,
    normalize_phone,
    pseudonymize,
)


def test_pii_normalization_and_keyed_pseudonymization():
    secret = "unit-test-secret-at-least-16-bytes"
    assert normalize_email("  User@Example.TEST ") == "user@example.test"
    assert normalize_phone("+1 (555) 012-3456") == "+15550123456"
    assert pseudonymize("stable", secret) == pseudonymize("stable", secret)
    assert pseudonymize("stable", secret) != pseudonymize("stable", secret + "-other")


def test_authenticated_encryption_roundtrip_and_tamper_detection():
    key = Fernet.generate_key()
    token = encrypt_value("synthetic@example.test", key)
    assert decrypt_value(token, key) == "synthetic@example.test"
    broken = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")
    try:
        decrypt_value(broken, key)
    except ValueError as exc:
        assert "invalid" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("tampered ciphertext was accepted")
