# Software Requirements Specification

## 1. Introduction

### 1.1 Purpose

This document specifies the functional and non-functional requirements
for PrintForHelp, a coordination platform that connects people who need
3D-printed parts with the maker community that can print and deliver
them.

### 1.2 Scope

PrintForHelp will provide:

- A catalog of 3D-printable parts contributed by the community
- A directory of physical drop-off Collection Centers
- A request board where people in need can post the parts they require
- A contribution lifecycle so makers can claim, print, deliver, and
  confirm receipt of printed parts
- Prioritization views that show the community which open requests need
  print capacity the most, avoiding duplicated effort
- Role-based access (user, maintainer, admin) with maintainer
  moderation of catalog, requests, collection centers, and delivery confirmation

### 1.3 Background

The platform was initially conceived in response to the June 2026
Venezuela earthquake, where independent 3D-printing groups began
producing medical splints (ferulas) for the injured and coordinated
informally via social media. The lack of a central coordination tool
caused duplicated work and made it hard for makers to know which
splints were most needed and where to send them. PrintForHelp aims to
solve that coordination problem first for the Venezuela response and
then as a general-purpose hub for community-driven 3D-printed
humanitarian aid.

## 2. Overall Description

### 2.1 Product Perspective

PrintForHelp is a standalone web application consisting of:

- A RESTful API backend (FastAPI) with role-based access control
- A responsive web frontend (Next.js) with a bilingual ES/EN UI
- A containerized deployment solution (Docker Compose for development,
  Kubernetes for production)

### 2.2 User Classes

| Actor | Description |
|---|---|
| **Guest** | An unauthenticated visitor — can browse public catalog and collection centers, register, or log in |
| **User** | An authenticated account — can post requests, claim prints, register parts and collection centers |
| **Maintainer** | A trusted account with moderation powers — verifies collection centers, edits/closes any request, moderates the parts catalog, confirms received contributions |
| **Admin** | A system administrator — has all maintainer powers plus user role management |

## 3. Functional Requirements

### 3.1 User Authentication & Registration

- **FR-001**: Guests must be able to self-register an account by
  providing a unique username and a password.
- **FR-002**: Passwords must meet a minimum strength policy (length and
  composition rules enforced server-side).
- **FR-003**: Users must be able to log in using their username and
  password.
- **FR-004**: Users must be able to log out, which invalidates their
  session.
- **FR-005**: Users must be able to change their password while
  authenticated.
- **FR-006**: Users must be able to update their preferred locale
  (`es` or `en`) which controls the UI language.
- **FR-007**: A default admin user must be created automatically on
  first deploy from environment variables, mirroring the bootstrap
  pattern used by the Colony project.
- **FR-008**: Users must be able to deactivate their own account
  (soft delete; data preserved for historical attribution).

### 3.2 User Roles & Permissions

- **FR-009**: Every user must have exactly one role: `user`,
  `maintainer`, or `admin`. New accounts default to `user`.
- **FR-010**: Only admins must be able to change another user's role.
- **FR-011**: The permission matrix below must be enforced by the
  backend; the frontend must hide controls the current user cannot
  invoke.

#### Permission Matrix

| Action | User | Maintainer | Admin |
|---|---|---|---|
| Create / edit own Parts | ✓ | ✓ | ✓ |
| Mark own Part as `discontinued` | ✓ | ✓ | ✓ |
| Archive own Part (only if no open Requests reference it) | ✓ | ✓ | ✓ |
| Edit any Part | — | ✓ | ✓ |
| Force-archive any Part (auto-closes referencing Requests) | — | ✓ | ✓ |
| Mark a Part as `featured` | — | ✓ | ✓ |
| Register a Collection Center | ✓ | ✓ | ✓ |
| Edit own Collection Center (while `verified = false`) | ✓ | ✓ | ✓ |
| Mark own Collection Center as `inactive` | ✓ | ✓ | ✓ |
| Archive own Collection Center (only if no open Contributions routed to it) | ✓ | ✓ | ✓ |
| Edit any Collection Center | — | ✓ | ✓ |
| Verify a Collection Center | — | ✓ | ✓ |
| Force-archive any Collection Center (releases routed Contributions) | — | ✓ | ✓ |
| Manage Shipments of a Collection Center you are an effective member of | ✓ | ✓ | ✓ |
| Manage Shipments of any Collection Center | — | ✓ | ✓ |
| Post / edit own comments (authenticated) | ✓ | ✓ | ✓ |
| Delete any comment | — | ✓ | ✓ |
| Create a Request | ✓ | ✓ | ✓ |
| Edit / close own Request | ✓ | ✓ | ✓ |
| Edit / close any Request | — | ✓ | ✓ |
| Claim a Contribution | ✓ | ✓ | ✓ |
| Advance own Contribution to `printed` / `delivered` | ✓ | ✓ | ✓ |
| Confirm a Contribution as `received` | — | ✓ | ✓ |
| Change another user's role | — | — | ✓ |
| Deactivate / reactivate another user | — | — | ✓ |

- **FR-012**: Admins must be able to deactivate or reactivate any
  user account.
- **FR-013**: A user whose account is deactivated must not be able to
  log in, but their historical Parts, Requests, and Contributions must
  remain visible (attributed to the deactivated account).
- **FR-014**: The system must prevent the last active admin from being
  demoted or deactivated, to avoid lockout.

### 3.3 Parts Catalog

- **FR-015**: Users must be able to register a Part in the catalog with
  the following attributes:
  - Name
  - Description (markdown supported)
  - Source URL (link to the STL/3MF file or model page)
  - Image URL (optional preview image) — **Phase 4 addition** not in the
    original SRS; lets the catalog and request views show a thumbnail
  - Suggested print settings (optional free-text field) — **deferred**,
    not yet implemented in the Phase 4 backend
  - Tags (optional list)
  - Owner — either the registering user themselves (default) or an
    Organization the registering user is an active member of (see
    §3.9 and the polymorphic ownership rules in §3.10)
- **FR-016**: The creator of a Part (the user who first registered it)
  must be recorded as immutable historical attribution. The Part's
  current owner — a User or an Organization — is tracked separately
  per §3.10 and may change over time via ownership transfer.
- **FR-017**: The owner of a Part must be able to edit it. When the
  Part is user-owned, this means the owner User; when it is
  org-owned, any active member of the owning Organization. See
  §3.10 for the polymorphic owner definition that applies to all
  "owner can …" rules below.
- **FR-018**: Maintainers and admins must be able to edit any Part
  regardless of authorship (catalog moderation). Archival semantics
  for Parts are specified separately in FR-076 (owner) and FR-077
  (moderator force-archive).
- **FR-019**: Maintainers and admins must be able to flag a Part as
  `featured` so it surfaces at the top of the catalog and on the
  landing page.
- **FR-020**: Parts must have a status of `active` or `discontinued`.
  Only active Parts can be referenced by new Requests.
- **FR-021**: Users must be able to view the full catalog, filtered by
  tag, status, and free-text search on name and description.
- **FR-022**: The catalog list must show, for each Part, the number of
  open Requests referencing it so makers can spot popular needs at a
  glance.
- **FR-023**: The detail view of a Part must list all open Requests
  that reference it, with quantity remaining and deadline.
- **FR-024**: The system must validate that the Source URL is a valid
  URL but must not require it to resolve (some sources are private
  Discord / Drive links).
- **FR-025**: Parts must be soft-deleted (`active = false`), never
  hard-deleted, to preserve historical Contribution attribution.
- **FR-075**: A Part's creator must be able to mark their own Part as
  `discontinued` at any time. Once discontinued, no new Requests may
  reference the Part, but existing Requests, Contributions, and
  catalog visibility remain unchanged. The action is reversible by
  the creator (or any maintainer/admin) by setting status back to
  `active`.
- **FR-076**: A Part's creator must be able to archive (soft-delete,
  `active = false`) their own Part only if no `open` Requests
  reference it. If any `open` Request exists, the request must be
  rejected with a clear error directing the user to mark the Part
  `discontinued` instead, or to escalate to a maintainer.
- **FR-077**: Maintainers and admins must be able to force-archive any
  Part regardless of referencing Requests. When this happens, every
  `open` Request referencing the Part must be automatically
  transitioned to `closed` with the system-generated reason
  `part_archived`, and the action must be recorded in the audit log
  (FR-008 / NFR-008).

### 3.4 Collection Centers

- **FR-026**: Any authenticated user must be able to register a
  Collection Center with the following attributes:
  - Name
  - Address (free-text)
  - Country
  - City
  - Contact (phone / email / social handle, free-text)
  - Opening hours (optional free-text)
  - Notes (optional free-text)
  - Owner — either the registering user themselves (default) or an
    Organization the registering user is an active member of (see
    §3.9 and §3.10)
- **FR-027**: A newly registered Collection Center must default to
  `verified = false` and must not appear in the public-facing
  collection centers list until a maintainer or admin verifies it.
- **FR-028**: A pending Collection Center must be visible to its
  members (see §3.4 Membership) and to maintainers/admins under a
  "Pending verification" filter.
- **FR-029**: Maintainers and admins must be able to verify a Collection Center
  by flipping the `verified` flag to `true`.
- **FR-030**: Maintainers and admins must be able to revoke
  verification on an existing Collection Center (revert to `verified = false`)
  with an optional reason that is recorded in an audit log.
- **FR-031**: Any active member of a Collection Center (owner or
  contributor — see Membership FRs below) must be able to edit the
  Collection Center's attributes at any time, regardless of its
  `verified` status. Edits to a verified Collection Center must
  preserve verification (do not automatically revoke); revocation is
  a separate maintainer action (FR-030).
- **FR-032**: Maintainers and admins must be able to edit any Collection Center
  at any time.
- **FR-033**: Collection Centers must support a status of `active` or
  `inactive`. An inactive Collection Center must not be selectable as
  a delivery target for new Contributions but must remain visible for
  historical reference.
- **FR-034**: Users must be able to browse the list of verified active
  Collection Centers, filtered by country and city.
- **FR-035**: Each Collection Center's detail view must show the number of
  Contributions currently in `delivered` state awaiting confirmation,
  so the collection center operator knows how much inventory is waiting.
- **FR-036**: Collection Centers must be soft-deleted, never hard-deleted, to
  preserve historical Contribution attribution.
- **FR-037**: The system must record `registered_by` (the user who
  created the Collection Center, immutable historical attribution)
  and `verified_by` (the maintainer/admin who verified it), both as
  FK references to User. The current owner of the Collection Center
  is stored separately (either `owner_user_id` or
  `owner_organization_id`, exactly one non-null per §3.10) and may
  change over time via ownership transfer.
- **FR-078**: Any active member of a Collection Center must be able to
  flip its status between `active` and `inactive` at any time. An
  inactive Collection Center cannot receive new Contributions but
  remains visible for historical reference (FR-033).
- **FR-079**: Only the Collection Center's owner (or a maintainer or
  admin) must be able to archive (soft-delete, `active = false`) the
  Collection Center. The action must be rejected if any `open`
  Contributions (status `claimed`, `printed`, or `delivered`) are
  routed to the Collection Center; the error must direct the owner to
  mark the Collection Center `inactive` instead, or to escalate to a
  maintainer.
- **FR-080**: Maintainers and admins must be able to force-archive any
  Collection Center regardless of routed Contributions. When this
  happens, every open Contribution routed to that Collection Center
  must be automatically transitioned to `released` with the
  system-generated reason `collection_center_archived`, and the
  action must be recorded in the audit log (FR-008 / NFR-008).

#### Collection Center Membership

Each Collection Center has a team of users — its **owner** and zero or
more **contributors** — who collectively operate it. This decentralizes
day-to-day management so maintainers are not the bottleneck for routine
operational changes (toggling status, confirming deliveries, editing
contact info).

- **FR-081**: The system must support a `CollectionCenterMembership`
  entity that links a `User` to a `CollectionCenter` as an additional
  per-center `contributor`. This is distinct from the polymorphic
  owner (User or Organization) stored on the Collection Center itself
  per §3.10 — the membership table does not record owners.
- **FR-082**: When a user registers a new Collection Center (FR-026),
  the system must set the owner principal on the Collection Center
  directly: either `owner_user_id = creator.id` (the default) or
  `owner_organization_id = org.id` if the creator is registering on
  behalf of an Organization they are an active member of (§3.10). No
  membership row is created for the owner; ownership is recorded on
  the Collection Center entity. The original creator is also stored
  as `registered_by_id` for immutable historical attribution (FR-037).
- **FR-083**: An active Collection Center must always have exactly
  one owner principal: either `owner_user_id` or
  `owner_organization_id` non-null, never both, never neither. The
  system must enforce this invariant on every write to the Collection
  Center.
- **FR-084**: The Collection Center's effective owner (the
  user-owner if user-owned, or any active `owner` member of the
  owning Organization if org-owned — see §3.10) must be able to add
  another user as a per-center `contributor` by username. The
  membership becomes active immediately; there is no separate accept
  step in v1.
- **FR-085**: The Collection Center's effective owner must be able to
  remove any per-center `contributor` at any time. The removed user
  loses all member powers on that Collection Center but retains
  historical attribution on any Contributions they confirmed as
  `received` while a member.
- **FR-086**: A per-center `contributor` must be able to leave a
  Collection Center voluntarily at any time (deactivate their own
  membership).
- **FR-087**: The Collection Center's user-owner (when user-owned)
  must not be able to release ownership without going through the
  transfer flow defined in §3.10 (FR-109 — initiate transfer with
  recipient acceptance). For org-owned Collection Centers, the
  individual user has no "owner of the Center" role to release —
  ownership lives at the org level.
- **FR-088**: Ownership transfer of a Collection Center (to a
  different User or a different Organization) is the polymorphic
  transfer flow defined in §3.10 (FR-109 – FR-114). Unlike the
  earlier owner→contributor transfer pattern, the recipient is a
  separate principal (not necessarily a current per-center member)
  and must accept the transfer.
- **FR-089**: When the user-owner of a Collection Center is
  deactivated (FR-013) and the Center has no org owner, the Center
  is considered orphaned. Maintainers and admins must be able to
  force-transfer ownership to any user or organization via FR-113
  (polymorphic force-transfer). Force-transfer must be recorded in
  the audit log.
- **FR-090**: Any user who has effective member powers on a
  Collection Center — the user-owner, any per-center contributor,
  or any active member of the owning Organization when org-owned —
  must be able to view the full list of the Center's contributors
  and (when org-owned) the owning Organization's members on the
  Center's detail view.
- **FR-091**: Per-center membership creations, removals, and
  ownership-related events (initiate, accept, decline, cancel,
  expire, force-transfer per §3.10) must each be recorded in the
  audit log (NFR-008) with actor, target user/org, target Collection
  Center, and optional reason.
- **FR-092**: The system must prevent a user who lacks effective
  member powers on a Collection Center (i.e., is not the user-owner,
  not a per-center contributor, not a member of the owning
  Organization, and not a maintainer/admin) from invoking any
  member-scoped action defined above. Frontend hiding of these
  controls is for UX only and must not be the sole defense
  (per NFR-006).
- **FR-093**: Future feature (deferred to a later release): each
  Collection Center should be able to declare which Parts it accepts
  (a per-center filter on the global Parts catalog), so makers see
  upfront which centers will receive a given Part. No FR is binding
  until the membership and ownership models are delivered.

##### Collection Center Membership Permission Matrix

This sub-matrix scopes actions to a specific Collection Center. The
columns are: a user with no relationship to the Center (**Non-member**),
a per-center `contributor` (**Contrib**), an active **member of the
owning Organization** when the Center is org-owned (**OrgMember**),
the Center's **effective owner** (the user-owner directly, or any
active `owner` of the owning Organization when org-owned), the global
**Maintainer** role, and the global **Admin** role. Maintainer and
Admin always have member-equivalent powers on every Collection Center.

| Action on a Collection Center | Non-member | Contrib | OrgMember | Owner | Maintainer | Admin |
|---|---|---|---|---|---|---|
| View public details | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| View contributor list & pending deliveries | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Edit details (FR-031) | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Toggle `active` / `inactive` (FR-078) | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Confirm a routed Contribution as `received` (FR-056) | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Add a per-center contributor (FR-084) | — | — | — | ✓ | ✓ | ✓ |
| Remove a per-center contributor (FR-085) | — | — | — | ✓ | ✓ | ✓ |
| Leave the Collection Center (self-remove contributor) (FR-086) | — | ✓ | n/a | n/a | n/a | n/a |
| Initiate ownership transfer (FR-088 / §3.10) | — | — | — | ✓ | — | ✓ |
| Force-transfer ownership (FR-089 / §3.10) | — | — | — | — | ✓ | ✓ |
| Archive the Collection Center (FR-079) | — | — | — | ✓ | ✓ | ✓ |
| Force-archive the Collection Center (FR-080) | — | — | — | — | ✓ | ✓ |
| Verify / revoke verification (FR-029 / FR-030) | — | — | — | — | ✓ | ✓ |

### 3.5 Print Requests

A **Request** is a campaign-level container ("Ferulas for Venezuela")
that bundles one or more **RequestItems**. Each RequestItem is a
specific Part with its own target quantity and lifecycle. Contributions
attach to RequestItems, not to the parent Request. This lets a single
campaign cover multiple distinct printable parts without forcing the
requester to create one Request per Part.

#### Request (campaign-level)

- **FR-038**: Authenticated users must be able to create a Request with
  the following attributes:
  - Title (required; e.g. "Ferulas for Venezuela")
  - Description (markdown supported, optional context for the campaign
    as a whole)
  - Deadline (optional date; applies to every item unless an item
    overrides it)
  - Preferred Collection Centers (optional list of FK Collection
    Centers — hints to makers which drop-off points are closest to
    the eventual beneficiary)
  - Requester — either the creating user themselves (default) or an
    Organization the creating user is an active member of (see §3.10
    and FR-125 for the polymorphic requester rules)
  - At least one RequestItem (FR-120). A Request without items must
    be rejected with a validation error.
- **FR-039**: The requester of a Request is polymorphic: either a
  User (`requester_user_id`) or an Organization
  (`requester_organization_id`) per §3.10, with exactly one non-null.
  The user who actually clicked "Create" is recorded separately as
  immutable historical attribution.
- **FR-040**: A Request must have a lifecycle status:
  - `open` — at least one RequestItem is still accepting Contributions
  - `fulfilled` — every RequestItem on the Request is `fulfilled`
  - `closed` — manually closed (by the Request's effective requester,
    maintainer, or admin) before all items reached `fulfilled`
- **FR-041**: The system must automatically transition a Request from
  `open` to `fulfilled` when every RequestItem on the Request is
  `fulfilled` (FR-121). A Request with at least one item whose status
  is still `open` cannot be auto-fulfilled.
- **FR-042**: The Request's effective requester (FR-109 mapping
  applied to Requests) must be able to edit campaign-level Request
  metadata (title, description, deadline, preferred Centers) while
  the Request is `open`. Item-level edits follow FR-120.
- **FR-043**: The Request's effective requester must be able to close
  their own Request at any time, with an optional reason. Closing a
  Request cascades to all its open RequestItems (FR-049 / FR-124).
- **FR-044**: Maintainers and admins must be able to edit or close
  any Request at any time, with an optional reason that is recorded
  in the audit log.
- **FR-045**: A Request's detail view must show:
  - The list of RequestItems with their progress (Part, quantity,
    committed, remaining, deadline, status)
  - Aggregate progress across items (total committed, total delivered,
    total received, total remaining)
  - The full Contribution breakdown grouped by item
- **FR-046**: Users must be able to browse open RequestItems (not
  parent Requests; see FR-065), filtered by Part, deadline, and
  remaining quantity, sorted by default by `deadline ASC,
  remaining DESC`. The parent Request's title is always displayed
  alongside the item so makers know the campaign context.
- **FR-047**: A Request must not be deletable. Closing it preserves
  historical attribution; once `fulfilled` or `closed`, the Request
  and all its items become read-only except for moderator audit
  fields.
- **FR-049**: When a Request is closed before fulfilment, every
  RequestItem still `open` on that Request must be transitioned to
  `closed`, and every Contribution still in `claimed` state on those
  items must be automatically transitioned to `released` (with reason
  `request_closed`), freeing makers to pick up other work.

#### RequestItem (line-item level)

- **FR-119**: The system must support a `RequestItem` entity. Every
  Request must contain at least one RequestItem at all times; if the
  last RequestItem on an `open` Request is removed, the system must
  reject the removal (the requester must close the whole Request
  instead). Each Contribution (FR-050) references a single
  RequestItem.
- **FR-120**: A RequestItem must have the following attributes:
  - Request (FK, required; the parent campaign)
  - Part (FK, required; must reference an `active` Part). A given Part
    may appear at most **once** as an active RequestItem on a Request —
    duplicates are rejected (`DUPLICATE_PART`, 409) on both create and
    add-item. Re-adding a Part after its item was removed is allowed.
  - Quantity (optional positive integer — null means "as many as
    possible" for that item)
  - Description (markdown, optional; item-level context such as
    sizing, color, or batch notes)
  - Deadline (optional date; overrides the parent Request's deadline
    when present)
  - Status — see FR-121
- **FR-121**: A RequestItem must have a lifecycle status independent
  of its parent Request:
  - `open` — accepting new Contributions
  - `fulfilled` — `Σ(contributions.quantity where status ≥ delivered)
    ≥ requestitem.quantity`. Items with a null quantity never
    auto-fulfill and must be closed manually.
  - `closed` — manually closed before fulfilment (by the Request's
    effective requester, maintainer, or admin)
- **FR-122**: A Request's effective requester must be able to add new
  RequestItems to a Request while the Request is `open`. Adding an
  item is always allowed regardless of any other item's state.
- **FR-123**: A Request's effective requester must be able to remove
  a RequestItem from an `open` Request only if it has no active
  Contributions (none in `claimed`, `printed`, `delivered`, or
  `received`). If it has active Contributions, the requester must
  close the item instead (FR-124), which releases any `claimed`
  contributions. The last remaining item on a Request cannot be
  removed (FR-119).
- **FR-124**: A Request's effective requester (or any
  maintainer/admin) must be able to close an individual RequestItem
  without closing the parent Request, with an optional reason. When
  an item is closed, every Contribution still in `claimed` state on
  that item must be automatically transitioned to `released` (with
  reason `request_item_closed`). The parent Request remains `open`
  unless all other items are also closed or fulfilled.
- **FR-125**: When the polymorphic requester (FR-039) is an
  Organization, all FRs in this section that refer to "the Request's
  effective requester" resolve through §3.10's effective-owner
  mapping: any active `owner` of the owning Organization can act as
  the requester. Plain organization `member`s have no Request-level
  powers; only `owner`s can edit or close on behalf of an Org. (This
  is stricter than the Collection Center model because a Request is
  a campaign-level commitment, not a day-to-day operational asset.)

### 3.6 Contributions

A Contribution represents a single maker's commitment to print a
specific quantity of one RequestItem (a specific Part within a
campaign-level Request, see §3.5) and the delivery of those printed
units to a Collection Center.

- **FR-050**: Authenticated users must be able to create a Contribution
  on an `open` RequestItem with the following attributes:
  - RequestItem (FK, required; the parent Request's status must also
    be `open`)
  - Quantity (positive integer, required)
  - Target Collection Center (FK Collection Center, required; must
    be `verified` and `active`)
  - Notes (optional free-text)
  The parent Request is reachable via the RequestItem; queries that
  need to filter Contributions by campaign should JOIN through
  `request_items`.
- **FR-051**: A new Contribution must start in `claimed` status with
  `claimed_at` set to the current timestamp.
- **FR-052**: A Contribution must support the following lifecycle:
  - `claimed` — maker has committed to print; not yet started
  - `printed` — printing complete; not yet dropped off
  - `delivered` — dropped off at the target Collection Center;
    awaiting confirmation
  - `received` — Collection Center operator (maintainer/admin) has confirmed
    receipt; closes the loop
  - `released` — voluntarily abandoned by the maker or expired
    (terminal, frees the quantity back to the Request)
- **FR-053**: A maker must be able to advance their own Contribution
  from `claimed → printed → delivered`. They must not be able to
  advance it to `received` (that requires the target Collection
  Center's members, or a maintainer/admin — see FR-056).
- **FR-054**: A maker must be able to release their own Contribution
  while it is in `claimed` or `printed` status, transitioning it to
  `released` and freeing the committed quantity.
- **FR-055**: A `claimed` Contribution that has not advanced to
  `printed` within a configurable number of days (default 14) must
  expire automatically (status set to `released`) so committed quantity
  does not block other makers indefinitely.
- **FR-056**: Only an active effective member (FR-110) of the
  Contribution's target Collection Center, or any maintainer/admin,
  must be able to transition a Contribution to `received`. The system
  must record `received_at` and `received_by_id` on this transition.
- **FR-126**: When a maker advances their own Contribution to
  `delivered` and that maker is also an active effective member
  (FR-110) of the target Collection Center, the system must
  automatically transition the Contribution to `received` in the same
  operation. The `received_by_id` must be set to the maker, and an
  `auto_receive_contribution` audit log entry must be written so the
  inferred receipt is traceable. If the maker is not an effective
  member of the target Centro, the Contribution remains in
  `delivered` and a manual confirmation per FR-056 is required.
- **FR-057**: A maker must be able to edit the quantity and notes of
  their Contribution only while it is in `claimed` status. Once it
  has advanced past `claimed`, the quantity is locked.
- **FR-058**: Each status transition must record an immutable
  timestamp (`claimed_at`, `printed_at`, `delivered_at`, `received_at`,
  `released_at` as applicable) and the actor user ID.
- **FR-059**: Contributions must not be deletable. The `released`
  status is the only way to back out of a Contribution.
- **FR-060**: Users must be able to view all their own Contributions
  ("My Prints" tab), filterable by status.
- **FR-061**: A Request's detail view must list all Contributions
  routed to every one of its RequestItems, grouped by item, including
  the maker's username, quantity, target collection center, and
  current status.
- **FR-062**: When computing "committed quantity" for a RequestItem
  (FR-121) — and by extension the Request roll-up (FR-041) —
  Contributions in `released` status must be excluded; Contributions
  in `claimed`, `printed`, `delivered`, and `received` must all be
  counted.
- **FR-063**: When computing "delivered quantity" for a RequestItem's
  auto-fulfilment (FR-121), only Contributions in `delivered` or
  `received` status must be counted.
- **FR-064**: The system must prevent a Contribution from being
  created against a Collection Center that is not `verified` and
  `active`, even if the user can otherwise see the Collection Center.

### 3.7 Discovery & Prioritization

This is the headline value of PrintForHelp: helping the community see
at a glance which open RequestItems most need print capacity, so
makers don't duplicate work.

- **FR-065**: The system must expose a prioritization view ("What to
  print next") that ranks open RequestItems (not parent Requests) by:
  - The effective deadline (`item.deadline ?? parent_request.deadline`)
    ASC — urgent first; null deadlines last
  - `remaining DESC` where
    `remaining = max(0, item.quantity − Σ active committed quantity)`
  - Featured Parts boosted above non-featured Parts at the same
    urgency tier
  Each row in the view must display both the item's Part name and the
  parent Request's title for context (e.g., "Forearm splint · Ferulas
  for Venezuela").
- **FR-066**: The prioritization view must filter RequestItems so
  that only items whose parent Request lists at least one `verified`
  and `active` Collection Center the maker can reasonably ship to are
  shown by default, with a toggle to show all open items globally.
- **FR-067**: The dashboard must show aggregate statistics:
  - Total open Requests and total open RequestItems
  - Total quantity remaining across all open RequestItems
  - Total quantity delivered in the last 30 days
  - Top 5 most-needed Parts (by aggregated remaining quantity across
    every open RequestItem that references the Part)
- **FR-068**: A Part's detail view must include a small chart of
  contributions over time (rolling 30-day window) so the community
  can see whether the response is keeping up with demand.
- **FR-069**: The prioritization view must be cache-warmed and update
  in near-real-time (≤ 5 seconds) when a Contribution status changes
  or a new RequestItem is created.
- **FR-070**: Aggregations in the discovery view must always use the
  live committed/delivered totals defined in FR-062 and FR-063; no
  denormalized counters that can drift.

### 3.8 Navigation

- **FR-071**: The application navigation must have the following tabs:
  - **Parts** — catalog of printable designs (public, read-only for
    guests; create / edit for users)
  - **Requests** — open print requests (public read; create / edit
    for users)
  - **Collection Centers** — directory of verified drop-off locations
    (public read; register for users)
  - **Organizations** — directory of verified organizations
    (public read; create / manage for users; verify for maintainers)
  - **My Prints** — the current user's Contributions (authenticated
    only)
  - **Users** — user and role management (admin only)
- **FR-072**: Guests must be able to browse Parts, Requests, Collection
  Centers, and Organizations without an account; any action that
  requires authentication must prompt them to log in or register.
- **FR-073**: The navigation must surface a persistent CTA to switch
  the UI language between Spanish (`es`) and English (`en`).
- **FR-074**: Each tab must reflect the user's role: admin-only tabs
  must not be rendered for non-admin users; controls gated by the
  permission matrix (§3.2) must be hidden from users who lack the
  permission.

### 3.9 Organizations

An Organization is a named group of users that can own Parts and
Collection Centers. Organizations let real-world entities (makerspaces,
hospitals, university labs, NGOs) operate on PrintForHelp under their
own identity, distinct from any single user account. Organizations are
also the recipient of ownership transfers from individuals — a single
volunteer can publish parts now, and once the originating organization
joins, ownership can be reassigned to them via §3.10.

- **FR-094**: Any authenticated user must be able to create an
  Organization with the following attributes:
  - Name (unique across all Organizations)
  - Description (markdown supported, optional)
  - Contact (phone / email / social handle, free-text, required)
  - Website (optional URL)
  - Country (required)
- **FR-095**: When a user creates an Organization, the system must
  atomically create an `OrganizationMembership` for the creator with
  role `owner`. The creator is also recorded as `registered_by_id` on
  the Organization for immutable historical attribution.
- **FR-096**: Organizations must default to `verified = false`.
  Maintainers and admins must be able to verify an Organization by
  flipping the `verified` flag to `true`, recording `verified_by_id`
  and the verification timestamp. Unverified Organizations may still
  own Parts and Collection Centers (FR-105) but are visibly flagged
  on public views.
- **FR-097**: Maintainers and admins must be able to revoke
  verification on an Organization (revert to `verified = false`) with
  an optional reason recorded in the audit log.
- **FR-098**: The owner of an Organization must be able to add another
  user as a `member` by username. The membership becomes active
  immediately; there is no separate accept step. Members can leave
  voluntarily at any time (FR-099).
- **FR-099**: The owner of an Organization must be able to remove any
  `member`. A `member` must be able to leave the Organization
  voluntarily at any time (deactivate their own membership).
- **FR-100**: The owner of an Organization must not be able to leave
  or remove their own membership. To step down, the owner must first
  transfer Organization ownership (FR-101).
- **FR-101**: The owner of an Organization must be able to transfer
  Organization ownership to any existing active `member`. The
  transfer is atomic: the new user becomes `owner` and the prior
  owner is demoted to `member`. Because the recipient is already a
  member of the Organization, no separate accept step is required.
- **FR-102**: When the owner of an Organization is deactivated
  (FR-013), the Organization is considered orphaned. Maintainers and
  admins must be able to force-transfer Organization ownership to any
  active member (or, if no other members exist, first add a member
  and then force-transfer). Force-transfer must be recorded in the
  audit log.
- **FR-103**: Organizations must support a status of `active` or
  `inactive`. Only the Organization's owner (or a maintainer/admin)
  must be able to change the status. An inactive Organization cannot
  receive new ownership transfers (it cannot become an owner of new
  assets), but its existing owned Parts and Collection Centers
  continue to operate.
- **FR-104**: Only the Organization's owner (or a maintainer/admin)
  must be able to archive (soft-delete, `active = false`) an
  Organization. The action must be rejected if the Organization owns
  any active Parts or Collection Centers; assets must be transferred
  away (§3.10) or force-archived (FR-077, FR-080) first. There is no
  force-archive that bypasses this rule; the cascade through asset
  archival keeps the model clean.
- **FR-105**: An unverified Organization may own Parts and Collection
  Centers, but every public-facing view of those assets and of the
  Organization itself must clearly display an "Unverified
  organization" badge so users can judge trust.
- **FR-106**: Any active member of an Organization must be able to
  view the Organization's member list, owned Parts, and owned
  Collection Centers on the Organization's detail view. Public users
  see only the public attributes (name, description, contact, country,
  verified status) and the counts of public owned assets.

##### Organization Membership Permission Matrix

This sub-matrix scopes actions to a specific Organization. The
columns are: a user with no relationship to the Organization
(**Non-member**), an active `member` (**Member**), the Organization's
`owner` (**Owner**), the global **Maintainer** role, and the global
**Admin** role.

| Action on an Organization | Non-member | Member | Owner | Maintainer | Admin |
|---|---|---|---|---|---|
| View public details | ✓ | ✓ | ✓ | ✓ | ✓ |
| View member list & owned assets | — | ✓ | ✓ | ✓ | ✓ |
| Edit Organization details | — | — | ✓ | ✓ | ✓ |
| Add a member (FR-098) | — | — | ✓ | ✓ | ✓ |
| Remove a member (FR-099) | — | — | ✓ | ✓ | ✓ |
| Leave the Organization (self-remove) (FR-099) | — | ✓ | — | n/a | n/a |
| Transfer ownership to a member (FR-101) | — | — | ✓ | — | ✓ |
| Force-transfer ownership (FR-102) | — | — | — | ✓ | ✓ |
| Toggle `active` / `inactive` (FR-103) | — | — | ✓ | ✓ | ✓ |
| Archive the Organization (FR-104) | — | — | ✓ | ✓ | ✓ |
| Verify / revoke verification (FR-096 / FR-097) | — | — | — | ✓ | ✓ |
| Act on Organization-owned Parts / Centers | — | ✓ | ✓ | ✓ | ✓ |

The last row resolves to per-asset rules: a `member` acting on an
org-owned Part has the same powers as a user-owner; a `member` acting
on an org-owned Collection Center has the same powers as a per-center
contributor (and an `owner` of the Organization has the same powers as
the user-owner of that Center). See §3.10 for the formal mapping.

### 3.10 Polymorphic Ownership & Transfers

Parts and Collection Centers are owned by either a User or an
Organization, never both, never neither. This section defines the
polymorphic ownership model and the cross-principal transfer flow that
lets owners reassign assets to other users or organizations.

#### Ownership Model

- **FR-107**: Each Part and each Collection Center must have exactly
  one owner principal at all times. The owner is stored as two
  nullable foreign key columns on the asset — `owner_user_id` (FK
  User) and `owner_organization_id` (FK Organization) — with a
  database-level constraint enforcing that exactly one is non-null.
- **FR-108**: At registration time the registering user must declare
  the owner principal: either themselves (default, sets
  `owner_user_id`) or an Organization they are an active member of
  (sets `owner_organization_id`). Registering on behalf of an
  Organization the registering user is not a member of must be
  rejected with a clear error.
- **FR-109**: For all FRs in §3.3 (Parts) and §3.4 (Collection
  Centers) that grant powers to the "owner" or "creator" of an
  asset, the **effective owner** is defined as:
  - For a user-owned asset: the user identified by `owner_user_id`.
  - For an org-owned asset: any user who has an active
    `OrganizationMembership` with role `owner` on the owning
    Organization.
- **FR-110**: For all FRs that grant powers to "members" or
  "contributors" of a Collection Center, the **effective members**
  are defined as the union of:
  - The user-owner of the Center (when user-owned).
  - All active per-center contributors recorded in
    `CollectionCenterMembership`.
  - All active members of the owning Organization (when org-owned).

#### Ownership Transfer Flow

- **FR-111**: An asset's effective owner must be able to initiate an
  ownership transfer to a target principal (another User by username,
  or another Organization by name). Initiating a transfer creates an
  `OwnershipTransfer` row with status `pending` and records both the
  source and the target principals.
- **FR-112**: A pending transfer must be accepted or declined by the
  target principal:
  - When the target is a User, that user accepts or declines.
  - When the target is an Organization, any active `owner` of that
    Organization accepts or declines on its behalf.
  Acceptance atomically swaps the asset's ownership FKs to point at
  the target principal and sets the transfer status to `accepted`.
  Declining sets the status to `declined` and ownership is unchanged.
- **FR-113**: The initiating effective owner must be able to cancel a
  pending transfer at any time before it is accepted or declined,
  setting the status to `cancelled`.
- **FR-114**: A pending transfer must auto-expire after a configurable
  number of days (default 7), setting the status to `expired`.
  Ownership is unchanged on expiry. Expiry must be processed by a
  scheduled job and recorded in the audit log.
- **FR-115**: An asset must not have more than one transfer in
  `pending` status at a time. If the effective owner initiates a new
  transfer while one is already pending, the request must be rejected
  with an error directing the user to cancel the existing pending
  transfer first.
- **FR-116**: Maintainers and admins must be able to force-transfer
  ownership of any Part or Collection Center to any User or
  Organization without acceptance, recording the reason in the audit
  log. This is used to recover assets from deactivated owners
  (FR-089) or to resolve abuse and ownership disputes.
- **FR-117**: Initiating, accepting, declining, cancelling, expiring,
  and force-transferring ownership must each be recorded in the
  audit log (NFR-008).
- **FR-118**: The polymorphic ownership transfer flow (FR-111 –
  FR-116) applies to Parts, Collection Centers, and Requests. The
  `ownership_transfer_asset_type` enum therefore contains three
  values: `part`, `collection_center`, and `request`. Organization
  ownership transfer is a separate mechanism that lives within an
  Organization's own membership (FR-101). The `creator_id` /
  `registered_by_id` columns on assets remain immutable historical
  attribution regardless of how many times ownership is transferred.

### 3.11 Collection Center Shipments

A **Shipment** is a planned dispatch of collected aid from a Collection
Center to where it is needed (e.g. the earthquake zone). It tells the
community the deadline by which to drop off their printed parts, and
tracks whether the center is still accepting packages for that batch.

- **FR-127**: A Collection Center must be able to have zero or more
  Shipments. Each Shipment has a planned `shipment_date`, an optional
  free-text `destination` ("the place where it is needed"), and an
  optional Markdown `description`.
- **FR-128**: A Shipment must have a `status` of `receiving` (still
  accepting packages), `closed` (dispatched / no longer accepting), or
  `cancelled`. New Shipments default to `receiving`.
- **FR-129**: Creating, editing, deleting, and changing the status of a
  Shipment requires authentication and is restricted to the effective
  members of the Collection Center (its owner, per-center contributors,
  and — when org-owned — the owning organization's members) plus
  maintainers and admins (NFR-006). Unlike Collection Center
  registration (which is open to guests, see FR-027 notes), Shipments
  cannot be created anonymously.
- **FR-130**: Shipments must be publicly visible — listed on the
  Collection Center's public detail view whether or not the viewer is
  authenticated, and regardless of the center's `verified` flag — so the
  community always knows the upcoming drop-off deadlines. Deleting a
  Shipment is a soft delete (`active = false`) and removes it from the
  public list.

### 3.12 Comments & Activity Timeline

To coordinate around drop-offs and shipments, the platform provides a
lightweight, polymorphic comment and activity system (modelled on the
Colony project's feed) attachable to any supported entity. In v1 the
supported entities are Collection Centers and Shipments.

- **FR-131**: Any authenticated user must be able to post a comment on a
  commentable entity (Collection Center or Shipment). Comment bodies
  support **Markdown** (rendered client-side; raw HTML is not rendered).
  Comments are publicly readable by everyone, including guests, so a
  community member can leave a note (e.g. "shipped 12 splints today")
  without anyone needing to log in to read it. A comment must reference
  an existing entity.
- **FR-132**: A comment may be edited only by its author. A comment may
  be deleted (soft delete) by its author or by a maintainer/admin.
- **FR-133**: The system must maintain a public, append-only **activity
  timeline** per entity, recording lifecycle events — entity created,
  updated, status changed, deleted — and comment events. The timeline is
  polymorphic over `entity_type` + `entity_id` and is readable by
  everyone. It is independent of the internal moderation `audit_log`
  (§6.6 / NFR-008), which remains private.

## 4. Non-Functional Requirements

### 4.1 Performance

- **NFR-001**: The prioritization view must load within 2 seconds for a
  catalog of up to 1,000 open Requests.
- **NFR-002**: Aggregation queries (FR-067) must use indexed columns
  and must not exceed 500 ms server-side at the 1,000-Request scale.
- **NFR-003**: Status changes on a Contribution must propagate to the
  prioritization view within 5 seconds.

### 4.2 Security

- **NFR-004**: Passwords must be hashed with Argon2ID via `pwdlib`
  (matching Colony's auth standard).
- **NFR-005**: All API endpoints except `auth/register`, `auth/login`,
  and the public read endpoints for Parts / Requests / verified
  Collection Centers must require authentication.
- **NFR-006**: Role-based authorization must be enforced server-side
  on every protected endpoint. Frontend hiding of controls is for UX
  only and must never be the sole defense.
- **NFR-007**: All API traffic in production must be served over
  HTTPS.
- **NFR-008**: Audit-relevant actions (Collection Center verification,
  revocation, request override-close, role change, deactivate user,
  confirm received) must record actor, action, target, timestamp, and
  optional
  reason in an immutable audit log.

### 4.3 Usability

- **NFR-009**: The interface must be responsive across desktop,
  tablet, and mobile breakpoints.
- **NFR-010**: Forms must validate inline before submission and must
  surface server errors in the user's preferred locale.
- **NFR-011**: Empty states (no parts yet, no requests yet, no
  contributions yet) must include a clear next action.

### 4.4 Reliability

- **NFR-012**: All entities must be soft-deletable only
  (`active = false`); the database must never hard-delete user-created
  records.
- **NFR-013**: Database backups must run daily and be retained for at
  least 30 days.
- **NFR-014**: Status transitions on Contributions and Requests must
  be transactional — partial updates that would leave totals out of
  sync must roll back.

### 4.5 Internationalization

- **NFR-015**: The frontend must ship bilingual Spanish and English
  translations from the v1 release. Every user-visible string must be
  resolved through an i18n layer; no hard-coded copy in components.
- **NFR-016**: The current locale must be persisted on the User record
  (`preferred_locale`) so it survives across sessions and devices.
- **NFR-017**: Guests must default to the browser's `Accept-Language`
  preference, falling back to Spanish.

## 5. Technical Constraints

- Must use FastAPI (Python 3.13+) for the backend.
- Must use Next.js 15 (App Router) for the frontend.
- Must use PostgreSQL as the production database.
- Must be containerizable with Docker; Docker Compose for local
  development.
- Must use Alembic for schema migrations.
- Must use SQLAlchemy 2.0 with typed `Mapped[...]` columns.
- Must use Pydantic 2.0 for request/response validation.
- Must follow the domain module layout documented in
  `backend/AGENTS.md` (one folder per domain with the seven canonical
  files).

## 6. Data Requirements

### 6.1 User Schema

```text
- id: UUID
- username: String (unique, required)
- password_hash: String (Argon2ID)
- role: Enum (user, maintainer, admin)
- preferred_locale: Enum (es, en)
- active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

### 6.2 Part Schema

```text
- id: UUID
- name: String (required)
- description: String (markdown, optional)
- source_url: String (URL, required)
- suggested_settings: String (optional)
- tags: String[] (optional)
- status: Enum (active, discontinued)
- featured: Boolean (default false)
- creator_id: UUID (FK User, required; immutable historical
  attribution — see FR-016)
- owner_user_id: UUID (FK User, nullable)
- owner_organization_id: UUID (FK Organization, nullable)
- active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

Invariant: exactly one of `owner_user_id` or `owner_organization_id`
is non-null at all times (FR-107). Both columns are mutated atomically
when ownership is transferred (§3.10).

### 6.3 Collection Center Schema

```text
- id: UUID
- name: String (required)
- address: String (required)
- country: String (required)
- city: String (required)
- contact: String (required)
- location_url: String (optional; absolute http(s) map link, e.g.
  Google Maps)
- opening_hours: String (optional)
- notes: String (optional)
- verified: Boolean (default false)
- registered_by_id: UUID (FK User, required; immutable historical
  attribution — see FR-082)
- verified_by_id: UUID (FK User, nullable until verified)
- owner_user_id: UUID (FK User, nullable)
- owner_organization_id: UUID (FK Organization, nullable)
- status: Enum (active, inactive)
- active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

Invariant: exactly one of `owner_user_id` or `owner_organization_id`
is non-null at all times (FR-107 / FR-083). Both columns are mutated
atomically when ownership is transferred (§3.10).

The current owner of a Collection Center is therefore stored directly
on this row (not derived from any membership table). The
`CollectionCenterMembership` table (§6.7) tracks only per-center
contributors, never owners.

### 6.4 Request Schema

A Request is the campaign-level container; each Request has one or
more RequestItems (§6.11). The `part_id` and `quantity` fields that
were on Request in earlier drafts have moved to RequestItem.

```text
- id: UUID
- title: String (required)
- description: String (markdown, optional)
- deadline: Date (optional; applies to all items unless overridden
  at the item level — see §6.11)
- requester_user_id: UUID (FK User, nullable)
- requester_organization_id: UUID (FK Organization, nullable)
- created_by_id: UUID (FK User, required; the user who clicked
  "Create" — immutable historical attribution)
- preferred_collection_center_ids: UUID[] (FK Collection Center,
  optional)
- status: Enum (open, fulfilled, closed)
- closed_reason: String (optional; free-text or system-generated)
- closed_by_id: UUID (FK User, nullable)
- closed_at: DateTime (nullable)
- active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

Invariant: exactly one of `requester_user_id` or
`requester_organization_id` is non-null at all times (FR-039 /
FR-107). Both columns are mutated atomically when ownership is
transferred (§3.10 / FR-118).

### 6.5 Contribution Schema

```text
- id: UUID
- request_item_id: UUID (FK RequestItem, required; the parent Request
  is reachable via JOIN through request_items)
- maker_id: UUID (FK User, required)
- collection_center_id: UUID (FK Collection Center, required, must be
  verified and active)
- quantity: Integer (positive, required)
- notes: String (optional)
- status: Enum (claimed, printed, delivered, received, released)
- claimed_at: DateTime (set on creation)
- printed_at: DateTime (nullable)
- delivered_at: DateTime (nullable)
- received_at: DateTime (nullable)
- received_by_id: UUID (FK User, nullable; set on transition to
  `received`. Equals `maker_id` when auto-received per FR-126)
- auto_received: Boolean (default false; true when the receipt was
  auto-confirmed because the maker was an effective member of the
  target Centro — FR-126)
- released_at: DateTime (nullable)
- released_reason: String (optional; "manual", "expired",
  "collection_center_archived", "request_closed", or
  "request_item_closed")
- active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

### 6.6 Audit Log Schema

```text
- id: UUID
- actor_id: UUID (FK User, required)
- action: Enum (verify_collection_center, revoke_collection_center,
  force_archive_part, force_archive_collection_center,
  override_close_request, override_close_request_item,
  change_role, deactivate_user, reactivate_user, confirm_received,
  auto_receive_contribution, add_contributor, remove_contributor,
  verify_organization, revoke_organization_verification,
  org_add_member, org_remove_member, org_transfer_ownership,
  force_transfer_org_ownership, initiate_ownership_transfer,
  accept_ownership_transfer, decline_ownership_transfer,
  cancel_ownership_transfer, expire_ownership_transfer,
  force_transfer_ownership)
- target_type: String (User, Part, Collection Center, Request,
  RequestItem, Contribution, CollectionCenterMembership, Organization,
  OrganizationMembership, OwnershipTransfer)
- target_id: UUID (required)
- reason: String (optional)
- created_at: DateTime
```

### 6.7 Collection Center Membership Schema

This table records per-center contributors only. Ownership of a
Collection Center is stored on the Collection Center entity itself
(§6.3), not here.

```text
- id: UUID
- collection_center_id: UUID (FK Collection Center, required)
- user_id: UUID (FK User, required)
- role: Enum (contributor)
- invited_by_id: UUID (FK User, required)
- active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

Invariants:

- Unique active membership per (`collection_center_id`, `user_id`)
  pair — a user cannot have two simultaneous contributor memberships
  on the same Collection Center.
- The `role` enum currently has a single value (`contributor`). It
  remains an enum to leave room for future per-center roles without
  a schema migration.

### 6.8 Organization Schema

```text
- id: UUID
- name: String (unique, required)
- description: String (markdown, optional)
- contact: String (required)
- website: String (URL, optional)
- country: String (required)
- verified: Boolean (default false)
- registered_by_id: UUID (FK User, required; immutable historical
  attribution — see FR-095)
- verified_by_id: UUID (FK User, nullable until verified)
- status: Enum (active, inactive)
- active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

### 6.9 Organization Membership Schema

```text
- id: UUID
- organization_id: UUID (FK Organization, required)
- user_id: UUID (FK User, required)
- role: Enum (owner, member)
- invited_by_id: UUID (FK User, nullable; null for the auto-created
  owner membership at Organization registration)
- active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

Invariants:

- Unique active membership per (`organization_id`, `user_id`).
- Exactly one active membership with `role = 'owner'` per active
  Organization (FR-100).

### 6.10 Ownership Transfer Schema

```text
- id: UUID
- asset_type: Enum (part, collection_center, request)
- asset_id: UUID (required; FK Part, FK Collection Center, or FK
  Request depending on asset_type)
- source_user_id: UUID (FK User, nullable)
- source_organization_id: UUID (FK Organization, nullable)
- target_user_id: UUID (FK User, nullable)
- target_organization_id: UUID (FK Organization, nullable)
- initiated_by_id: UUID (FK User, required; the user who initiated)
- resolved_by_id: UUID (FK User, nullable; the user who accepted,
  declined, cancelled, or force-transferred)
- status: Enum (pending, accepted, declined, cancelled, expired,
  force_transferred)
- reason: String (optional; used on force-transfer)
- expires_at: DateTime (required)
- resolved_at: DateTime (nullable)
- created_at: DateTime
- updated_at: DateTime
```

Invariants:

- Exactly one of `source_user_id` or `source_organization_id` is
  non-null (the source principal at initiation time).
- Exactly one of `target_user_id` or `target_organization_id` is
  non-null (the target principal).
- At most one row per (`asset_type`, `asset_id`) may have
  `status = 'pending'` at any time (FR-115).

### 6.11 RequestItem Schema

A RequestItem is one line in a Request: a specific Part with a target
quantity. Contributions reference RequestItems, not the parent
Request. See §3.5 (FR-119 – FR-124) for the lifecycle.

```text
- id: UUID
- request_id: UUID (FK Request, required; ON DELETE CASCADE)
- part_id: UUID (FK Part, required; the Part must be `active` at
  insertion time)
- quantity: Integer (nullable; null = "as many as possible")
- description: String (markdown, optional; item-level context such
  as sizing, color, or batch notes)
- deadline: Date (optional; overrides the parent Request's deadline
  when non-null)
- status: Enum (open, fulfilled, closed)
- closed_reason: String (optional; free-text or system-generated
  values like "parent_request_closed", "part_archived")
- closed_by_id: UUID (FK User, nullable)
- closed_at: DateTime (nullable)
- active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

Invariants:

- Every active Request must have at least one active RequestItem
  (FR-119). The service layer enforces this on item removal.
- A Contribution's `request_item_id` must point at an item whose
  parent Request is `open` at the time the Contribution is created
  (FR-050).

### 6.12 Shipment Schema

A Shipment is a planned dispatch of aid from a Collection Center
(§3.11 / FR-127 – FR-130).

```text
- id: UUID
- collection_center_id: UUID (FK CollectionCenter, required;
  ON DELETE CASCADE)
- shipment_date: Date (required; the planned dispatch date)
- status: Enum (receiving, closed, cancelled; default receiving)
- destination: String(255) (optional; "the place where it is needed")
- description: String (markdown, optional)
- created_by_id: UUID (FK User, required; historical attribution)
- active: Boolean (soft delete)
- created_at: DateTime
- updated_at: DateTime
```

### 6.13 Comment Schema

A Comment is a user-authored, Markdown note attached polymorphically to
a commentable entity (§3.12 / FR-131 – FR-132).

```text
- id: UUID
- entity_type: String(40) (e.g. "collection_center", "shipment")
- entity_id: UUID (the target entity; no FK — polymorphic)
- author_user_id: UUID (FK User, required)
- body: Text (markdown, required, non-empty, max 10000 chars)
- edited_at: DateTime (nullable; set when the author edits)
- active: Boolean (soft delete)
- created_at: DateTime
- updated_at: DateTime
```

Indexed on `(entity_type, entity_id, created_at)` for fast per-entity
listing.

### 6.14 Activity Log Schema

The public activity timeline (§3.12 / FR-133). Distinct from the private
moderation `audit_log` (§6.6).

```text
- id: UUID
- entity_type: String(40)
- entity_id: UUID (polymorphic; no FK)
- actor_user_id: UUID (FK User, required)
- action: String(40) (created, updated, status_changed, deleted,
  commented, comment_edited, comment_deleted)
- changes: JSONB (event detail, e.g. {"status": {"from": "receiving",
  "to": "closed"}})
- active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

Indexed on `(entity_type, entity_id, created_at)`.

## 7. Integration Requirements

### 7.1 Authentication

- **IR-001**: Google OAuth must be supported as a future
  authentication option, with the goal of making it the primary
  signup path once available. Username/password remains supported for
  users who prefer not to link a Google account.

### 7.2 Notifications (Future)

- **IR-002**: Email notifications must be supported as a future
  feature for the following events:
  - A Request the user created has been fulfilled
  - A Contribution the user is responsible for has been confirmed as
    received
  - A Collection Center the user registered has been verified or had
    verification revoked
- **IR-003**: A future integration must allow makers to subscribe to
  alerts for new Requests matching a tag, Part, or country.
