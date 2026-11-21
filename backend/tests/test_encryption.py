"""Provider-key encryption at rest."""

from __future__ import annotations

import pytest

from app.core import crypto


def test_encrypt_decrypt_round_trip() -> None:
    secret = "sk-test-ABCDEFGH12345678"
    token = crypto.encrypt(secret)
    assert isinstance(token, bytes)
    # Stored value is ciphertext, not the plaintext key.
    assert secret.encode() not in token
    assert crypto.decrypt(token) == secret


def test_key_hint_last_four() -> None:
    assert crypto.key_hint("sk-abcd1234") == "1234"
    assert crypto.key_hint("ab") == "****"


def test_decrypt_invalid_token_raises() -> None:
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(b"not-a-valid-fernet-token")
