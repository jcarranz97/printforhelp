"""Auth HTTP routes: login, current user, password change."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import CurrentActiveUser
from app.ratelimit import (
    FORGOT_PASSWORD_LIMIT,
    GOOGLE_LOGIN_LIMIT,
    LOGIN_LIMIT,
    REGISTER_LIMIT,
    RESET_PASSWORD_LIMIT,
    limiter,
)
from app.users import service as users_service
from app.users.schemas import MeResponse, UserRegister, UserResponse

from . import service
from .schemas import (
    ForgotPasswordRequest,
    GoogleLoginRequest,
    MessageResponse,
    PasswordChange,
    ResetPasswordRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit(REGISTER_LIMIT)
async def register(
    request: Request,
    payload: UserRegister,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Self-register an account and return a JWT (FR-001).

    Registration only needs name + email + password; the new account is
    logged in immediately (no email confirmation in v1).
    """
    user = users_service.register_user(db, payload)
    token = service.create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(LOGIN_LIMIT)
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Exchange username/password for a JWT (FR-003)."""
    user = service.authenticate(db, form_data.username, form_data.password)
    token = service.create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/google", response_model=TokenResponse)
@limiter.limit(GOOGLE_LOGIN_LIMIT)
async def google_login(
    request: Request,
    payload: GoogleLoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Sign in with Google, creating the account on first login (IR-001)."""
    user = users_service.login_or_create_google_user(db, payload.id_token)
    token = service.create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit(FORGOT_PASSWORD_LIMIT)
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Email a password-reset link if the address has an account.

    Always returns the same message whether or not the email is
    registered, so it can't be used to probe which emails exist.
    """
    service.request_password_reset(db, payload.email)
    return MessageResponse(
        message="If that email has an account, we sent a reset link."
    )


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit(RESET_PASSWORD_LIMIT)
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Set a new password using a token from the reset email."""
    service.reset_password_with_token(db, payload.token, payload.new_password)
    return MessageResponse(message="Password updated.")


@router.get("/me", response_model=MeResponse)
async def read_me(
    current_user: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> MeResponse:
    """Return the authenticated user's profile plus their generic flags."""
    return MeResponse(
        **UserResponse.model_validate(current_user).model_dump(),
        flags=users_service.get_user_flags(db, current_user.id),
        username_change_available_at=users_service.username_change_available_at(
            db, current_user.id
        ),
    )


@router.put("/me/password", response_model=MessageResponse)
async def change_my_password(
    payload: PasswordChange,
    current_user: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Change the authenticated user's password (FR-005)."""
    service.change_password(
        db, current_user, payload.current_password, payload.new_password
    )
    return MessageResponse(message="Password updated.")
