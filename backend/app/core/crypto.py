"""Symmetric encryption for secrets held in the application database.

Data source passwords have to be stored — the app reconnects to the customer's
database long after whoever configured it has gone home — but they must never
sit in the database as plaintext, and they must never be returned to a browser.

The key is derived from APP_SECRET_KEY. Rotating that secret makes existing
stored passwords undecryptable, which is the correct behaviour: the operator
re-enters them rather than the app silently continuing to use a secret that was
supposed to have been retired.
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("mediextract.crypto")


class SecretDecryptionError(RuntimeError):
    """Raised when a stored secret cannot be decrypted with the current key."""


def _fernet(app_secret_key: str) -> Fernet:
    """Derive a Fernet key from the application secret.

    SHA-256 rather than using the secret directly: Fernet needs exactly 32
    bytes of urlsafe-base64, and APP_SECRET_KEY is free-form.
    """
    digest = hashlib.sha256(app_secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str, app_secret_key: str) -> str:
    """Encrypt a secret for storage. Empty input stays empty."""
    if not plaintext:
        return ""
    return _fernet(app_secret_key).encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str, app_secret_key: str) -> str:
    """Decrypt a stored secret."""
    if not ciphertext:
        return ""
    try:
        return _fernet(app_secret_key).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise SecretDecryptionError(
            "Stored credential could not be decrypted — APP_SECRET_KEY has "
            "probably changed since it was saved. Re-enter the password."
        ) from exc
