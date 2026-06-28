"""Admin-only user management routes (Phase 1)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AdminUser

from . import schemas, service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[schemas.UserResponse])
async def list_users(
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[schemas.UserResponse]:
    """List all users (admin only)."""
    return [schemas.UserResponse.model_validate(u) for u in service.list_users(db)]


@router.post("", response_model=schemas.UserResponse, status_code=201)
async def create_user(
    payload: schemas.UserCreate,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.UserResponse:
    """Provision a new account (admin only, FR-007)."""
    user = service.create_user(db, payload, admin)
    return schemas.UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=schemas.UserResponse)
async def get_user(
    user_id: UUID,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.UserResponse:
    """Get a single user (admin only)."""
    return schemas.UserResponse.model_validate(
        service.get_user_by_id_or_raise(db, user_id)
    )


@router.put("/{user_id}/role", response_model=schemas.UserResponse)
async def update_role(
    user_id: UUID,
    payload: schemas.RoleUpdate,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.UserResponse:
    """Change a user's role (admin only, FR-010 / FR-014)."""
    user = service.update_role(db, user_id, payload.role, admin)
    return schemas.UserResponse.model_validate(user)


@router.put("/{user_id}/password", response_model=schemas.UserResponse)
async def reset_password(
    user_id: UUID,
    payload: schemas.PasswordReset,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.UserResponse:
    """Set a new password for any user (admin only, Phase 1)."""
    user = service.set_password(db, user_id, payload.new_password, admin)
    return schemas.UserResponse.model_validate(user)


@router.post("/{user_id}/deactivate", response_model=schemas.UserResponse)
async def deactivate_user(
    user_id: UUID,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.UserResponse:
    """Deactivate a user (admin only, FR-012 / FR-014)."""
    user = service.deactivate_user(db, user_id, admin)
    return schemas.UserResponse.model_validate(user)


@router.post("/{user_id}/reactivate", response_model=schemas.UserResponse)
async def reactivate_user(
    user_id: UUID,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.UserResponse:
    """Reactivate a user (admin only, FR-012)."""
    user = service.reactivate_user(db, user_id, admin)
    return schemas.UserResponse.model_validate(user)
