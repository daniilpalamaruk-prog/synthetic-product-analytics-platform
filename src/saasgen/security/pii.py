"""PII normalization, keyed pseudonymization and authenticated encryption.

The generator emits obviously synthetic contact data so the ETL path can show how
PII is handled. Analytics code must use the HMAC identifiers produced here and
must never copy the source values into marts.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re

from cryptography.fernet import Fernet, InvalidToken

PII_FIELDS = frozenset({"name", "email", "phone", "ip_address"})


def normalize_email(value: str) -> str:
    """Return the canonical representation used before hashing."""
    return value.strip().casefold()


def normalize_phone(value: str) -> str:
    """Return a stable E.164-like representation for synthetic phone values."""
    value = value.strip()
    digits = re.sub(r"\D", "", value)
    if not digits:
        raise ValueError("phone must contain digits")
    return f"+{digits}"


def pseudonymize(value: str, secret: str | bytes) -> str:
    """Create a deterministic, non-reversible HMAC-SHA256 identifier."""
    key = secret.encode("utf-8") if isinstance(secret, str) else secret
    if len(key) < 16:
        raise ValueError("HMAC secret must contain at least 16 bytes")
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()


def _fernet(key: str | bytes) -> Fernet:
    raw = key.encode("ascii") if isinstance(key, str) else key
    try:
        decoded = base64.urlsafe_b64decode(raw)
    except Exception as exc:  # pragma: no cover - exact decoder exception is version-specific
        raise ValueError("PII encryption key must be a URL-safe Fernet key") from exc
    if len(decoded) != 32:
        raise ValueError("PII encryption key must decode to 32 bytes")
    return Fernet(raw)


def encrypt_value(value: str, key: str | bytes) -> str:
    """Encrypt a value with authenticated encryption (Fernet/AES + HMAC)."""
    return _fernet(key).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_value(token: str, key: str | bytes) -> str:
    """Decrypt and authenticate a Fernet token."""
    try:
        return _fernet(key).decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("encrypted PII token is invalid or was tampered with") from exc


def hmac_secret_from_env() -> str:
    secret = os.getenv("PII_HMAC_SECRET")
    if not secret:
        raise RuntimeError("PII_HMAC_SECRET is required for warehouse ingestion")
    return secret


def encryption_key_from_env() -> str | None:
    """Return an optional key; raw PII is dropped when reversible storage is not needed."""
    return os.getenv("PII_ENCRYPTION_KEY")
