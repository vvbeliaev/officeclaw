# api/tests/test_crypto.py
from src.shared.crypto import encrypt_json, decrypt_json


def test_encrypt_decrypt_roundtrip():
    data = {"ANTHROPIC_API_KEY": "sk-ant-123", "TELEGRAM_TOKEN": "bot:456"}
    encrypted = encrypt_json(data)
    assert isinstance(encrypted, bytes)
    assert encrypted != str(data).encode()
    result = decrypt_json(encrypted)
    assert result == data


def test_encrypt_produces_different_ciphertext_each_time():
    data = {"key": "value"}
    enc1 = encrypt_json(data)
    enc2 = encrypt_json(data)
    assert enc1 != enc2  # Fernet uses random IV
