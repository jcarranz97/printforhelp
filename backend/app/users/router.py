"""Admin-only user management routes (Phase 1)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.contributions import service as contributions_service
from app.database import get_db
from app.dependencies import AdminUser, CurrentActiveUser

from . import schemas, service
from .constants import USER_SEARCH_LIMIT_DEFAULT, USER_SEARCH_LIMIT_MAX

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


@router.get("/search", response_model=list[schemas.UserSearchResult])
async def search_users(
    _user: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str, Query(max_length=64)] = "",
    limit: Annotated[
        int, Query(ge=1, le=USER_SEARCH_LIMIT_MAX)
    ] = USER_SEARCH_LIMIT_DEFAULT,
) -> list[schemas.UserSearchResult]:
    """Typeahead search for @mention autocomplete (any logged-in user)."""
    users = service.search_users(db, q, limit)
    return [schemas.UserSearchResult.model_validate(u) for u in users]


@router.get("/{username}/profile", response_model=schemas.PublicUserProfile)
async def get_public_profile(
    username: str,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.PublicUserProfile:
    """Return a user's public profile by handle: identity + projects (no auth).

    Email is never exposed. Unknown, deactivated, or system accounts return
    404 so a guessed handle reveals nothing.
    """
    user = service.get_public_profile_user(db, username)
    projects = contributions_service.list_public_for_user(db, user.id)
    return schemas.PublicUserProfile(
        user=schemas.PublicProfileResponse.model_validate(user),
        projects=projects,
        projects_count=len(projects),
    )


@router.put("/me", response_model=schemas.MeResponse)
async def update_my_profile(
    payload: schemas.ProfileUpdate,
    user: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.MeResponse:
    """Update the caller's own public profile (name, bio, avatar picture)."""
    updated = service.update_own_profile(db, user, payload)
    return schemas.MeResponse(
        **schemas.UserResponse.model_validate(updated).model_dump(),
        flags=service.get_user_flags(db, updated.id),
    )


@router.put("/me/username", response_model=schemas.UserResponse)
async def set_my_username(
    payload: schemas.UsernameChoice,
    user: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.UserResponse:
    """Pick your own username (one-time, for Google sign-ups)."""
    updated = service.set_own_username(db, user, payload.username)
    return schemas.UserResponse.model_validate(updated)


@router.put("/me/locale", response_model=schemas.UserResponse)
async def set_my_locale(
    payload: schemas.LocaleChoice,
    user: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.UserResponse:
    """Persist the caller's preferred locale (UI + email language)."""
    updated = service.set_own_locale(db, user, payload.locale)
    return schemas.UserResponse.model_validate(updated)


@router.put("/me/flags/{key}", response_model=schemas.UserFlagsResponse)
async def set_my_flag(
    key: str,
    payload: schemas.FlagUpdate,
    user: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.UserFlagsResponse:
    """Set one of the caller's own self-assignable flags (e.g. ``maker``)."""
    flags = service.set_own_flag(db, user, key, payload.value)
    return schemas.UserFlagsResponse(flags=flags)


@router.put("/{user_id}/flags/{key}", response_model=schemas.UserFlagsResponse)
async def set_user_flag(
    user_id: UUID,
    key: str,
    payload: schemas.FlagUpdate,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.UserFlagsResponse:
    """Grant or revoke any registered flag on a user (admin only)."""
    flags = service.set_flag_as_admin(db, user_id, key, payload.value, admin)
    return schemas.UserFlagsResponse(flags=flags)


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
