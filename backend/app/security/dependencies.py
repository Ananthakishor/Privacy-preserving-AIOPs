"""
backend/app/security/dependencies.py
FastAPI dependency functions for authentication and authorization.

These are injected into route functions using FastAPI's Depends() system.
Every protected endpoint calls get_current_user() which validates the JWT
and enforces tenant isolation automatically.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.collector import Collector
from .auth import decode_token, verify_password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Validate JWT token and return the authenticated user.
    Raises HTTP 401 if the token is missing, invalid, or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(*roles: str):
    """
    Dependency factory: enforce that the current user has one of the specified roles.
    Usage: Depends(require_role("admin", "operator"))
    """
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not authorized for this action"
            )
        return current_user
    return checker


def check_tenant_access(user: User, tenant_id: str):
    """
    Raise HTTP 403 if the user is not an admin and tries to access another tenant's data.
    Admins can access all tenants (for fleet management).
    """
    if user.role != "admin" and user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this tenant's data is not authorized"
        )


def get_collector_from_api_key(
    x_collector_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Collector:
    """
    Authenticate a collector using the X-Collector-API-Key header.
    The API key is stored as a bcrypt hash — we verify against the hash.
    """
    if not x_collector_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Collector API key required"
        )
    if len(x_collector_api_key.encode()) > 72:
        raise HTTPException(401, "Invalid collector API key")
    collectors = db.query(Collector).all()
    for collector in collectors:
        if verify_password(x_collector_api_key, collector.api_key_hash):
            return collector
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid collector API key"
    )
