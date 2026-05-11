"""
Authentication endpoints for user registration, login, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import datetime, timedelta
import secrets

from app.core.database import get_session
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import (
    User,
    UserCreate,
    UserRead,
    UserLogin,
    Token,
    PasswordResetRequest,
    PasswordResetConfirm,
    EmailVerificationConfirm
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


# ============================================
# USER REGISTRATION (SIGNUP)
# ============================================

@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserCreate, db: Session = Depends(get_session)):
    """
    Register a new user.

    **Duplicate Prevention:**
    - Checks if email already exists
    - Checks if username already taken

    **Returns:**
    - User data (without password)
    - HTTP 201 on success
    - HTTP 400 if email/username already exists
    """
    # Check if email already exists
    existing_email = db.exec(
        select(User).where(User.email == user_data.email)
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    existing_username = db.exec(
        select(User).where(User.username == user_data.username)
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Hash the password
    hashed_password = hash_password(user_data.password)

    # Create new user
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


# ============================================
# USER LOGIN
# ============================================

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_session)
):
    """
    Login with email (in username field) and password.

    **OAuth2 compatible** - Uses form data with username/password fields.
    For OAuth2, email goes in the 'username' field.

    **Returns:**
    - JWT access token
    - HTTP 401 if credentials invalid
    - HTTP 403 if account inactive
    """
    # Find user by email (stored in username field for OAuth2 compatibility)
    user = db.exec(
        select(User).where(User.email == form_data.username)
    ).first()

    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.add(user)
    db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(access_token=access_token, token_type="bearer")


@router.post("/login/json", response_model=Token)
def login_json(credentials: UserLogin, db: Session = Depends(get_session)):
    """
    Login with JSON body (alternative to form data).

    **Use this for:**
    - Modern web apps that prefer JSON
    - Mobile apps
    - Non-OAuth2 clients

    **Returns:**
    - JWT access token
    """
    user = db.exec(
        select(User).where(User.email == credentials.email)
    ).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.add(user)
    db.commit()

    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(access_token=access_token, token_type="bearer")


# ============================================
# CURRENT USER
# ============================================

@router.get("/me", response_model=UserRead)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    **Requires:** Valid JWT token in Authorization header
    """
    return current_user


# ============================================
# EMAIL VERIFICATION
# ============================================

@router.post("/verify-email/request")
def request_email_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Request new email verification token.

    **Use case:** User didn't receive original email or token expired.
    """
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )

    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    token_expires = datetime.utcnow() + timedelta(hours=24)

    current_user.verification_token = verification_token
    current_user.verification_token_expires = token_expires
    db.add(current_user)
    db.commit()

    # TODO: Send verification email
    # send_verification_email(current_user.email, verification_token)

    return {
        "message": "Verification email sent",
        "token": verification_token  # Remove in production!
    }


@router.post("/verify-email/confirm")
def verify_email(
    verification: EmailVerificationConfirm,
    db: Session = Depends(get_session)
):
    """
    Verify email with token.

    **Sent via email** after registration or re-request.
    """
    user = db.exec(
        select(User).where(User.verification_token == verification.token)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid verification token"
        )

    if user.verification_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token expired"
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.add(user)
    db.commit()

    return {"message": "Email verified successfully"}


# ============================================
# PASSWORD RESET
# ============================================

@router.post("/password-reset/request")
def request_password_reset(
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_session)
):
    """
    Request password reset email.

    **Security:** Always returns success to prevent user enumeration.
    Actual email only sent if user exists.
    """
    user = db.exec(
        select(User).where(User.email == reset_request.email)
    ).first()

    # Always return success to prevent user enumeration
    if not user:
        return {
            "message": "If the email exists, a password reset link has been sent"
        }

    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    reset_expires = datetime.utcnow() + timedelta(hours=1)

    user.reset_token = reset_token
    user.reset_token_expires = reset_expires
    db.add(user)
    db.commit()

    # TODO: Send password reset email
    # send_password_reset_email(user.email, reset_token)

    return {
        "message": "If the email exists, a password reset link has been sent",
        "token": reset_token  # Remove in production!
    }


@router.post("/password-reset/confirm")
def reset_password(
    reset_confirm: PasswordResetConfirm,
    db: Session = Depends(get_session)
):
    """
    Confirm password reset with token and set new password.

    **Sent via email** after password reset request.
    """
    user = db.exec(
        select(User).where(User.reset_token == reset_confirm.token)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    if user.reset_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )

    # Update password
    user.hashed_password = hash_password(reset_confirm.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.add(user)
    db.commit()

    return {"message": "Password reset successful"}


# ============================================
# LOGOUT (Optional - for token blacklist)
# ============================================

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    Logout endpoint (placeholder).

    **Note:** JWTs are stateless. True logout requires:
    - Token blacklist (Redis)
    - Short token expiry
    - Client-side token deletion

    For now, client should delete the token.
    """
    # TODO: Implement token blacklist if needed
    # blacklist_token(token)

    return {"message": "Logged out successfully"}
