"""backend/app/schemas/auth.py — Auth request/response schemas."""
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    tenant_id: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    tenant_id: str
    is_active: bool

    class Config:
        from_attributes = True
