"""
Security helpers: password hashing/verification (bcrypt) and, as a
placeholder for future auth work, JWT access-token creation.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import settings


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt.

    bcrypt has a 72-byte input limit; we encode as UTF-8 and rely on
    bcrypt's own truncation-safe handling of the salt/round parameters.
    """
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        # Malformed hash in the DB — never let this raise into a 500 crash path.
        return False


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token. Not wired to an endpoint yet —
    provided so the /auth module has a ready-made path to login."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
from jose import JWTError, jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jose.JWTError on any failure
    (bad signature, malformed token, expired token, etc.)."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])