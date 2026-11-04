import hashlib
import secrets


def generate_raw_token():
    return secrets.token_urlsafe(32)


def hash_token(raw_token):
    return hashlib.sha256(raw_token.encode()).hexdigest()
