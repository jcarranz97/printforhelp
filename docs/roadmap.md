# Project Roadmap

This roadmap outlines the planned development phases for PrintForHelp.
The ordering reflects the **immediate community need** in Venezuela:
make the directory of Collection Centers discoverable to the public as
fast as possible — people are asking for this every day — so the
platform delivers value to **non-registered visitors** before the
maker-coordination features are built out.

For the full feature surface this roadmap eventually delivers, see
[`requirements.md`](requirements.md). For the schema it builds against,
see [`architecture/database-schema.md`](architecture/database-schema.md).

## Guiding Constraints

- **Account creation is admin-provisioned in v1.** No public
  self-registration on the landing page until the platform is stable
  and the community is ready for open signup. `POST /auth/register`
  (FR-001) ships **disabled**; admins create accounts by hand through
  `POST /users` for trusted contributors.
- **Public read first.** Verified Collection Centers and verified
  Organizations must be visible to guests with no login required.
  That is the headline immediate value (FR-072).
- **Spanish-first UI.** Bilingual ES/EN (NFR-015) lands once the core
  flows work. The v1 UI is Spanish-only; English follows in a later
  phase.

## Phase 0: Project Foundation ✅

- [x] Monorepo scaffold (FastAPI + Next.js + Postgres + MkDocs)
- [x] Docker Compose dev environment
- [x] Initial landing page (Spanish)
- [x] Requirements specification ([requirements.md](requirements.md))
- [x] Database schema design
      ([architecture/database-schema.md](architecture/database-schema.md))
- [x] Backend architecture documentation
      ([architecture/backend.md](architecture/backend.md))
- [x] API specification draft
      ([architecture/api-specification.md](architecture/api-specification.md))

## Phase 1: Authentication & Admin-Provisioned Users ✅

Goal: an admin can log in and create accounts for trusted contributors.
Self-registration stays disabled.

### Backend

- [x] Alembic initialization + first migration (`users`, `audit_log`)
- [x] Bootstrap default admin from `DEFAULT_ADMIN_USERNAME` /
      `DEFAULT_ADMIN_PASSWORD` env vars (FR-007)
- [x] `POST /auth/login` — JWT issuance with Argon2ID password hashing
- [x] `GET /auth/me` + `PUT /auth/me/password`
- [x] Admin-only: `POST /users` to create an account
- [x] Admin-only: `GET /users`, `PUT /users/{id}/role`,
      `POST /users/{id}/deactivate` (+ `reactivate`)
- [x] Admin-only: `PUT /users/{id}/password` — reset any account's
      password (no current-password required; policy still enforced)
- [x] Last-admin lockout-protection guard (FR-014)
- [x] CI: Pyright + Ruff + pytest pipeline green

Password policy (FR-002): minimum 8 characters with at least one letter
and one digit. Sessions are 7-day JWTs (no refresh-token flow in v1).
For local development, the backend auto-runs `alembic upgrade head` on
startup and seeds two extra accounts (`maintainer1`, `user1`) when
`SEED_DEV_DATA=true` (set in `docker-compose.yml`).

### Frontend

- [x] `/login` page wired to `POST /auth/login`
- [x] JWT stored in httpOnly cookie
- [x] Logged-in header state on the landing page (username + logout)
- [x] `/logout` clears the cookie and redirects to the landing page
- [x] Auth middleware (`proxy.ts`): protect any future `/admin/*` paths
- [x] `/admin/users` — admin-only management tab: create accounts,
      change roles, reset passwords, and activate/deactivate users

## Phase 2: Organizations & Collection Centers — Backend ✅

Goal: ship the data model and APIs that back the public directory.
After this phase, an admin-provisioned user can register their
organization and one or more drop-off centers, and a guest can read
them from the API.

### Migrations & shared layer

- [x] Migration for `organizations`, `organization_memberships`,
      `collection_centers`, `collection_center_memberships`
- [x] `app/permissions.py` with `effective_owner_user_ids`,
      `effective_cc_member_user_ids`, `has_global_override`,
      `assert_caller_can_own_on_behalf_of`
- [x] `app/audit_log/service.write_audit()` infrastructure

### Organizations

- [x] CRUD: create / list / get / edit / archive
- [x] Maintainer/admin verification:
      `POST /organizations/{id}/verify` and `revoke-verification`
- [x] Membership: add / remove / leave; ownership transfer within org
- [x] Public read: verified orgs visible without auth (FR-105)

### Collection Centers

- [x] CRUD: create / list / get / edit / archive
      (owner-archive guard + maintainer force-archive)
- [x] Maintainer/admin verification:
      `POST /collection-centers/{id}/verify` and `revoke-verification`
- [x] Per-center contributors: add / remove / leave
- [x] `POST /collection-centers/{id}/toggle-status` for members
- [x] Public read: verified active centers visible without auth
      (FR-072), filterable by country and city

## Phase 3: Public Collection Centers Tab — Frontend 🚧

Goal: a guest opens the page and immediately finds the Collection
Centers near them, with full contact info — no login required.

- [x] `/centers` tab — public list with country/city filters
- [x] `/centers/{id}` detail — address, hours, contact, owning
      organization (with Unverified badge when applicable, FR-105)
- [ ] `/organizations` tab — public list of verified orgs
- [ ] `/organizations/{id}` detail — owned centers + contact info
- [ ] Logged-in flows (member-side):
  - [x] Create a Collection Center (self-owned at `/centers/new`;
        on-behalf-of-Org pending a "my organizations" endpoint)
  - [ ] Edit Center details / toggle `active`
  - [ ] Add / remove per-center contributors
- [ ] Logged-in flows (maintainer/admin side):
  - [x] Verify or revoke verification on a Center (review queue +
        per-center action on `/centers`; Org verification lands with
        the `/organizations` tab)
  - [x] Create user accounts (admin user-management UI shipped in
        Phase 1 at `/admin/users`)

## Phase 4: Parts, Requests, Contributions 🔮

Goal: the full maker-coordination loop. Builds on the Phase 2/3
foundation.

### Backend

- [ ] Migration for `parts`, `requests`, `request_items`,
      `contributions`
- [ ] Parts catalog CRUD + `featured` + discontinue/archive
      (owner) + force-archive (maintainer, FR-077)
- [ ] Requests with items (FR-119 – FR-124): create, add/remove items,
      close
- [ ] Contributions lifecycle endpoints
      (`mark-printed`, `mark-delivered`, `confirm-received`, `release`)
- [ ] FR-126 auto-receive when the maker is an effective CC member
- [ ] FR-055 auto-expire stale `claimed` Contributions via
      APScheduler
- [ ] Discovery: `GET /discovery/next`, `/dashboard`,
      `/parts/{id}/chart`

### Frontend

- [ ] Parts tab (public read; create for logged-in users)
- [ ] Requests tab — public read; create for logged-in users
- [ ] Request detail page with item-level progress breakdown
- [ ] My Prints tab (authenticated only)
- [ ] "What to print next" dashboard (FR-065)

## Phase 5: Ownership Transfers 🔮

Goal: enable the "creator joins later" handoff that the polymorphic
ownership model was designed for.

- [ ] Migration for `ownership_transfers`
- [ ] `POST /{parts|collection-centers|requests}/{id}/transfers`
- [ ] `POST /transfers/{id}/accept | decline | cancel`
- [ ] FR-114 auto-expire pending transfers via APScheduler
- [ ] Maintainer/admin force-transfer endpoints (FR-116)
- [ ] Frontend: incoming/outgoing transfers view + accept/decline UI

## Phase 6: Polish & Integrations 💫

- [ ] Open up public self-registration (`POST /auth/register`, FR-001)
- [x] Bilingual ES/EN UI (NFR-015): locale toggle in the navigation,
      full string extraction into the i18n layer **(pulled forward into
      Phase 3 — header ES/EN toggle + `frontend/i18n` dictionaries)**
- [ ] Google OAuth (IR-001) — eventual primary signup path
- [ ] Email notifications (IR-002, IR-003)
- [ ] Per-center "accepted Parts" filter (FR-093)
- [ ] Audit log viewer UI (maintainer/admin only)
- [ ] Personal Access Tokens UI
- [ ] Helm chart + production deployment + scheduled-job worker pod
- [ ] Performance pass (Redis cache layer for `/discovery/next` if
      load demands it)
- [ ] Security audit before opening self-registration

---

**Legend:**

- ✅ Completed
- 🚧 In Progress
- 📅 Planned
- 🔮 Future Consideration
- 💫 Polish Phase
