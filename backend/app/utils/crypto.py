import base64
import hashlib

from cryptography.fernet import Fernet


def _derive_key(secret_key: str) -> bytes:
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(value: str, secret_key: str) -> str:
    fernet = Fernet(_derive_key(secret_key))
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(token: str, secret_key: str) -> str:
    fernet = Fernet(_derive_key(secret_key))
    return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
