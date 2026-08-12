import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app

def get_fernet_key(secret_phrase: str = None) -> bytes:
    if not secret_phrase:
        secret_phrase = os.getenv("ENCRYPTION_KEY", "trademerc-default-encryption-secret-key-32bytes")
    
    # Derive a key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'trademerc_salt_static_2026',
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_phrase.encode()))
    return key

def encrypt_credential(plain_text: str) -> str:
    if not plain_text:
        return ""
    key = get_fernet_key()
    f = Fernet(key)
    return f.encrypt(plain_text.encode()).decode()

def decrypt_credential(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    try:
        key = get_fernet_key()
        f = Fernet(key)
        return f.decrypt(cipher_text.encode()).decode()
    except Exception:
        return "[Decryption Failed]"
