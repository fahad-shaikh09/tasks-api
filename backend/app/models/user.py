"""
User model for authentication and user management.
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from pydantic import EmailStr, validator
import re


# ============================================
# TABLE MODEL (Database)
# ============================================

class User(SQLModel, table=True):
    """
    User table model with hashed password.

    Never expose hashed_password in API responses!
    Use UserRead schema instead.
    """
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    username: str = Field(unique=True, index=True, max_length=50)
    full_name: str = Field(max_length=100)
    hashed_password: str = Field(max_length=255)

    # Account status
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    is_verified: bool = Field(default=False)

    # Email verification
    verification_token: Optional[str] = Field(default=None, max_length=100)
    verification_token_expires: Optional[datetime] = None

    # Password reset
    reset_token: Optional[str] = Field(default=None, max_length=100)
    reset_token_expires: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )
    last_login: Optional[datetime] = None


# ============================================
# API SCHEMAS (No table - for API I/O)
# ============================================

class UserCreate(SQLModel):
    """
    Schema for user registration (signup).

    Includes plain password that will be hashed before storage.
    """
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=100)

    @validator("username")
    def username_alphanumeric(cls, v):
        """Validate username contains only alphanumeric and underscores."""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username must be alphanumeric (underscores allowed)")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "password": "securepassword123"
            }
        }


class UserRead(SQLModel):
    """
    Schema for reading user data.

    NEVER includes hashed_password or tokens.
    """
    id: int
    email: EmailStr
    username: str
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "is_active": True,
                "is_verified": True,
                "created_at": "2024-01-01T12:00:00"
            }
        }


class UserUpdate(SQLModel):
    """
    Schema for updating user data.

    All fields optional.
    """
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)

    @validator("username")
    def username_alphanumeric(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username must be alphanumeric (underscores allowed)")
        return v


class UserLogin(SQLModel):
    """Schema for user login."""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class Token(SQLModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    """Schema for data encoded in JWT token."""
    user_id: Optional[int] = None


# ============================================
# PASSWORD RESET SCHEMAS
# ============================================

class PasswordResetRequest(SQLModel):
    """Schema for requesting password reset."""
    email: EmailStr


class PasswordResetConfirm(SQLModel):
    """Schema for confirming password reset."""
    token: str
    new_password: str = Field(min_length=8, max_length=100)


class PasswordChange(SQLModel):
    """Schema for changing password (when logged in)."""
    current_password: str
    new_password: str = Field(min_length=8, max_length=100)

    @validator("new_password")
    def passwords_different(cls, v, values):
        if "current_password" in values and v == values["current_password"]:
            raise ValueError("New password must be different from current password")
        return v


# ============================================
# EMAIL VERIFICATION SCHEMAS
# ============================================

class EmailVerificationRequest(SQLModel):
    """Schema for requesting new verification email."""
    email: EmailStr


class EmailVerificationConfirm(SQLModel):
    """Schema for confirming email verification."""
    token: str
