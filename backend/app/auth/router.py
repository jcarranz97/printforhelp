"""Auth HTTP routes: login, current user, password change."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import CurrentActiveUser
from app.users import service as users_service
from app.users.schemas import MeResponse, UserRegister, UserResponse

from . import service
from .schemas import MessageResponse, PasswordChange, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
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
async def login(
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


@router.get("/me", response_model=MeResponse)
async def read_me(
    current_user: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> MeResponse:
    """Return the authenticated user's profile plus their generic flags."""
    return MeResponse(
        **UserResponse.model_validate(current_user).model_dump(),
        flags=users_service.get_user_flags(db, current_user.id),
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
