"""
Security utilities for password hashing and JWT token management.
Uses pwdlib with Argon2 for password hashing.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import settings


# ============================================
# PASSWORD HASHING WITH PWDLIB/ARGON2
# ============================================

# Initialize password hasher with Argon2
password_hash = PasswordHash((
    Argon2Hasher(
        memory_cost=65536,  # 64 MB memory
        time_cost=3,        # 3 iterations
        parallelism=4,      # 4 parallel threads
        hash_len=32,        # 32 bytes output
        salt_len=16         # 16 bytes salt
    ),
))


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.

    Args:
        password: Plain text password

    Returns:
        Hashed password string (safe to store in database)
    """
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password from user input
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception:
        # Handle any verification errors (malformed hash, etc.)
        return False


# ============================================
# JWT TOKEN MANAGEMENT
# ============================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary containing claims to encode (e.g., {"sub": user_id})
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    # Encode JWT
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload (dict) if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
