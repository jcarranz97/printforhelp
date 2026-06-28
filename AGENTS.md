# PrintForHelp

Coordination platform for the 3D printing community to help people in
need. Initial focus: medical splints (ferulas) for the June 2026
Venezuela earthquake. Long-term: general-purpose hub for community-
driven 3D-printed humanitarian aid.

**Stack**: FastAPI (Python 3.13) + PostgreSQL + Next.js 15 + Tailwind
v4 + HeroUI + MkDocs Material, all orchestrated via Docker Compose.
See `backend/AGENTS.md` and `frontend/AGENTS.md` for domain-specific
guidance.

## Quick Start

```bash
# First-time only — generate lock files
cd backend && uv sync && cd ..
cd frontend && npm install && cd ..

# Run everything
docker-compose up --build
# Frontend → http://localhost:3001
# API      → http://localhost:8100
# API Docs → http://localhost:8100/docs
# Docs     → http://localhost:2012
```

## Commands

### Backend

```bash
cd backend
uv run fastapi dev                          # hot reload
PYTHONPATH=. uv run pytest                  # all tests
PYTHONPATH=. uv run pytest tests/parts/     # single domain
PYTHONPATH=. uv run ruff check . --fix
PYTHONPATH=. uv run ruff format .
PYTHONPATH=. uv run pyright .
uv run alembic revision --autogenerate -m "msg"
uv run alembic upgrade head
```

### Frontend

```bash
cd frontend
npm run dev
npx tsc --noEmit
```

### Pre-commit (from repo root)

```bash
# List only the files you changed — do NOT use --all-files (OOM risk):
pre-commit run prettier --files frontend/app/page.tsx
pre-commit run markdownlint --files AGENTS.md
```

Ruff and Pyright are **not** pre-commit hooks — run them directly via
`uv run` from `backend/`.

## Structure

```text
backend/app/           # FastAPI app (see Domains below)
frontend/app/          # Next.js App Router (Spanish UI v1)
frontend/components/   # {feature}/index.tsx + actions.ts pattern
frontend/lib/          # apiClient + per-domain *.api.ts
docs/                  # MkDocs Material — full design docs (see below)
helm/                  # Kubernetes manifests (added later)
```

### Backend Domains (target layout per `docs/architecture/backend.md`)

```text
backend/app/
├── auth/                  # JWT issuance, login, password
├── users/                 # Profile + role management (admin)
├── organizations/         # Orgs + OrganizationMembership
├── parts/                 # Catalog of printable designs
├── collection_centers/    # Drop-off locations + per-center contributors
├── requests/              # Request (campaign) + RequestItem (line item)
├── contributions/         # Maker contribution lifecycle
├── ownership_transfers/   # Polymorphic transfer state machine
├── audit_log/             # Append-only audit trail
├── discovery/             # Aggregate read-only views
├── scheduled/             # APScheduler background jobs
├── permissions.py         # Polymorphic owner / member helpers
└── main.py                # FastAPI app factory
```

Every domain follows the seven-file pattern (router · schemas · models
· service · dependencies · exceptions · constants). Tests mirror the
domain layout under `backend/tests/`.

## Key Constraints

- **PYTHONPATH=.** required for all backend pytest/ruff/pyright
  invocations.
- **Soft deletes only** — set `active = False`; never `db.delete()`.
- **No CASCADE from `users`** — deactivating a user must preserve
  historical attribution (FR-013).
- **No `HTTPException` in services** — raise domain exceptions
  inheriting `AppExceptionError`; global handler converts to the
  standard `{success, error}` JSON envelope.
- **80-char prose limit** on `.md` files outside `docs/` (markdownlint
  MD013). Code blocks and table rows are exempt.
- **English-only docs and code identifiers.** Every `.md` file outside
  the i18n translation layer and every code identifier (entity class
  names, table names, FK columns, enum values, domain folder names,
  URL path segments) use English. The Spanish phrase **"centros de
  acopio"** is canonically rendered as **"Collection Center"** —
  entity `CollectionCenter`, table `collection_centers`, FK
  `collection_center_id`, folder `app/collection_centers/`, URL
  `/api/v1/collection-centers/`. Spanish copy lives only in
  user-facing UI strings under `frontend/`.
- **MkDocs file-mount quirk (WSL2)**: edits to `mkdocs.yml` need
  `docker compose up -d --force-recreate docs` to take effect (file
  bind-mounts cache the inode). `.md` file edits hot-reload normally.

## Key Business Rules

### Polymorphic Ownership

`Parts`, `CollectionCenter`s, and `Request`s each carry **two nullable
owner FKs** — `owner_user_id` + `owner_organization_id` (for Parts /
Centers) or `requester_user_id` + `requester_organization_id` (for
Requests) — with a database `CHECK` constraint enforcing exactly one
non-null. Service code never branches on which FK is set; all
authorization flows through `app/permissions.py` helpers
(`effective_owner_user_ids`, `effective_cc_member_user_ids`). See
`docs/requirements.md` §3.10 and `docs/architecture/database-schema.md`.

### Membership Models

- **OrganizationMembership**: `role` is `owner` or `member`. Exactly
  one active owner per org (partial unique index).
- **CollectionCenterMembership**: `role` is only `contributor`. The
  owner is **on the Center entity**, not in this table.
- "Effective members" of a Center = per-center contributors + the
  user-owner (if user-owned) + all members of the owning Org (if
  org-owned). Codified in `effective_cc_member_user_ids`.

### Request → RequestItem → Part

A Request is a campaign-level container ("Ferulas for Venezuela").
Each Request contains one or more **RequestItems**, each tied to a
single Part with its own target quantity, status, and (optional)
deadline. **Contributions reference `request_item_id`**, not
`request_id`. A Request must always have at least one item (FR-119).

### Contribution Lifecycle

`claimed → printed → delivered → received | released`. Key rules:

- Only the maker can advance `claimed → printed → delivered`.
- Only effective members of the target Centro (or maintainer/admin)
  can confirm `received` (FR-056).
- **FR-126 auto-receive**: when the maker is also an effective member
  of the target Centro, `delivered` auto-advances to `received` in
  the same transaction (`auto_received = true`).
- Stale `claimed` contributions auto-expire after 14 days (FR-055,
  APScheduler).

### Ownership Transfer Flow

Polymorphic accept/decline flow over Parts, Collection Centers, **and**
Requests (FR-118). One row per asset can be `pending` at a time
(partial unique index). 7-day default TTL on pending transfers
(FR-114, APScheduler). Maintainers/admins can force-transfer to
recover orphaned assets (FR-116).

### Verification Gates

- Newly registered Centers and Organizations default to
  `verified = false` and are hidden from public lists until a
  maintainer/admin verifies them (FR-027, FR-096).
- Unverified Orgs **may** own assets (FR-105) but a "Unverified
  organization" badge must appear on public-facing views.
- Centers must be `verified` and `active` to be selectable as a
  Contribution drop-off target (FR-064).

### Authorization Layering

`NFR-006`: every protected endpoint must enforce role + ownership
**server-side**. Frontend hiding of controls is for UX only. Use
`has_global_override(user)` for the "maintainer/admin can do anything"
check.

### Self-Registration Is Disabled in v1

Per the roadmap, `POST /auth/register` (FR-001) ships **disabled**.
Admins provision accounts manually via `POST /users`. Self-register
is unlocked in Phase 6 alongside Google OAuth (IR-001).

## Validation Checklist

```bash
cd backend
PYTHONPATH=. uv run ruff check . --fix
PYTHONPATH=. uv run ruff format .
PYTHONPATH=. uv run pyright .
PYTHONPATH=. uv run pytest
cd ../frontend && npx tsc --noEmit
pre-commit run --files <changed files>
```

## Default Admin

`admin` / `printforhelp-admin` (configurable via
`DEFAULT_ADMIN_USERNAME` / `DEFAULT_ADMIN_PASSWORD` env vars on
deploy).

## Documentation

All design docs live under `docs/` and are served by the `docs`
container at <http://localhost:2012>.

| Doc | Purpose |
|---|---|
| [`docs/index.md`](docs/index.md) | Project intro |
| [`docs/roadmap.md`](docs/roadmap.md) | Phased plan with v1 scope (Phases 1–3 = MVP) |
| [`docs/requirements.md`](docs/requirements.md) | Full SRS — 125 FRs · 17 NFRs · 3 IRs |
| [`docs/architecture/backend.md`](docs/architecture/backend.md) | FastAPI architecture, domain pattern, polymorphic auth helpers, background jobs |
| [`docs/architecture/database-schema.md`](docs/architecture/database-schema.md) | PostgreSQL schema, polymorphic ownership pattern, sample queries |
| [`docs/architecture/api-specification.md`](docs/architecture/api-specification.md) | REST surface — all endpoints, payloads, error codes, end-to-end examples |

**When in doubt, read the requirements doc first.** Every FR is
numbered (`FR-NNN`) and referenced throughout the architecture and
API docs.

## Project Status

Currently entering **Phase 2** per
[`docs/roadmap.md`](docs/roadmap.md):

- ✅ Phase 0 — scaffold, full design docs, schema design
- ✅ Phase 1 — auth (JWT/Argon2ID), admin-provisioned users, login UI,
  and the `/admin/users` management tab (create/role/password/activate)
- 📅 Phase 2 — Orgs + Collection Centers backend (incl. public read)
- 📅 Phase 3 — Public Collection Centers tab on the frontend
  (the headline v1 deliverable for the Venezuela community)
- 🔮 Phases 4–6 — Parts/Requests/Contributions, ownership transfers,
  polish (bilingual UI, OAuth, notifications, self-registration)

V1 is **Spanish-only UI** and **admin-provisioned accounts only** —
both are deliberate deviations from the SRS captured in the roadmap's
"Guiding Constraints" section.
