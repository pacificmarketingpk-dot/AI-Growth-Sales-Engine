"""Encrypt OAuth tokens at rest with a key derived from SECRET_KEY."""
import base64
import hashlib
import json

from cryptography.fernet import Fernet

from app.config import get_settings


def _fernet() -> Fernet:
    key = hashlib.sha256(("tokens:" + get_settings().secret_key).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_json(data: dict) -> str:
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_json(token: str) -> dict:
    return json.loads(_fernet().decrypt(token.encode()))
