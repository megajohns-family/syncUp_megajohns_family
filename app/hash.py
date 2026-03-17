import hashlib
import os


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    pw_hash = hashlib.scrypt(
        password.encode(),
        salt=salt.encode(),
        n=16384,
        r=8,
        p=1
    ).hex()
    return f"{salt}${pw_hash}"


def verify_password(plain: str, stored: str) -> bool:
    try:
        salt, pw_hash = stored.split("$")
        return hashlib.scrypt(
            plain.encode(),
            salt=salt.encode(),
            n=16384,
            r=8,
            p=1
        ).hex() == pw_hash
    except ValueError:
        return False