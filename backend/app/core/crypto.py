"""Encryption of provider API keys at rest.

Uses Fernet (authenticated AES-128-CBC + HMAC-SHA256, random IV per token) with a
32-byte url-safe key from ``OMNIDESK_MASTER_KEY``. Plaintext keys are never stored
or logged; only the ciphertext token and a non-sensitive last-4 hint are kept.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

_fernet = Fernet(get_settings().omnidesk_master_key.encode())


class DecryptionError(Exception):
    """Raised when a stored ciphertext cannot be decrypted (wrong/rotated key)."""


def encrypt(plaintext: str) -> bytes:
    return _fernet.encrypt(plaintext.encode())


def decrypt(token: bytes) -> str:
    try:
        return _fernet.decrypt(bytes(token)).decode()
    except InvalidToken as exc:
        raise DecryptionError("Could not decrypt stored key") from exc


def key_hint(plaintext: str) -> str:
    """Non-sensitive display hint (last 4 chars)."""
    return plaintext[-4:] if len(plaintext) >= 4 else "****"
