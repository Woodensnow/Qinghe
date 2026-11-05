"""Node scrypt-compatible password hashes and cryptographic identifiers."""
import hashlib
import hmac
import secrets


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(str(password).encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64)
    return salt, digest.hex()


def verify_password(password, salt, expected):
    try:
        return hmac.compare_digest(hash_password(password, salt)[1], expected)
    except (ValueError, TypeError, AttributeError):
        return False


def make_id(prefix):
    return f'{prefix}_{secrets.token_hex(6)}'


def make_token():
    return secrets.token_hex(32)
