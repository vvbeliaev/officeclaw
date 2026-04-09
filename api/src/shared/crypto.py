# api/src/crypto.py
import json
from cryptography.fernet import Fernet
from src.config import get_settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_settings().encryption_key.encode())
    return _fernet


def encrypt_json(data: dict) -> bytes:
    return _get_fernet().encrypt(json.dumps(data).encode())


def decrypt_json(ciphertext: bytes) -> dict:
    return json.loads(_get_fernet().decrypt(ciphertext))
