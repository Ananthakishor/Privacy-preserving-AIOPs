"""
backend/app/security/auth.py
Password hashing and JWT token utilities.

We use:
- passlib with bcrypt for password hashing (never store plaintext passwords)
- python-jose for JWT creation and validation
- HS256 algorithm (symmetric — fast for prototype; use RS256 in production)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from ..config import get_settings

settings = get_settings()

# CryptContext selects bcrypt as the hashing algorithm
# bcrypt is a deliberately slow hash — this protects against brute-force attacks
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against a stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt. Store the result, never the original."""
    return pwd_context.hash(plain_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT token containing the provided data.
    The token expires after ACCESS_TOKEN_EXPIRE_MINUTES (default 60 minutes).
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token. Raises JWTError if invalid or expired.
    Returns the payload dict (contains sub, tenant_id, role, exp).
    """
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
