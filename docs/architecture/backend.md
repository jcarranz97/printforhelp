# Backend Architecture

PrintForHelp's backend follows a modular, domain-driven architecture
using **FastAPI** with clear separation of concerns. Each business
domain — `auth`, `users`, `organizations`, `resources`,
`collection_centers`, `requests`, `contributions`,
`ownership_transfers`, `audit_log`, `discovery` — is a self-contained
module with its own router, schemas, models, services, and
exceptions. The schema modelled in
[`database-schema.md`](database-schema.md) is implemented one domain
at a time, behind a uniform REST surface defined in
[`api-specification.md`](api-specification.md).

## Architecture Overview

- **Domain-Driven Design** — each business domain is a separate
  module with the seven canonical files used in the Colony project
  (router · schemas · models · service · dependencies · exceptions
  · constants).
- **Polymorphic Ownership at the Service Layer** — the two-FK +
  CHECK pattern on `resources` / `collection_centers` / `requests` is
  resolved by a small set of helper functions in `app/permissions.py`
  that every domain's service layer calls before performing a
  mutating operation. There is no Owner ORM hierarchy; principals
  are looked up by FK.
- **Soft Deletes Only** — the global `BaseModel` provides `active`,
  `created_at`, `updated_at`. The codebase never calls `db.delete()`
  on user-created entities.
- **Domain Exceptions, Never `HTTPException` in Services** — services
  raise subclasses of `AppExceptionError`; a global handler converts
  them to the standard `{success, error}` envelope.
- **Type Safety** — Pyright strict on the backend; every public
  function carries explicit annotations.

## Project Structure

```text
backend/
├── alembic/                        # Database migrations (Alembic)
│   ├── versions/
│   └── env.py
├── app/
│   ├── auth/                       # JWT issuance + session
│   │   ├── router.py               # POST /auth/login, /register
│   │   ├── schemas.py              # LoginRequest, TokenResponse
│   │   ├── service.py              # password hashing, JWT encode/decode
│   │   ├── dependencies.py         # get_current_user, CurrentActiveUser
│   │   ├── exceptions.py
│   │   ├── constants.py
│   │   └── utils.py                # Argon2ID hash / verify
│   ├── users/                      # User profile + role management
│   │   ├── router.py               # GET/PUT /users, PUT /users/{id}/role
│   │   ├── schemas.py
│   │   ├── models.py               # User
│   │   ├── service.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   └── constants.py
│   ├── organizations/              # Orgs + OrganizationMembership
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py               # Organization, OrganizationMembership
│   │   ├── service.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   └── constants.py
│   ├── resources/                      # Catalog of printable designs
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py               # Resource
│   │   ├── service.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   └── constants.py
│   ├── collection_centers/         # Drop-off locations + memberships
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py               # CollectionCenter,
│   │   │                           # CollectionCenterMembership
│   │   ├── service.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   └── constants.py
│   ├── requests/                   # Request + RequestItem
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py               # Request, RequestItem
│   │   ├── service.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   └── constants.py
│   ├── contributions/              # Maker contribution lifecycle
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py               # Contribution
│   │   ├── service.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   └── constants.py
│   ├── ownership_transfers/        # Polymorphic transfer state machine
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py               # OwnershipTransfer
│   │   ├── service.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   └── constants.py
│   ├── audit_log/                  # Append-only audit trail
│   │   ├── router.py               # GET /audit-log (admin/maintainer)
│   │   ├── schemas.py
│   │   ├── models.py               # AuditLog
│   │   ├── service.py              # write_event() called by every domain
│   │   └── constants.py            # documented action / target_type values
│   ├── discovery/                  # Aggregate read-only views
│   │   ├── router.py               # GET /discovery/next, /dashboard
│   │   ├── schemas.py
│   │   ├── service.py              # ranking + aggregation queries
│   │   └── exceptions.py
│   ├── scheduled/                  # Background jobs (FR-055, FR-114)
│   │   ├── expire_claims.py        # cron: release stale `claimed`
│   │   ├── expire_transfers.py     # cron: expire pending transfers
│   │   └── scheduler.py            # APScheduler bootstrap
│   ├── config.py                   # Global Pydantic Settings
│   ├── database.py                 # Engine + SessionLocal + get_db
│   ├── models.py                   # BaseModel (UUID, timestamps, active)
│   ├── exceptions.py               # AppExceptionError + global handlers
│   ├── dependencies.py             # CurrentActiveUser re-export, get_db
│   ├── permissions.py              # Polymorphic owner / member helpers
│   ├── pagination.py               # Cursor + offset pagination utils
│   └── main.py                     # FastAPI app factory
├── tests/                          # Test suite mirrors domain layout
│   ├── conftest.py                 # db, client fixtures
│   ├── auth/
│   ├── users/
│   ├── organizations/
│   ├── resources/
│   ├── collection_centers/
│   ├── requests/
│   ├── contributions/
│   ├── ownership_transfers/
│   └── discovery/
├── alembic.ini
└── pyproject.toml
```

> **Phase 4 implementation status.** `resources`, `requests`, and
> `contributions` are implemented (the `requests` domain holds both
> `Request` and `RequestItem`). Per-item progress aggregation lives in
> `requests.service.compute_item_progress` and is reused by request
> detail. `FR-055` stale-claim expiry lives in
> `contributions.service.expire_stale_claims` (unit-testable) with a
> thin `app/scheduled/expire_claims.py` runner; the APScheduler
> bootstrap (`scheduler.py`) and `ownership_transfers` / `discovery`
> domains remain target-state for later phases. Because the
> `resources`/`requests`/`contributions`/`collection_centers` services call
> one another, they use function-local imports to avoid import cycles.

## Domain Module Layout

Every domain has the same seven files. Adding a new domain is
strictly mechanical — copy an existing folder, swap the names, write
the FRs.

### router.py

Thin HTTP layer. Delegates to `service`; raises domain exceptions on
business-rule failures (never `HTTPException`).

```python
# app/resources/router.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentActiveUser

from . import service, schemas

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("/", response_model=schemas.ResourceResponse, status_code=201)
async def create_part(
    payload: schemas.ResourceCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentActiveUser,
) -> schemas.ResourceResponse:
    """Register a new Resource. Owner is the caller (default) or an Org
    the caller is an active member of (FR-015 / FR-108)."""
    return service.create_part(db, payload, current_user)


@router.post("/{resource_id}/discontinue", response_model=schemas.ResourceResponse)
async def discontinue_part(
    resource_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentActiveUser,
) -> schemas.ResourceResponse:
    """FR-075. Mark a Resource as `discontinued`. Owner only."""
    return service.discontinue_part(db, resource_id, current_user)
```

### schemas.py

Request/response Pydantic models. Use
`ConfigDict(from_attributes=True)` on responses so SQLAlchemy models
serialize directly.

```python
# app/resources/schemas.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    source_url: HttpUrl
    suggested_settings: str | None = None
    tags: list[str] = Field(default_factory=list)
    # Owner discriminator: exactly one of these two must be set
    owner_user_id: UUID | None = None
    owner_organization_id: UUID | None = None


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    source_url: str
    suggested_settings: str | None
    tags: list[str]
    status: str
    featured: bool
    creator_id: UUID
    owner_user_id: UUID | None
    owner_organization_id: UUID | None
    active: bool
    created_at: datetime
    updated_at: datetime
```

### models.py

SQLAlchemy 2.0 typed models inheriting `BaseModel` (provides
`id`, `created_at`, `updated_at`, `active`).

```python
# app/resources/models.py
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import BaseModel

if TYPE_CHECKING:
    from app.organizations.models import Organization
    from app.users.models import User


class Resource(BaseModel):
    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_organization_id IS NULL) OR "
            "(owner_user_id IS NULL AND owner_organization_id IS NOT NULL)",
            name="parts_one_owner",
        ),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    suggested_settings: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    owner_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )

    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id])
    owner_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[owner_user_id]
    )
    owner_organization: Mapped["Organization | None"] = relationship(
        "Organization", foreign_keys=[owner_organization_id]
    )
```

### service.py

Business logic. Static methods or plain functions — no class state.
Every mutating call ends with `db.commit()` + `db.refresh(obj)`.

```python
# app/resources/service.py
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit_log.service import write_audit
from app.permissions import (
    assert_caller_can_own_on_behalf_of,
    effective_owner_user_ids,
)
from app.users.models import User

from . import models, schemas
from .exceptions import (
    ResourceArchiveBlockedExceptionError,
    ResourceNotFoundExceptionError,
    ResourceOwnerRequiredExceptionError,
)


def create_part(
    db: Session, payload: schemas.ResourceCreate, caller: User
) -> models.Resource:
    """FR-015 / FR-108: register a Resource owned by the caller or an Org
    the caller is an active member of."""
    owner_user_id, owner_org_id = _resolve_owner(payload, caller)
    if owner_org_id is not None:
        assert_caller_can_own_on_behalf_of(db, caller, owner_org_id)

    part = models.Resource(
        name=payload.name,
        description=payload.description,
        source_url=str(payload.source_url),
        suggested_settings=payload.suggested_settings,
        tags=payload.tags,
        creator_id=caller.id,
        owner_user_id=owner_user_id,
        owner_organization_id=owner_org_id,
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


def discontinue_part(
    db: Session, resource_id: UUID, caller: User
) -> models.Resource:
    """FR-075. Only effective owners can flip status to `discontinued`."""
    part = _get_part_or_raise(db, resource_id)
    if caller.id not in effective_owner_user_ids(db, part):
        raise ResourceOwnerRequiredExceptionError(resource_id)

    part.status = "discontinued"
    db.commit()
    db.refresh(part)
    return part


def _get_part_or_raise(db: Session, resource_id: UUID) -> models.Resource:
    part = db.query(models.Resource).filter(
        models.Resource.id == resource_id, models.Resource.active.is_(True)
    ).first()
    if part is None:
        raise ResourceNotFoundExceptionError(resource_id)
    return part


def _resolve_owner(
    payload: schemas.ResourceCreate, caller: User
) -> tuple[UUID | None, UUID | None]:
    if payload.owner_organization_id is not None:
        return None, payload.owner_organization_id
    # Default: the caller owns the Resource personally
    return caller.id, None
```

### dependencies.py

Domain-level FastAPI dependencies (path-parameter resolvers, ownership
checks bundled as `Annotated` types). Re-export from `app.dependencies`
when used elsewhere.

```python
# app/resources/dependencies.py
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db

from . import service
from .exceptions import ResourceNotFoundExceptionError


def get_part_by_id(
    resource_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> service.models.Resource:
    part = service._get_part_or_raise(db, resource_id)
    return part


TargetPart = Annotated[service.models.Resource, Depends(get_part_by_id)]
```

### constants.py

Enums + error codes. Keep the enum classes simple — string-backed.

```python
# app/resources/constants.py
from enum import StrEnum


class ResourceStatus(StrEnum):
    ACTIVE = "active"
    DISCONTINUED = "discontinued"


class ErrorCode(StrEnum):
    PART_NOT_FOUND = "PART_NOT_FOUND"
    PART_OWNER_REQUIRED = "PART_OWNER_REQUIRED"
    PART_ARCHIVE_BLOCKED = "PART_ARCHIVE_BLOCKED"
    PART_NOT_AN_ORG_MEMBER = "PART_NOT_AN_ORG_MEMBER"
```

### exceptions.py

Domain exceptions inheriting `AppExceptionError`. The global handler
converts them to the JSON envelope.

```python
# app/resources/exceptions.py
from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class ResourceNotFoundExceptionError(AppExceptionError):
    def __init__(self, resource_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.PART_NOT_FOUND,
            message=f"Resource {resource_id} not found.",
            status_code=404,
        )


class ResourceOwnerRequiredExceptionError(AppExceptionError):
    def __init__(self, resource_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.PART_OWNER_REQUIRED,
            message=f"Action on Resource {resource_id} requires the effective owner.",
            status_code=403,
        )


class ResourceArchiveBlockedExceptionError(AppExceptionError):
    def __init__(self, resource_id: UUID, open_requests: int) -> None:
        super().__init__(
            error_code=ErrorCode.PART_ARCHIVE_BLOCKED,
            message=(
                f"Resource {resource_id} cannot be archived while {open_requests} "
                "open Request(s) reference it. Mark it `discontinued` or "
                "ask a maintainer to force-archive."
            ),
            status_code=409,
        )
```

## Global Architecture Components

### app/main.py

App factory. Loads CORS, exception handlers, all routers, and the
background scheduler (lazy — disabled under pytest).

```python
# app/main.py
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.audit_log.router import router as audit_router
from app.auth.router import router as auth_router
from app.collection_centers.router import router as cc_router
from app.config import settings
from app.contributions.router import router as contrib_router
from app.discovery.router import router as discovery_router
from app.exceptions import (
    AppExceptionError,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.organizations.router import router as orgs_router
from app.ownership_transfers.router import router as transfers_router
from app.resources.router import router as resources_router
from app.requests.router import router as requests_router
from app.scheduled.scheduler import start_scheduler, stop_scheduler
from app.users.router import router as users_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Bootstrap admin + start scheduled jobs."""
    _bootstrap_admin()
    start_scheduler()
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="Coordination platform for community 3D-printed aid",
        lifespan=lifespan,
    )

    app.add_exception_handler(AppExceptionError, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(ValueError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for r in (
        auth_router, users_router, organizations := orgs_router, resources_router,
        cc_router, requests_router, contrib_router, transfers_router,
        audit_router, discovery_router,
    ):
        app.include_router(r, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": "printforhelp-api"}

    return app


app = create_app()
```

### app/database.py

Single engine, sessionmaker, and `get_db` dependency. No surprises
versus the Colony layout.

```python
# app/database.py
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### app/models.py

Base class shared by every ORM model. UUID primary key, two
timestamps, and the soft-delete flag.

```python
# app/models.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
```

### app/dependencies.py

Re-exports the common `Annotated` types used across domains.

```python
# app/dependencies.py
from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import (
    get_current_active_user,
    get_current_user,
)
from app.database import get_db
from app.users.models import User

CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]

__all__ = ["CurrentUser", "CurrentActiveUser", "get_db"]
```

### app/permissions.py — polymorphic authorization helpers

The single most important "shared" module in the project. Every
mutating service call funnels its permission checks through one of
these helpers, so the polymorphic ownership rules in §3.10 of the
requirements doc are implemented in exactly one place.

```python
# app/permissions.py
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.collection_centers.models import (
    CollectionCenter,
    CollectionCenterMembership,
)
from app.organizations.models import Organization, OrganizationMembership
from app.resources.models import Resource
from app.requests.models import Request
from app.users.models import User


# ----------------------------------------------------------------------
# Effective owner of a Resource / CollectionCenter / Request (FR-109)
# ----------------------------------------------------------------------
def effective_owner_user_ids(
    db: Session, asset: Resource | CollectionCenter | Request
) -> set[UUID]:
    """Return the set of users that have owner-equivalent powers."""
    if isinstance(asset, Request):
        user_id, org_id = asset.requester_user_id, asset.requester_organization_id
    else:
        user_id, org_id = asset.owner_user_id, asset.owner_organization_id

    if user_id is not None:
        return {user_id}

    rows = (
        db.query(OrganizationMembership.user_id)
        .filter(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.role == "owner",
            OrganizationMembership.active.is_(True),
        )
        .all()
    )
    return {row.user_id for row in rows}


# ----------------------------------------------------------------------
# Effective members of a Collection Center (FR-110)
# ----------------------------------------------------------------------
def effective_cc_member_user_ids(
    db: Session, cc: CollectionCenter
) -> set[UUID]:
    """Per-center contributors + the owner principal's user set."""
    members: set[UUID] = set()

    rows = (
        db.query(CollectionCenterMembership.user_id)
        .filter(
            CollectionCenterMembership.collection_center_id == cc.id,
            CollectionCenterMembership.active.is_(True),
        )
        .all()
    )
    members.update(r.user_id for r in rows)

    if cc.owner_user_id is not None:
        members.add(cc.owner_user_id)
    else:
        rows = (
            db.query(OrganizationMembership.user_id)
            .filter(
                OrganizationMembership.organization_id == cc.owner_organization_id,
                OrganizationMembership.active.is_(True),
            )
            .all()
        )
        members.update(r.user_id for r in rows)

    return members


def has_global_override(user: User) -> bool:
    """Maintainers and admins can act on anything (NFR-006)."""
    return user.role in ("maintainer", "admin")


def assert_caller_can_own_on_behalf_of(
    db: Session, caller: User, organization_id: UUID
) -> None:
    """Used at registration time (FR-108). The caller must be an active
    member (any role) of the org they're registering an asset under."""
    from app.resources.exceptions import (
        ResourceNotAnOrgMemberExceptionError,  # local import avoids cycle
    )

    is_member = (
        db.query(OrganizationMembership.id)
        .filter(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == caller.id,
            OrganizationMembership.active.is_(True),
        )
        .first()
        is not None
    )
    if not is_member:
        raise ResourceNotAnOrgMemberExceptionError(caller.id, organization_id)
```

## Cross-Domain Communication

Domains do **not** import each other's `service.py` (matches the
Colony rule). The only sanctioned imports across domains are:

- ORM models (read-only inspection)
- `app.permissions` helpers (which import ORM models from multiple
  domains by design)
- `app.audit_log.service.write_audit()` — called from every domain's
  mutating service methods

When a domain needs another domain's business logic, the helper goes
into `app.permissions` (for authorization) or stays as a `_helper`
function inside the calling service (the Colony "shared local helper"
pattern). This keeps the dependency graph between domain `service.py`
files acyclic.

## Polymorphic Ownership: How It Plays Out at the Service Layer

`Resources`, `CollectionCenter`s, and `Request`s each carry two nullable
owner FKs with a `CHECK` enforcing "exactly one non-null." Service
code never branches on `if asset.owner_user_id is not None: ... else:
...`; that branching is delegated to `app.permissions`.

A typical mutating service method follows this pattern:

```python
def edit_part(db: Session, resource_id: UUID, payload, caller: User) -> Resource:
    part = _get_part_or_raise(db, resource_id)

    # Authorization: caller is effective owner OR global override
    if caller.id not in effective_owner_user_ids(db, part) \
            and not has_global_override(caller):
        raise ResourceOwnerRequiredExceptionError(resource_id)

    # Apply patch
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(part, field, value)

    db.commit()
    db.refresh(part)
    return part
```

## Ownership Transfer State Machine

`ownership_transfers/service.py` is the only place that mutates
ownership FKs. The state machine is implemented as four small methods
sharing a common `_load_transfer_or_raise` helper. Each state
transition is one transaction that does three things atomically:

1. Mutate the asset's ownership FKs (on `accept` / `force_transfer`)
2. Update the `OwnershipTransfer` row's status + `resolved_at`
3. Write an audit log entry

```python
# app/ownership_transfers/service.py — accept_transfer (sketch)
def accept_transfer(db: Session, transfer_id: UUID, acceptor: User) -> Transfer:
    t = _load_transfer_or_raise(db, transfer_id)
    _assert_can_accept(db, t, acceptor)            # raises on auth fail
    asset = _load_asset(db, t.asset_type, t.asset_id)

    # Atomic ownership swap
    if t.asset_type == "request":
        asset.requester_user_id = t.target_user_id
        asset.requester_organization_id = t.target_organization_id
    else:
        asset.owner_user_id = t.target_user_id
        asset.owner_organization_id = t.target_organization_id

    t.status = "accepted"
    t.resolved_by_id = acceptor.id
    t.resolved_at = datetime.now(UTC)

    write_audit(
        db, acceptor.id, "accept_ownership_transfer",
        "OwnershipTransfer", t.id,
    )
    db.commit()
    db.refresh(asset)
    return t
```

The `parts_one_owner` / `cc_one_owner` / `requests_one_requester`
`CHECK` constraints guarantee that any bug here aborts the transaction
rather than producing a corrupt row.

## Background Jobs

Two scheduled jobs live in `app/scheduled/`, both implemented with
APScheduler (in-process) for v1. Both run **inside the FastAPI process**
in development; in production the Helm chart runs a dedicated
"scheduler" replica with `START_SCHEDULER=true`.

### Auto-Expire Stale `claimed` Contributions (FR-055)

Runs every 30 minutes. Releases any Contribution that has been in
`claimed` for longer than `STALE_CLAIM_DAYS` (default 14):

```python
# app/scheduled/expire_claims.py
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.audit_log.service import write_audit
from app.config import settings
from app.contributions.models import Contribution


def expire_stale_claims(db: Session) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=settings.STALE_CLAIM_DAYS)
    stale = (
        db.query(Contribution)
        .filter(
            Contribution.status == "claimed",
            Contribution.claimed_at < cutoff,
            Contribution.active.is_(True),
        )
        .all()
    )
    for c in stale:
        c.status = "released"
        c.released_at = datetime.now(UTC)
        c.released_reason = "expired"
        # actor_id = system user (created on bootstrap)
        write_audit(db, settings.SYSTEM_USER_ID, "expire_ownership_transfer",
                    "Contribution", c.id, reason="stale_claim")
    db.commit()
    return len(stale)
```

### Auto-Expire Pending Ownership Transfers (FR-114)

Same pattern. Runs every 5 minutes. Flips
`OwnershipTransfer.status` from `pending` to `expired` when
`expires_at` has passed.

## Data Flow Architecture

```mermaid
graph TD
    A[HTTP Request] --> B[Router Layer]
    B --> C[Pydantic Validation]
    C --> D[Dependency Injection]
    D --> E{Auth Check}
    E -- "JWT / PAT" --> F[CurrentActiveUser]
    F --> G[Service Layer]
    G --> H[app/permissions.py]
    H -- "effective_owner / member" --> I[SQLAlchemy Models]
    I --> J[PostgreSQL]
    G --> K[write_audit]
    K --> J
    G --> L[Response Schema]
    L --> M[HTTP Response]

    N[APScheduler] --> O[expire_claims]
    N --> P[expire_transfers]
    O --> G
    P --> G
```

## Authentication & Security

### JWT + Personal Access Tokens

```python
# app/auth/config.py
from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_prefix = "AUTH_"
```

- `/auth/login` returns a JWT signed with `AUTH_SECRET_KEY`.
- Personal Access Tokens (`pforh_pat_…`) — created via
  `POST /api-tokens/` — work anywhere a JWT does. Resolution lives in
  `app/auth/dependencies.py::get_current_user`, which tries JWT first
  and falls back to PAT lookup if the token has the prefix.

### Password Hashing — Argon2ID via `pwdlib`

Matches Colony's standard (NFR-004):

```python
# app/auth/utils.py
from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _hasher.verify(plain, hashed)
```

### Authorization

- `CurrentActiveUser` resolves the JWT/PAT and raises 401/403 on
  invalid/inactive.
- `has_global_override(user)` is the canonical "is maintainer or
  admin" check.
- For polymorphic-ownership checks, services call
  `effective_owner_user_ids` (Resources/CCs/Requests) or
  `effective_cc_member_user_ids` (CC member powers).
- Frontend hides controls the caller cannot invoke, but every check
  is re-enforced server-side (NFR-006).

## Error Handling

### Exception Hierarchy

```python
# app/exceptions.py
class AppExceptionError(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 400,
        details: dict | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)
```

### Global Handler

Converts every `AppExceptionError` to the standard envelope. Routes
never raise `HTTPException` from within a service method.

```python
async def app_exception_handler(request: Request, exc: AppExceptionError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )
```

See [`api-specification.md`](api-specification.md) §Error Codes for
the full canonical list.

## Database Architecture

### Engine + Pool

Already shown above. Notable settings:

- `pool_pre_ping=True` — guards against stale connections
- `pool_recycle=300` — match Cloud SQL / RDS short-cycle behaviors
- `echo=settings.DEBUG` — full SQL trace in dev

### Migrations — Alembic

Every model change requires an Alembic migration. The Helm chart runs
`alembic upgrade head` in an init container before the API starts.

```bash
uv run alembic revision --autogenerate -m "add request_items"
uv run alembic upgrade head
```

Polymorphic-ownership `CHECK` constraints and partial unique indexes
(e.g. `uniq_org_owner_active`) are **not** autogenerated reliably;
review every migration and hand-add what's missing. The repo keeps
an `alembic/checks.md` checklist of which invariants need manual
verification per migration.

### No `ON DELETE CASCADE` from `users`

Per FR-013, deactivating a user must preserve their historical
attribution on Resources, Requests, Contributions, and audit log rows.
Foreign keys from those tables to `users.id` therefore default to
`ON DELETE RESTRICT`; the only cascades in the schema are
within-domain (`organizations → organization_memberships` and
`requests → request_items`).

## Validation & Serialization

### Pydantic 2.0

- `model_config = ConfigDict(from_attributes=True)` on every response
  model so SQLAlchemy ORM instances serialize directly.
- `Field(min_length=..., max_length=...)` for trivial limits;
  custom `field_validator` only when a constraint genuinely needs
  Python logic (e.g., the "exactly one of owner_user_id /
  owner_organization_id" check at the API boundary, in case a caller
  sets both).

### Boundary Check Example

```python
# app/resources/schemas.py — additional validator
from pydantic import model_validator


class ResourceCreate(BaseModel):
    # ... fields as above

    @model_validator(mode="after")
    def _exactly_one_owner_hint(self):
        # Either both omitted (server defaults to caller owns) or
        # exactly one provided. Both set is a client error.
        if self.owner_user_id is not None and self.owner_organization_id is not None:
            raise ValueError(
                "Specify either owner_user_id or owner_organization_id, not both."
            )
        return self
```

## Testing

### Fixtures (tests/conftest.py)

Per-test database created with `create_all` + dropped at teardown;
`TestClient` with `get_db` overridden:

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_URL = (
    "postgresql://test_user:test_pass@localhost:5433/test_printforhelp"
)
test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=test_engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

Each domain has its own `tests/<domain>/conftest.py` with domain
fixtures (e.g., `tests/resources/conftest.py` defines `user_owned_part`,
`org_owned_part`, `discontinued_part` fixtures).

### Conventions

Mirroring Colony:

- Test files mirror the domain layout: `tests/<domain>/test_<layer>.py`
- Class per feature: `class TestCreatePart:` with `def test_*` methods
- Every new endpoint needs at least:
  - `test_requires_auth` — 401 without token
  - `test_<happy_path>` — 200/201 with valid data
  - `test_not_found` — 404 for unknown ID
  - `test_other_user_cannot_access` — ownership isolation
  - `test_<conflict>` — 409 for uniqueness / state conflicts
- **Polymorphic-ownership** specific:
  - `test_user_owner_can_X` — direct user owner can do X
  - `test_org_member_can_X_when_org_owns` — org-member resolution
    via `effective_owner_user_ids`
  - `test_stranger_cannot_X` — non-owner, non-org-member, non-mod
    gets 403
- Tests hit a real PostgreSQL — never mock the DB.

## Configuration

```python
# app/config.py
from pydantic_settings import BaseSettings


class AdminSettings(BaseSettings):
    USERNAME: str = "admin"
    PASSWORD: str = "printforhelp-admin"

    class Config:
        env_prefix = "DEFAULT_ADMIN_"


class Settings(BaseSettings):
    APP_NAME: str = "PrintForHelp API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str
    SECRET_KEY: str
    ALLOWED_HOSTS: list[str] = ["http://localhost:3001"]

    # Bootstrap / scheduled-job tuning
    ADMIN: AdminSettings = AdminSettings()
    STALE_CLAIM_DAYS: int = 14            # FR-055
    PENDING_TRANSFER_DAYS: int = 7        # FR-114

    SYSTEM_USER_ID: str | None = None     # Set after bootstrap

    class Config:
        env_file = ".env"


settings = Settings()  # noqa: E501  - pyright: ignore[reportCallIssue]
```

## Logging

Structured JSON logging via a small custom formatter so log lines are
machine-parseable in production. Per-domain loggers use the
`__name__` convention so the source domain is always in the log line.
Logs about ownership transfers and auto-receive events get an extra
`event` key for easy filtering.

## Performance Considerations

- The discovery endpoints (`/discovery/next`, `/discovery/dashboard`)
  use the exact queries shown in [`database-schema.md`](database-schema.md)
  with the partial indexes that are already in place.
- The "What to print next" view is **not** cached in the DB — it's
  computed on every request, but the query is cheap because all
  filters hit indexed columns. If it later grows expensive, the
  natural cache point is a Redis layer in front of
  `discovery.service.list_next()`, invalidated whenever a
  Contribution status changes (NFR-003).
- Background jobs (`expire_claims`, `expire_transfers`) commit in
  bulk — one transaction per job run.

This architecture covers every functional requirement in
[`requirements.md`](../requirements.md) and every database invariant
in [`database-schema.md`](database-schema.md), while keeping each
domain small enough that a new feature usually fits in a single
folder.
