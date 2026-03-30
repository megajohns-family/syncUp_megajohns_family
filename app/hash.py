from passlib.hash import argon2


def hash_password(password: str) -> str:
    return argon2.using(rounds=4, memory_cost=65536, parallelism=2).hash(password)


def verify_password(plain: str, stored: str) -> bool:
    try:
        return argon2.verify(plain, stored)
    except Exception:
        return False