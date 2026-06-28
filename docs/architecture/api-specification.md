# PrintForHelp API Specification

!!! warning "**DOCUMENTATION STATUS**"
    This document defines the REST surface during **initial design and
    planning**. Once the FastAPI implementation begins, the canonical
    reference is the auto-generated OpenAPI / Swagger docs:

    - **Development**: `http://localhost:8100/docs` (Swagger UI)
    - **Development**: `http://localhost:8100/redoc` (ReDoc)

    The purpose of this document is to define endpoints, payloads, and
    error codes against the requirements in
    [`../requirements.md`](../requirements.md) and the schema in
    [`database-schema.md`](database-schema.md), and to drive the
    initial backend implementation.

## API Overview

- **Base URL** (dev): `http://localhost:8100/api/v1`
- **Authentication**: Bearer token (JWT) or Personal Access Token
  (prefix `pforh_pat_…`)
- **Content-Type**: `application/json`
- **API Version**: v1

## Authentication

All endpoints require authentication except:

- `POST /auth/register`
- `POST /auth/login`
- `GET /health`
- Public read endpoints on Parts (`GET /parts`, `GET /parts/{id}`)
- Public read endpoints on Requests (`GET /requests`,
  `GET /requests/{id}`, `GET /requests/{id}/items`)
- Public read endpoints on verified Collection Centers and
  Organizations
- Public read endpoints on Shipments
  (`GET /collection-centers/{id}/shipments`)
- Public read endpoints on Comments and Activity (`GET /comments`,
  `GET /activity`)

```http
Authorization: Bearer <jwt_or_pat>
```

## Response Format

### Success

Data is returned directly without a wrapper. List endpoints either
return arrays or `{ items, pagination }` for paginated lists.

### Errors

Consistent envelope (matches Colony's contract):

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message.",
    "details": { }
  }
}
```

## Polymorphic Owner Field Convention

Several create/update payloads accept a polymorphic owner. The
convention across the API:

- Send **either** `owner_user_id` **or** `owner_organization_id`,
  never both.
- On creation, both may be omitted — the server defaults to "caller
  owns the asset personally."
- The caller must be an active member of the Organization they pass
  in `owner_organization_id`, else `403 ORG_MEMBERSHIP_REQUIRED`.

Requests use the same convention with the field names
`requester_user_id` / `requester_organization_id`.

---

## API Endpoints

### 1. Authentication & Users

#### POST /auth/register

Self-register. **Public.**

**Request Body:**

```json
{
  "username": "alice",
  "password": "securePassword123",
  "preferred_locale": "es"
}
```

**Response:** `201 Created`

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "username": "alice",
  "role": "user",
  "preferred_locale": "es",
  "active": true,
  "created_at": "2026-06-27T00:00:00Z",
  "updated_at": "2026-06-27T00:00:00Z"
}
```

**Errors:** `409 USERNAME_TAKEN`, `400 WEAK_PASSWORD`

#### POST /auth/login

Exchange username/password for a JWT.

**Request Body (Form Data):**

```
username=alice
password=securePassword123
```

**Response:** `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs…",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors:** `401 INVALID_CREDENTIALS`, `403 INACTIVE_USER`

#### GET /auth/me

Current user info.

**Response:** `200 OK` — same shape as the register response.

#### PUT /auth/me

Update own profile (currently just `preferred_locale`).

**Request Body:**

```json
{ "preferred_locale": "en" }
```

#### PUT /auth/me/password

```json
{
  "current_password": "oldPassword123",
  "new_password": "newSecurePassword456"
}
```

**Response:** `200 OK` — `{ "message": "Password updated." }`
**Errors:** `400 INCORRECT_PASSWORD`, `400 WEAK_PASSWORD`

#### DELETE /auth/me

Self-deactivate (soft delete). **FR-008.**

**Response:** `204 No Content`

#### Admin user-management

| Method | Path | Description |
|---|---|---|
| `GET`    | `/users`             | List all users. **Admin.** |
| `POST`   | `/users`             | Create an account: `{ "username", "password", "role"?, "preferred_locale"? }`. **Admin.** (FR-007 / Phase 1) |
| `GET`    | `/users/{user_id}`   | Get a user. **Admin.** |
| `PUT`    | `/users/{user_id}/role` | `{ "role": "maintainer" }`. **Admin.** Rejected if would demote the last active admin (FR-014). |
| `PUT`    | `/users/{user_id}/password` | `{ "new_password": "..." }`. **Admin.** Resets any account's password; no current password required, password policy still enforced (FR-002). |
| `POST`   | `/users/{user_id}/deactivate` | **Admin.** Same lockout guard. |
| `POST`   | `/users/{user_id}/reactivate` | **Admin.** |

---

### 2. Organizations

#### POST /organizations

Create an Organization. **Any authenticated user.** Creator
auto-receives the `owner` membership (FR-095).

**Request Body:**

```json
{
  "name": "UCAB Lab 3D",
  "description": "Lab oficial de impresión 3D en UCAB Caracas.",
  "contact": "fablab@ucab.edu.ve",
  "website": "https://lab.ucab.edu.ve",
  "country": "VE"
}
```

**Response:** `201 Created`

```json
{
  "id": "cccc1111-e89b-12d3-a456-426614174000",
  "name": "UCAB Lab 3D",
  "description": "Lab oficial de impresión 3D en UCAB Caracas.",
  "contact": "fablab@ucab.edu.ve",
  "website": "https://lab.ucab.edu.ve",
  "country": "VE",
  "verified": false,
  "registered_by_id": "<user uuid>",
  "verified_by_id": null,
  "status": "active",
  "active": true,
  "created_at": "2026-06-27T00:00:00Z",
  "updated_at": "2026-06-27T00:00:00Z"
}
```

**Errors:** `409 ORG_NAME_TAKEN`

#### GET /organizations

List verified Organizations. **Public.** Unverified Orgs are visible
only to their own members and to maintainers/admins.

Query params: `verified` (bool), `country` (string), `q` (text search
on name and description).

#### GET /organizations/{id}

Full Organization detail. Public users see only public attributes
plus public-asset counts (FR-106). Members get the member list and
owned-asset lists.

#### PUT /organizations/{id}

Edit. **Owner / maintainer / admin.**

#### POST /organizations/{id}/verify

Flip `verified=true`. **Maintainer / admin.** Records
`verify_organization` in the audit log.

#### POST /organizations/{id}/revoke-verification

**Maintainer / admin.** `{ "reason": "..." }`.

#### POST /organizations/{id}/archive

**Owner / maintainer / admin.** Rejected with `409` if the Org owns
any active Parts or Collection Centers (FR-104).

##### Membership

| Method | Path | Description |
|---|---|---|
| `GET`    | `/organizations/{id}/members` | List members. **Members + mod/admin.** |
| `POST`   | `/organizations/{id}/members` | `{ "username": "bob" }`. Immediate, no accept (FR-098). **Owner.** |
| `DELETE` | `/organizations/{id}/members/{user_id}` | Remove a member. **Owner** removing others; **member** removing self. Owners can't self-remove (FR-100). |
| `POST`   | `/organizations/{id}/transfer-ownership` | `{ "target_user_id": "..." }`. Atomic owner-swap to an existing member (FR-101). **Owner.** |
| `POST`   | `/organizations/{id}/force-transfer-ownership` | **Maintainer / admin** rescue for orphaned orgs (FR-102). |

---

### 3. Parts

#### POST /parts

Register a Part. **Authenticated.** Owner defaults to caller.

**Request Body:**

```json
{
  "name": "Forearm splint v3",
  "description": "Adjustable forearm splint, 200 mm length.",
  "source_url": "https://www.thingiverse.com/thing:9999",
  "image_url": "https://example.com/splint.png",
  "tags": ["splint", "forearm", "venezuela2026"],
  "owner_organization_id": "cccc1111-e89b-12d3-a456-426614174000"
}
```

> **Phase 4 v1:** `image_url` (optional preview image) is accepted;
> `suggested_settings` and `POST /parts/{id}/feature` are deferred
> (not yet implemented). Each `RequestItem` in a request-detail response
> carries a `progress` object with center-level buckets:
> `target_quantity`, `claimed_quantity` (claimed+printed),
> `at_center_quantity` (delivered+received), `committed_quantity`, and
> `remaining`.

**Response:** `201 Created` — full `PartResponse`.

**Errors:** `403 ORG_MEMBERSHIP_REQUIRED`, `400 VALIDATION_ERROR`

#### GET /parts

Public catalog. Query params: `tag`, `status`, `featured`, `q`
(free-text search on name + description), `page`, `per_page`.

Each item carries an `open_requests_count` (FR-022) so the catalog
list reflects demand.

#### GET /parts/{id}

Public. Adds `open_requests` — a list of open `RequestItem`s that
reference the Part (FR-023):

```json
{
  "id": "...",
  "name": "Forearm splint v3",
  "...": "...",
  "open_requests": [
    {
      "request_id": "...",
      "request_item_id": "...",
      "request_title": "Ferulas for Venezuela",
      "quantity": 8,
      "remaining": 5,
      "deadline": "2026-08-15"
    }
  ]
}
```

#### PUT /parts/{id}

Edit. **Effective owner** (FR-017) **or maintainer/admin** (FR-018).

#### POST /parts/{id}/discontinue

**Effective owner.** Sets `status=discontinued` (FR-075). Idempotent
on a Part already discontinued.

#### POST /parts/{id}/reactivate

Reverse of discontinue. **Effective owner / maintainer / admin.**

#### POST /parts/{id}/feature

Flip `featured=true`. **Maintainer / admin** only (FR-019).

#### POST /parts/{id}/archive

Owner-side archive (FR-076). **Effective owner.** Rejected with
`409 PART_ARCHIVE_BLOCKED` if any open Requests reference the Part.
The error response details include `open_request_count`.

#### POST /parts/{id}/force-archive

**Maintainer / admin** (FR-077). Cascades: every open RequestItem
referencing the Part is auto-closed with reason `part_archived`.

---

### 4. Collection Centers

#### POST /collection-centers

**Open — no auth required (v1).** Authenticated callers own the center
themselves (or, via `owner_organization_id`, an org they belong to).
Guests submit anonymously and the center is owned by the system
`anonymous` account; any `owner_organization_id` they send is ignored.
Either way it starts `verified=false` and is moderated by maintainers.

**Request Body:**

```json
{
  "name": "UCAB Lab — Caracas",
  "address": "Av. Teherán, Montalbán, Caracas",
  "country": "VE",
  "city": "Caracas",
  "contact": "+58-212-407-4400 / fablab@ucab.edu.ve",
  "location_url": "https://maps.google.com/?q=UCAB+Caracas",
  "opening_hours": "Lun-Vie 9-17",
  "description": "Entrega por puerta principal del edificio Mendoza.",
  "owner_organization_id": "cccc1111-…"
}
```

**Response:** `201 Created` — full `CollectionCenterResponse`.

> **Markdown `description`.** Collection Centers, Parts, and Requests
> each expose a Markdown `description` rendered in the UI and editable by
> the asset's effective owner/requester (or a maintainer/admin) via the
> respective `PUT` endpoint. For Collection Centers this field was
> renamed from `notes` (migration `0007_cc_description`).

#### GET /collection-centers

**Open — no auth required.** Lists every `status=active` center,
verified or not, so guests and third-party apps can pull the directory
(each row carries a `verified` flag for a "No verificado" badge). Query
params: `country`, `city`, and `verified` (a `true`/`false` filter
available to **everyone** — e.g. third-party apps pulling only verified
centers, or a maintainer's `verified=false` queue). Maintainers/admins
additionally see operationally-inactive (`status=inactive`) centers.

#### GET /collection-centers/{id}

Public for verified active centers. Members and mods see pending ones
too. The response adds a `pending_deliveries` count (FR-035).

#### PUT /collection-centers/{id}

**Effective member** (any contributor or org member, FR-031) or
**mod/admin**.

#### POST /collection-centers/{id}/verify

**Maintainer / admin.** Records `verify_collection_center`.

#### POST /collection-centers/{id}/revoke-verification

**Maintainer / admin.** `{ "reason": "..." }`.

#### POST /collection-centers/{id}/toggle-status

`{ "status": "inactive" }`. **Effective member** (FR-078).

#### POST /collection-centers/{id}/archive

**Effective owner.** Rejected `409` if any open Contributions are
routed to it (FR-079).

#### POST /collection-centers/{id}/force-archive

**Maintainer / admin** (FR-080). Auto-releases routed Contributions.

##### Per-center membership

| Method | Path | Description |
|---|---|---|
| `GET`    | `/collection-centers/{id}/contributors` | List per-center contributors. **Effective members + mod/admin.** |
| `POST`   | `/collection-centers/{id}/contributors` | `{ "username": "bob" }`. **Effective owner** (FR-084). |
| `DELETE` | `/collection-centers/{id}/contributors/{user_id}` | Effective owner removes; contributor self-removes. |

##### Shipments (FR-127 – FR-130)

A Shipment is a planned dispatch of aid from the center. Reads are
**public**; writes require **auth** and an **effective member** of the
center (owner / contributor / owning-org member) or **mod/admin**.

| Method | Path | Description |
|---|---|---|
| `GET`    | `/collection-centers/{id}/shipments` | List the center's shipments, soonest date first. **Public — always visible.** |
| `GET`    | `/collection-centers/{id}/shipments/{shipment_id}` | Get one shipment (powers its detail page). **Public.** `404` if missing. |
| `POST`   | `/collection-centers/{id}/shipments` | Create a shipment. **Effective member / mod/admin.** |
| `PATCH`  | `/collection-centers/{id}/shipments/{shipment_id}` | Edit fields and/or change `status`. **Effective member / mod/admin.** |
| `DELETE` | `/collection-centers/{id}/shipments/{shipment_id}` | Soft-delete a shipment. **Effective member / mod/admin.** |

**Create / PATCH body** (all fields optional on PATCH):

```json
{
  "shipment_date": "2026-07-15",
  "status": "receiving",
  "destination": "Caracas, Venezuela",
  "description": "El camión sale a las 8am."
}
```

`status` ∈ `receiving` (default) · `closed` · `cancelled`.
**Response:** full `ShipmentResponse` (`201` on create, `200` on PATCH,
`204` on delete).

---

### 5. Comments & Activity

A polymorphic, public timeline for any commentable entity. v1 entity
types: `collection_center`, `shipment` (FR-131 – FR-133).

#### GET /comments

**Public.** Query params `entity_type` + `entity_id` (both required),
optional `before` (ISO cursor) and `limit` (≤ 200). Newest first.

#### POST /comments

**Authenticated (any logged-in user).** Body supports **Markdown**.

```json
{
  "entity_type": "shipment",
  "entity_id": "ssss2222-…",
  "body": "¡Enviadas 12 férulas hoy! 🎉"
}
```

`404 INVALID_ENTITY_REFERENCE` if the target does not exist; `422` if
the body is blank. **Response:** `201` `CommentResponse`.

#### PATCH /comments/{id}

Edit a comment body. **Author only** (`403 COMMENT_NOT_AUTHOR`). Sets
`edited_at`.

#### DELETE /comments/{id}

Soft-delete. **Author or mod/admin** (`403 COMMENT_DELETE_FORBIDDEN`).
`204`.

#### GET /activity

**Public.** Same query params as `GET /comments`. Returns the
append-only event feed (`created`, `updated`, `status_changed`,
`deleted`, `commented`, `comment_edited`, `comment_deleted`); each row
carries an `actor` summary and a `changes` object, e.g.
`{"status": {"from": "receiving", "to": "closed"}}`.

---

### 6. Requests & Request Items

#### POST /requests

Create a Request. **Authenticated.** Must include at least one item
(FR-119).

**Request Body:**

```json
{
  "title": "Ferulas for Venezuela",
  "description": "Campaña de férulas para el terremoto de junio 2026.",
  "deadline": "2026-08-15",
  "preferred_collection_center_ids": ["<cc-uuid-caracas>", "<cc-uuid-mexico>"],
  "requester_organization_id": "cccc1111-…",
  "items": [
    {
      "part_id": "<part-uuid-forearm>",
      "quantity": 50,
      "description": "Tamaño adulto preferido"
    },
    {
      "part_id": "<part-uuid-finger>",
      "quantity": 100
    },
    {
      "part_id": "<part-uuid-hand>",
      "quantity": null,
      "description": "Cualquier cantidad bienvenida"
    }
  ]
}
```

**Response:** `201 Created`

```json
{
  "id": "rrrr1111-…",
  "title": "Ferulas for Venezuela",
  "description": "Campaña de férulas …",
  "deadline": "2026-08-15",
  "requester_user_id": null,
  "requester_organization_id": "cccc1111-…",
  "created_by_id": "<user-uuid>",
  "preferred_collection_center_ids": ["…", "…"],
  "status": "open",
  "active": true,
  "items": [
    {
      "id": "ii1-…",
      "part_id": "<part-uuid-forearm>",
      "quantity": 50,
      "description": "Tamaño adulto preferido",
      "deadline": null,
      "status": "open",
      "committed": 0,
      "delivered": 0,
      "remaining": 50
    },
    { "id": "ii2-…", "part_id": "<part-uuid-finger>", "quantity": 100, "...": "..." },
    { "id": "ii3-…", "part_id": "<part-uuid-hand>", "quantity": null, "...": "..." }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

**Errors:** `400 REQUEST_REQUIRES_ITEMS`, `404 PART_NOT_FOUND`,
`403 ORG_MEMBERSHIP_REQUIRED`

#### GET /requests

Public. Query params: `status`, `country` (resolves through preferred
centers), `q`, `page`, `per_page`. Returns paginated `{ items,
pagination }` where each item is a Request summary.

#### GET /requests/{id}

Public. Includes the items array with per-item progress.

#### PUT /requests/{id}

Edit campaign-level fields (title, description, deadline, preferred
centers). **Effective requester** (FR-042) or mod/admin.

#### POST /requests/{id}/close

`{ "reason": "..." }`. **Effective requester / mod / admin** (FR-043
/ FR-044). Cascades: every open item is closed; every `claimed`
Contribution on those items is released with reason `request_closed`
(FR-049).

##### Request items

| Method | Path | Description |
|---|---|---|
| `GET`    | `/requests/{id}/items` | List items. Public. |
| `POST`   | `/requests/{id}/items` | Add a new item. **Effective requester** (FR-122). |
| `GET`    | `/requests/{id}/items/{item_id}` | Item detail with contribution breakdown. |
| `PUT`    | `/requests/{id}/items/{item_id}` | Edit item-level fields. **Effective requester.** |
| `DELETE` | `/requests/{id}/items/{item_id}` | Remove. **Effective requester** (FR-123). Rejected `409 ITEM_HAS_CONTRIBUTIONS` if any active Contribution references it; rejected `409 LAST_ITEM_CANNOT_BE_REMOVED` if it is the only remaining item. |
| `POST`   | `/requests/{id}/items/{item_id}/close` | Close one item without closing the parent Request. **Effective requester / mod / admin** (FR-124). |

---

### 7. Contributions

#### POST /contributions

Create a new Contribution. **Authenticated.**

**Request Body:**

```json
{
  "request_item_id": "ii1-…",
  "quantity": 5,
  "collection_center_id": "<cc-uuid-caracas>",
  "notes": "Batch 1 of 5 — printing this weekend"
}
```

**Response:** `201 Created`

```json
{
  "id": "co1-…",
  "request_item_id": "ii1-…",
  "request_id": "rrrr1111-…",
  "request_title": "Ferulas for Venezuela",
  "part_id": "<part-uuid-forearm>",
  "part_name": "Forearm splint v3",
  "maker_id": "<user-uuid>",
  "collection_center_id": "<cc-uuid-caracas>",
  "quantity": 5,
  "notes": "Batch 1 of 5 — printing this weekend",
  "status": "claimed",
  "claimed_at": "2026-06-27T01:00:00Z",
  "printed_at": null,
  "delivered_at": null,
  "received_at": null,
  "received_by_id": null,
  "auto_received": false,
  "released_at": null,
  "released_reason": null,
  "active": true,
  "created_at": "2026-06-27T01:00:00Z",
  "updated_at": "2026-06-27T01:00:00Z"
}
```

**Errors:**

- `404 REQUEST_ITEM_NOT_FOUND`
- `409 REQUEST_NOT_OPEN` — parent Request is closed or fulfilled
- `409 COLLECTION_CENTER_NOT_VERIFIED_OR_ACTIVE`

#### GET /contributions/me

Authenticated user's own contributions. Query params: `status`,
`request_id`, `collection_center_id`, `page`, `per_page`. Backs the
"My Prints" tab (FR-060).

#### GET /contributions/{id}

Visible to: maker, effective members of the target Centro, effective
requesters of the parent Request, mod/admin.

#### POST /contributions/{id}/mark-printed

Transitions `claimed → printed`. **Maker only.**

#### POST /contributions/{id}/mark-delivered

Transitions `printed → delivered`. **Maker only.**

> When the maker is also an effective member of the target Centro
> (FR-126), this call also auto-advances the status to `received`
> in the same transaction. The response contains `status="received"`
> and `auto_received=true`. An `auto_receive_contribution` audit
> entry is written.

#### POST /contributions/{id}/confirm-received

Transitions `delivered → received`. **Effective member of the target
Centro / mod / admin** (FR-056). Sets `received_by_id` to the caller.

#### POST /contributions/{id}/release

`{ "reason": "..." }`. **Maker only**, while status is `claimed` or
`printed` (FR-054). Sets status to `released` with reason `manual`.

---

### 8. Ownership Transfers

The polymorphic transfer flow applies to **Parts, Collection Centers,
and Requests** (FR-118).

#### POST /parts/{id}/transfers

Initiate a transfer.

**Request Body:**

```json
{
  "target_user_id": "<user-uuid>"
}
```

Either `target_user_id` or `target_organization_id` is required.

**Response:** `201 Created`

```json
{
  "id": "tx1-…",
  "asset_type": "part",
  "asset_id": "<part-uuid>",
  "source_user_id": "<caller-uuid>",
  "source_organization_id": null,
  "target_user_id": "<user-uuid>",
  "target_organization_id": null,
  "initiated_by_id": "<caller-uuid>",
  "resolved_by_id": null,
  "status": "pending",
  "reason": null,
  "expires_at": "2026-07-04T00:00:00Z",
  "resolved_at": null
}
```

**Errors:** `409 TRANSFER_ALREADY_PENDING`, `403 NOT_EFFECTIVE_OWNER`

#### POST /collection-centers/{id}/transfers — same shape

#### POST /requests/{id}/transfers — same shape

#### GET /transfers/me

Pending transfers where the caller is the target (must accept or
decline) or the source (can cancel). Query param `direction=incoming|
outgoing|all` (default `all`).

#### GET /transfers/{id}

Single transfer. Visible to source/target principals and mod/admin.

#### POST /transfers/{id}/accept

Target accepts. Atomic ownership swap (FR-112).

- If `target_user_id` was set: only that user can call.
- If `target_organization_id` was set: any active `owner` of the org
  can call on its behalf.

**Response:** `200 OK` — full transfer plus the updated asset summary.

#### POST /transfers/{id}/decline

Same authorization as accept. `{ "reason": "..." }`.

#### POST /transfers/{id}/cancel

The initiating effective owner cancels a pending transfer (FR-113).

#### POST /parts/{id}/force-transfer | similar paths for CCs & Requests

**Maintainer / admin only** (FR-116). `{ "target_user_id": "...",
"reason": "owner unreachable" }`.

---

### 9. Discovery & Prioritization

The discovery endpoints power the "What to print next" experience —
the headline value of PrintForHelp.

#### GET /discovery/next

Ranks open RequestItems per FR-065.

**Query Parameters:**

- `country` (optional) — filter to items whose preferred centers
  include one in that country
- `tag` (optional, repeatable) — filter to items whose Part has that
  tag
- `featured_only` (bool) — only featured-Part items
- `show_all` (bool) — skip the FR-066 reachable-Centro filter
- `page`, `per_page`

**Response:** `200 OK`

```json
{
  "items": [
    {
      "request_item_id": "ii1-…",
      "request_id": "rrrr1111-…",
      "request_title": "Ferulas for Venezuela",
      "part_id": "<part-uuid>",
      "part_name": "Forearm splint v3",
      "part_featured": false,
      "quantity": 50,
      "committed": 12,
      "remaining": 38,
      "effective_deadline": "2026-08-15",
      "preferred_collection_centers": [
        { "id": "<cc>", "name": "UCAB Lab — Caracas", "country": "VE" }
      ]
    }
  ],
  "pagination": { "page": 1, "per_page": 20, "total": 47, "pages": 3 }
}
```

#### GET /discovery/dashboard

Aggregate stats (FR-067).

**Response:** `200 OK`

```json
{
  "open_requests": 8,
  "open_request_items": 47,
  "quantity_remaining_total": 1842,
  "delivered_last_30d": 612,
  "top_parts": [
    { "id": "<part>", "name": "Finger splint v2", "remaining_total": 480 },
    { "id": "<part>", "name": "Forearm splint v3", "remaining_total": 320 },
    { "...": "..." }
  ]
}
```

#### GET /discovery/parts/{part_id}/chart

Rolling-30-day contributions chart for one Part (FR-068).

**Response:** `200 OK`

```json
{
  "part_id": "<part>",
  "window_days": 30,
  "points": [
    { "date": "2026-05-29", "claimed": 12, "delivered": 5 },
    { "date": "2026-05-30", "claimed": 9, "delivered": 3 }
  ]
}
```

---

### 10. Audit Log

#### GET /audit-log

**Maintainer / admin only.**

Query params: `actor_id`, `action`, `target_type`, `target_id`,
`before` (cursor), `limit` (default 100, max 500).

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "au1-…",
      "actor_id": "<user>",
      "actor_username": "alice",
      "action": "verify_collection_center",
      "target_type": "CollectionCenter",
      "target_id": "<cc>",
      "reason": null,
      "created_at": "2026-06-27T02:00:00Z"
    }
  ],
  "next_before": "2026-06-26T22:00:00Z"
}
```

---

### 11. Personal Access Tokens

| Method | Path | Description |
|---|---|---|
| `GET`    | `/api-tokens/` | List the caller's tokens (metadata only). |
| `POST`   | `/api-tokens/` | Create a token. The plaintext `token` is returned **once**. |
| `DELETE` | `/api-tokens/{token_id}` | Revoke (soft delete). |

PATs are prefixed `pforh_pat_` and may be sent as bearer tokens
anywhere a JWT is accepted.

---

### 12. System Endpoints

#### GET /enums

Returns every documented enum so the frontend doesn't hard-code them.

```json
{
  "user_roles": ["user", "maintainer", "admin"],
  "locales": ["es", "en"],
  "part_statuses": ["active", "discontinued"],
  "collection_center_statuses": ["active", "inactive"],
  "organization_statuses": ["active", "inactive"],
  "request_statuses": ["open", "fulfilled", "closed"],
  "contribution_statuses": [
    "claimed", "printed", "delivered", "received", "released"
  ],
  "organization_roles": ["owner", "member"],
  "collection_center_roles": ["contributor"],
  "ownership_transfer_asset_types": ["part", "collection_center", "request"],
  "ownership_transfer_statuses": [
    "pending", "accepted", "declined", "cancelled", "expired",
    "force_transferred"
  ]
}
```

#### GET /health

```json
{
  "status": "healthy",
  "service": "printforhelp-api",
  "version": "1.0.0"
}
```

---

## Error Codes

| Code | HTTP | Description |
|---|---|---|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `WEAK_PASSWORD` | 400 | Password does not meet strength policy |
| `INCORRECT_PASSWORD` | 400 | Current password is incorrect |
| `INVALID_CREDENTIALS` | 401 | Invalid username or password |
| `INVALID_TOKEN` | 401 | Invalid or expired token |
| `INACTIVE_USER` | 403 | User account is inactive |
| `ROLE_REQUIRED` | 403 | Endpoint requires a higher role |
| `LOCKOUT_PROTECTION` | 403 | Cannot demote/deactivate the last active admin (FR-014) |
| `NOT_EFFECTIVE_OWNER` | 403 | Caller is not an effective owner of the asset |
| `NOT_EFFECTIVE_MEMBER` | 403 | Caller is not an effective member of the Collection Center |
| `ORG_MEMBERSHIP_REQUIRED` | 403 | Caller is not an active member of the referenced Organization |
| `PART_NOT_FOUND` | 404 | Part not found |
| `COLLECTION_CENTER_NOT_FOUND` | 404 | Collection Center not found |
| `ORGANIZATION_NOT_FOUND` | 404 | Organization not found |
| `REQUEST_NOT_FOUND` | 404 | Request not found |
| `REQUEST_ITEM_NOT_FOUND` | 404 | Request item not found |
| `CONTRIBUTION_NOT_FOUND` | 404 | Contribution not found |
| `TRANSFER_NOT_FOUND` | 404 | Ownership transfer not found |
| `USER_NOT_FOUND` | 404 | User not found |
| `API_TOKEN_NOT_FOUND` | 404 | API token not found |
| `USERNAME_TAKEN` | 409 | Username already exists |
| `ORG_NAME_TAKEN` | 409 | Organization name already exists |
| `PART_ARCHIVE_BLOCKED` | 409 | Part has open Requests referencing it (FR-076) |
| `CC_ARCHIVE_BLOCKED` | 409 | Collection Center has open Contributions (FR-079) |
| `ORG_ARCHIVE_BLOCKED` | 409 | Organization still owns active assets (FR-104) |
| `REQUEST_REQUIRES_ITEMS` | 400 | A Request must contain at least one item (FR-119) |
| `LAST_ITEM_CANNOT_BE_REMOVED` | 409 | Cannot remove the last item from an active Request (FR-119) |
| `ITEM_HAS_CONTRIBUTIONS` | 409 | Cannot remove an item with active Contributions (FR-123) |
| `REQUEST_NOT_OPEN` | 409 | Cannot create a Contribution on a non-open parent Request |
| `COLLECTION_CENTER_NOT_VERIFIED_OR_ACTIVE` | 409 | Centro must be verified and active (FR-064) |
| `CONTRIBUTION_NOT_IN_EXPECTED_STATE` | 409 | Status transition not allowed from current state |
| `TRANSFER_ALREADY_PENDING` | 409 | An asset cannot have two pending transfers (FR-115) |
| `TRANSFER_NOT_PENDING` | 409 | Accept/decline/cancel allowed only on `pending` |
| `OWNER_CANNOT_LEAVE` | 409 | Owner must transfer ownership first (FR-087, FR-100) |
| `INTERNAL_SERVER_ERROR` | 500 | Server error |

## HTTP Status Codes

- `200 OK` — successful GET / PUT / POST that mutates state
- `201 Created` — POST that creates a new resource
- `204 No Content` — successful DELETE / self-deactivate
- `400 Bad Request` — invalid request data
- `401 Unauthorized` — auth required or invalid token
- `403 Forbidden` — insufficient permissions
- `404 Not Found` — resource not found
- `409 Conflict` — state-based rejection (membership rules, archive
  guards, transfer rules)
- `422 Unprocessable Entity` — semantic validation failure
- `500 Internal Server Error` — server error

## Rate Limiting

- **Authenticated**: 1,000 requests / hour
- **Authentication endpoints**: 10 requests / minute / IP
- **Discovery endpoints**: 60 requests / minute / user (these are
  heavier aggregations)

## Data Validation Rules

### Identifiers

- All IDs are UUID v4.

### Quantities

- `Contribution.quantity`, `RequestItem.quantity`: positive integers
- `RequestItem.quantity` may be `null` (means "as many as possible";
  the item never auto-fulfills, FR-121)
- Maximum quantity per single Contribution: 1,000 (sanity guard)

### Dates & Times

- Dates: `YYYY-MM-DD`
- Timestamps: ISO 8601 with `Z` suffix
- `deadline`: not enforced to be in the future (back-fill of historical
  campaigns is allowed) — but the frontend warns

### Text Fields

- `Organization.name`: 1–120 chars, unique
- `Part.name`, `CollectionCenter.name`, `Request.title`: 1–200 chars
- `description` fields: up to 10,000 chars, markdown
- Free-text contact/notes: up to 2,000 chars

---

## API Usage Examples

### End-to-End: "Ferulas for Venezuela"

The exact workflow described in §3.5 of the requirements doc.

```javascript
const API = "http://localhost:8100/api/v1";

// 1. Log in (after self-registering as `alice`)
const login = await fetch(`${API}/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: "username=alice&password=securePassword123",
});
const { access_token: token } = await login.json();
const H = { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" };

// 2. Register a Collection Center (Caracas drop-off)
const cc = await (await fetch(`${API}/collection-centers/`, {
  method: "POST",
  headers: H,
  body: JSON.stringify({
    name: "Casa de Alice — Caracas",
    address: "Av. Principal, Caracas",
    country: "VE",
    city: "Caracas",
    contact: "+58-...",
  }),
})).json();

// 2b. As admin, verify it (alice happens to be the bootstrap admin)
await fetch(`${API}/collection-centers/${cc.id}/verify`, { method: "POST", headers: H });

// 3. Register the Parts in the catalog
const forearm = await (await fetch(`${API}/parts/`, {
  method: "POST", headers: H,
  body: JSON.stringify({
    name: "Forearm splint v3",
    source_url: "https://www.thingiverse.com/thing:9999",
    tags: ["splint", "forearm"],
  }),
})).json();
const finger = await (await fetch(`${API}/parts/`, {
  method: "POST", headers: H,
  body: JSON.stringify({
    name: "Finger splint v2",
    source_url: "https://www.thingiverse.com/thing:9998",
    tags: ["splint", "finger"],
  }),
})).json();

// 4. Create the campaign Request bundling both Parts
const req = await (await fetch(`${API}/requests/`, {
  method: "POST", headers: H,
  body: JSON.stringify({
    title: "Ferulas for Venezuela",
    description: "Campaña férulas - terremoto junio 2026",
    deadline: "2026-08-15",
    preferred_collection_center_ids: [cc.id],
    items: [
      { part_id: forearm.id, quantity: 50 },
      { part_id: finger.id, quantity: 100 },
    ],
  }),
})).json();

// 5. Claim a Contribution for the first batch (5 forearm splints)
const forearmItemId = req.items.find(i => i.part_id === forearm.id).id;
const c1 = await (await fetch(`${API}/contributions/`, {
  method: "POST", headers: H,
  body: JSON.stringify({
    request_item_id: forearmItemId,
    quantity: 5,
    collection_center_id: cc.id,
    notes: "Batch 1 of 10",
  }),
})).json();

// 6. After printing, mark printed
await fetch(`${API}/contributions/${c1.id}/mark-printed`, { method: "POST", headers: H });

// 7. After delivering to Centro
//    Because alice is the user-owner of the Centro (an effective member),
//    this auto-advances to `received` per FR-126 — auto_received=true.
const delivered = await (await fetch(`${API}/contributions/${c1.id}/mark-delivered`, {
  method: "POST", headers: H,
})).json();
console.log(delivered.status);          // → "received"
console.log(delivered.auto_received);   // → true

// 8. (Future) Share the registration link
//    Other users self-register at /auth/register and repeat steps 5-7.
```

### Inviting an Organization to Take Over a Part

Once UCAB Lab joins, alice transfers ownership of the forearm Part:

```javascript
// 1. UCAB Lab is registered (by their admin user, not alice)
//    -> orgId = "cccc1111-…"

// 2. Alice initiates the transfer to UCAB
const tx = await (await fetch(`${API}/parts/${forearm.id}/transfers`, {
  method: "POST", headers: H,
  body: JSON.stringify({ target_organization_id: orgId }),
})).json();

// 3. Any UCAB owner accepts on behalf of the org
//    (calling with their own JWT)
const accepted = await fetch(`${API}/transfers/${tx.id}/accept`, {
  method: "POST",
  headers: { Authorization: `Bearer ${ucabOwnerJwt}` },
});
// Part's owner_user_id now NULL; owner_organization_id = orgId. Atomic swap.
```

This reproduces the "creator joins later" scenario the polymorphic
ownership model was designed for.
