"""Auth HTTP routes: login, current user, password change."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import CurrentActiveUser
from app.users.schemas import UserResponse

from . import service
from .exceptions import RegistrationDisabledExceptionError
from .schemas import MessageResponse, PasswordChange, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=403)
async def register() -> None:
    """Self-registration is disabled in v1 (FR-001, roadmap Phase 6)."""
    raise RegistrationDisabledExceptionError


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


@router.get("/me", response_model=UserResponse)
async def read_me(current_user: CurrentActiveUser) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


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
