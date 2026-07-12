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
PYTHONPATH=. uv run pytest tests/resources/     # single domain
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
├── resources/             # Catalog of aid items (3D prints; generic-ready)
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

`Resources`, `CollectionCenter`s, and `Request`s each carry **two nullable
owner FKs** — `owner_user_id` + `owner_organization_id` (for Resources /
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

### Request → RequestItem → Resource

A Request is a campaign-level container ("Ferulas for Venezuela").
Each Request contains one or more **RequestItems**, each tied to a
single Resource with its own target quantity, status, and (optional)
deadline. **Contributions reference `request_item_id`**, not
`request_id`. A Request must always have at least one item (FR-119).
The **same Resource may appear on multiple items** of one Request (a
recurring need); each item tracks progress independently. Every item
carries a stable, per-Request **`item_number`** (1, 2, ...; unique per
Request, never reused) so duplicates are distinguishable ("Name #2") and
each item gets a short, shareable public page
(`/requests/{id}/items/{item_number}`) with a commitments list, comments,
and an activity timeline (`request_item` entity type). The item's UUID
stays its true identity (Contributions, comments, and watches key on it);
the number is only for display, friendly URLs, and public reads. (v1
deviation from FR-120's "duplicates rejected" rule.)

### Generic Resource Catalog

The catalog entity is `Resource` (table `resources`; it was `Part` /
`parts` through Phase 4, renamed in migration `0010_resources_generic`).
A Resource carries a **`category`** (`resource_category` enum) so the
same Request/Contribution machinery can coordinate non-printed aid
(food, water, medicine, ...) with no schema migration. v1 surfaces two
kinds: **`category = print_3d`** ("Piezas" / Parts) and **`category =
other`** ("Insumos" / Supplies, the single generic supply type). Rules:

- `source_url` is nullable in the DB but **required for `print_3d`**
  (enforced in `resources/service.py`, raising `SOURCE_URL_REQUIRED`);
  optional for supplies.
- `units` is a list of suggested units of measure (e.g. `["litros",
  "cajas"]`; empty = countable pieces). A supply may accept several;
  each RequestItem records the one `unit` chosen for its quantity
  (seeded from the resource's suggestions but freely editable).
- The Parts UI never sends `category`, so its creates default to
  `print_3d`; the Supplies UI sends `category = other`. Parts and
  Supplies each scope their catalog reads by `category`. See
  `docs/architecture/database-schema.md` → "Generic Resource Catalog".

### Request Moderation (FR-134/FR-135)

A Request carries a **`moderation_status`** — `draft` → `pending` →
`approved` | `changes_requested` | `rejected` — in a column **separate
from** its lifecycle `status` (`open`/`fulfilled`/`closed`). Keep them
separate: `status` is guarded by the `request_closed_consistency` CHECK
and feeds the `HelpState` progress math; publication is an orthogonal
axis. Rules:

- Only `approved` is **public**. Every other state is readable solely by
  the campaign's effective requesters and maintainers/admins, enforced
  server-side by `requests.service.can_view_request` — the single source
  of truth. Unpublished campaigns **404** (never 403) on the detail, item,
  and commitment reads, vanish from the directory, expose no comments or
  activity, and reject new Contributions
  (`409 REQUEST_NOT_PUBLISHED`). A leaked link must stay worthless.
  **Any new read path that can surface a Request must go through that
  gate.**
- Maintainers/admins bypass the queue (their campaigns are born
  `approved`). Trusted-publisher bypass for regular users is a documented
  follow-up — use the capability-flag registry, not a new role.
- `changes_requested` and `rejected` can be edited and **resubmitted**;
  neither is terminal. Submitting needs ≥1 item.
- **Unpublish** (`POST /requests/{id}/unpublish`) pulls a live campaign
  back to `pending` — the takedown lever, open to maintainers/admins and
  to the campaign's own requesters.
- **UI copy never names the reviewer.** The author is told only that the
  campaign is waiting for approval.
- Tests: the `auto_publish_requests` autouse fixture in
  `tests/conftest.py` publishes campaigns created via the API so the other
  domains' suites are unaffected. Tests that exercise the gate carry
  `@pytest.mark.moderation` to opt out.

### Contribution Lifecycle

`claimed → prepared → delivered → received | released`. Key rules:

- The middle state was `printed` through Phase 4; it was generalized to
  `prepared` (migration `0011`, column `prepared_at`) so the lifecycle
  is item-neutral for the generic Resource catalog. The v1 UI still
  *displays* "printed" copy for 3D resources; only the state is neutral.
  The maker tab is **"My Contributions"** (`/my-contributions`, route +
  `Contribution` entity; ES "Mis aportes").
- Only the maker can advance `claimed → prepared → delivered`.
- **Quantity/notes/center are editable until `delivered`** (v1 widening of
  FR-057, which locked them at `claimed`): makers routinely find mid-print
  that they can manage more — or fewer — units than they first committed
  to. A quantity edit reconciles the Contribution's per-unit tracking QRs
  via `tracking.service.sync_units`; unit tokens are stable, so a label
  already printed for unit *n* survives a shrink-then-grow. Locked from
  `delivered` on (`CONTRIBUTION_LOCKED`).
- Only effective members of the target Centro (or maintainer/admin)
  can confirm `received` (FR-056).
- **FR-126 auto-receive**: when the maker is also an effective member
  of the target Centro, `delivered` auto-advances to `received` in
  the same transaction (`auto_received = true`).
- Stale `claimed` contributions auto-expire after 14 days (FR-055,
  APScheduler).

### Ownership Transfer Flow

Polymorphic accept/decline flow over Resources, Collection Centers, **and**
Requests (FR-118). One row per asset can be `pending` at a time
(partial unique index). 7-day default TTL on pending transfers
(FR-114, APScheduler). Maintainers/admins can force-transfer to
recover orphaned assets (FR-116).

### Verification Gates

- Newly registered Centers and Organizations default to
  `verified = false`. **Deliberate v1 deviation from FR-027**:
  unverified *Centers* are **shown publicly** (list + detail) with a
  "No verificado" badge so the community can find drop-offs sooner; the
  `verified` flag drives the badge, not visibility. Likewise,
  operationally inactive (`status = inactive`) Centers are **shown
  publicly** with a "No recibe donaciones" badge and a directory filter
  to narrow to centers still receiving donations; `status` drives the
  badge, not visibility. Effective members and maintainers/admins flip
  it via `/toggle-status` (FR-078). Only archived (`active = false`)
  Centers stay private to effective members and maintainers/admins.
- Organizations are **still hidden** from public lists until verified
  (FR-096); the `/organizations` public read only returns verified orgs.
- **Open center submission (v1 deviation):** `POST /collection-centers`
  requires **no auth** so guests — and third-party apps — can register
  drop-offs, and reads (`GET`) never require a token. Guest submissions
  are owned by a system **`anonymous`** user (bootstrapped at startup,
  unguessable password, never logs in); see
  `users.service.get_or_create_anonymous_user`. Authenticated callers
  still own their submissions. All new centers start unverified and are
  moderated by maintainers. (Abuse mitigation — rate limiting / captcha
  — is a recommended follow-up before scale.)
- Unverified Orgs **may** own assets (FR-105) but a "Unverified
  organization" badge must appear on public-facing views.
- Centers must be `verified` and `active` to be selectable as a
  Contribution drop-off target (FR-064) — that gate is unchanged; only
  public *visibility* was relaxed.

### Authorization Layering

`NFR-006`: every protected endpoint must enforce role + ownership
**server-side**. Frontend hiding of controls is for UX only. Use
`has_global_override(user)` for the "maintainer/admin can do anything"
check.

### User Flags (generic traits + capabilities)

Users carry generic yes/no flags in the `user_flags` table
(`(user_id, key, value, source, set_by_id)`, one row per pair; **absent
row = unknown**, giving a tri-state). The registry `app/users/flags.py`
is the source of truth for known keys and their **trust boundary**:

- **Traits** (`self_assignable=True`) are self-declared personalization
  and **must never authorize** anything. `maker` is the first — it only
  drives the "Hola, Maker" header greeting; a one-time login modal asks
  when it is unknown.
- **Capabilities** (`self_assignable=False`) are admin/maintainer-granted
  and gate access; check them with `permissions.has_capability(db, user,
  key)` (admin override OR an active granted flag). `can_add_part` /
  `_center` / `_request` exist as scaffolding but are **not yet enforced**
  on any endpoint (follow-up).

APIs: `GET /auth/me` returns the user's `flags` map; `PUT
/users/me/flags/{key}` (self, self-assignable only) and `PUT
/users/{id}/flags/{key}` (admin, any key). Adding a new flag is one
registry entry — no migration.

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

Currently in **Phase 4** per [`docs/roadmap.md`](docs/roadmap.md):

- ✅ Phase 0 — scaffold, full design docs, schema design
- ✅ Phase 1 — auth (JWT/Argon2ID), admin-provisioned users, login UI,
  and the `/admin/users` management tab (create/role/password/activate)
- ✅ Phase 2 — Orgs + Collection Centers backend: full CRUD,
  verification, membership/contributor management, polymorphic
  ownership helpers, and public read (incl. country/city filters)
- ✅ Phase 3 — Public Collection Centers tab on the frontend
  (directory, detail, shipments, comments/activity)
- ✅ Phase 4 — Resources catalog, Requests + RequestItems, and the
  Contribution lifecycle (claim → prepared → delivered → received →
  released), with per-item progress aggregation (FR-062/063),
  FR-126 auto-receive, and the FR-055 stale-claim expiry job. Frontend
  adds the Resources, Requests (list/detail/create), and My Contributions tabs.
- 🔮 Phases 5–6 — ownership transfers, polish (OAuth, notifications,
  self-registration, discovery/dashboard ranking)

**Phase 4 v1 deviations:** the `parts` table was generalized into
`resources` (migration `0010_resources_generic`) with a `category`
enum + `unit` and a nullable `source_url`, so the catalog can hold
non-printed aid later with no migration (v1 stays `print_3d`-only — see
"Generic Resource Catalog"). `Resource` also gains an `image_url` column
(not in the original schema); per-item progress uses **center-level
buckets** (`claimed` = claimed+prepared, `at center` = delivered+received)
— the
contribution↔shipment "shipped out" bucket is a documented follow-up.

V1 is **Spanish-only UI** and **admin-provisioned accounts only** —
both are deliberate deviations from the SRS captured in the roadmap's
"Guiding Constraints" section.
