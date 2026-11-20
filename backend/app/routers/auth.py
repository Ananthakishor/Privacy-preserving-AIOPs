"""backend/app/routers/auth.py — Authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..schemas.auth import TokenResponse, UserResponse
from ..security.auth import verify_password, create_access_token
from ..security.dependencies import get_current_user
from ..services.audit_service import log_audit

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate user and return a JWT access token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        log_audit("login_failed", "unknown", "unknown")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is inactive")

    token = create_access_token({"sub": user.id, "tenant_id": user.tenant_id, "role": user.role})
    log_audit("login_success", user.id, user.tenant_id, {"email": user.email})
    return TokenResponse(access_token=token, token_type="bearer", role=user.role, tenant_id=user.tenant_id)


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Logout — stateless JWT: just log the action."""
    log_audit("logout", current_user.id, current_user.tenant_id)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user
