# PrintForHelp Frontend

This is **Next.js 16 with App Router**, React 19, Tailwind CSS v4,
HeroUI v3. **Phase 1 (auth) is implemented**: a `/login` page, an
httpOnly-cookie session, a global top nav (HeroUI Tabs) with logged-in
state, `/logout`, the `/admin/users` management tab, and a `proxy.ts`
guard for `/admin/*`. The server-side API layer lives in `lib/` (raw
`fetch` calls), and cookie reads/writes live in `actions/auth.action.ts`.

## Running Commands

```bash
# Start everything (recommended)
docker-compose up --build          # Frontend at http://localhost:3001

# Frontend only (no Docker)
cd frontend
npm install
npm run dev
```

## Project Layout (current)

```text
frontend/
├── app/
│   ├── layout.tsx          # Root layout; renders the global TopNav
│   ├── page.tsx            # Landing page
│   ├── login/page.tsx      # Login page (HeroUI Card)
│   ├── logout/route.ts     # Clears the cookie, redirects to /
│   ├── admin/page.tsx      # Redirects to /admin/users
│   ├── admin/users/page.tsx # Admin user-management tab
│   ├── globals.css         # Tailwind + HeroUI styles + theme vars
│   └── providers.tsx       # next-themes provider
├── actions/
│   ├── auth.action.ts      # "use server" — cookie reads/writes, login
│   └── users.action.ts     # "use server" — admin user mutations
├── components/
│   ├── auth/login-form.tsx
│   ├── admin/create-user-form.tsx
│   ├── admin/users-table.tsx
│   ├── admin/reset-password-card.tsx
│   ├── layout/top-nav.tsx   # Global header (server): brand + auth state
│   └── layout/nav-tabs.tsx  # HeroUI Tabs nav (underlined), route-synced
├── lib/
│   ├── api.ts              # apiBaseUrl, ApiError, cookie name
│   ├── auth.api.ts         # loginRequest, fetchMe
│   └── users.api.ts        # admin user CRUD (server-side)
├── proxy.ts                # Route guard for /admin/* (was middleware.ts)
├── public/                 # Static assets
├── next.config.ts
└── tsconfig.json
```

## When Adding Features

Conventions for this codebase:

- The JWT lives in an **httpOnly cookie**, so the browser cannot read
  it. Every authenticated backend call therefore runs **server-side**.
- `lib/*.api.ts` hold raw `fetch` calls to the backend. They take the
  bearer `token` as an argument and are imported only by server code
  (server components, route handlers, or `actions/*.action.ts`). They
  use `apiBaseUrl()`, which prefers `API_URL_INTERNAL` (the in-network
  backend URL) over the public `NEXT_PUBLIC_API_URL`.
- `actions/*.action.ts` are the `"use server"` files. They read/write
  the auth cookie, re-verify authorization server-side (NFR-006), and
  call the `lib/*.api.ts` functions. New mutating flows add a new
  `*.action.ts` here.
- Client components (`"use client"`) handle interactivity and call the
  server actions; they never touch the cookie or the backend directly.
- `proxy.ts` redirects unauthenticated users away from `/admin/*`; it is
  a UX guard only — the real role check is repeated in the page/action.

### HeroUI v3 components

The UI is built with **HeroUI v3** (`@heroui/react`), which is a
compound, React-Aria-based API — different from v2. Notes:

- Use the **HeroUI MCP server** as the source of truth for component
  APIs (`get_component_docs`); do not guess props from memory/v2.
- Compound parts use dot notation: `Card.Header`, `Select.Trigger`,
  `Table.Body`, `Tabs.Tab`, `Alert.Content`, etc.
- Buttons use `onPress` (not `onClick`) and `isPending`/`isDisabled`.
- `Select` is controlled with `value`/`onChange` or form-bound with
  `name`/`defaultValue`; options are `ListBox.Item` with an `id`.
- The underlined Tabs style is `variant="secondary"` (there is no
  literal `"underlined"` value in v3).
- Styles load via `@import "@heroui/styles";` after `@import
"tailwindcss";` in `globals.css`. No Provider is required.

## Validation Checklist Before Finishing

After implementing any frontend change, run all of the following and
fix every error before stopping. CI runs the same checks — if they
fail locally, the PR build will fail.

Run TypeScript type checking from the `frontend/` directory:

```bash
cd frontend && npx tsc --noEmit
```

Run prettier on every file you modified. Prettier auto-formats
TypeScript, TSX, CSS, JSON, and Markdown. If you skip this step, the
`git commit` hook will modify your files and abort the commit,
requiring re-staging.

Run from the **repo root** (where `.pre-commit-config.yaml` lives),
not from inside `frontend/`. Pass only the files you changed — do
**not** use `--all-files`, which processes the whole repo and can run
out of memory:

```bash
# From repo root — list every frontend file you changed:
pre-commit run prettier --files frontend/app/page.tsx \
  frontend/app/globals.css
```

Also run markdownlint on any `.md` files you edited:

```bash
pre-commit run markdownlint --files frontend/AGENTS.md
```

### Markdown rules

Pre-commit runs `markdownlint` on all `.md` files outside `docs/`.
Follow these or the commit will fail:

- **80-character line limit** on prose lines (MD013).
- Code blocks (` ``` `) and table rows are exempt from the line limit.
- No trailing spaces, files must end with a newline.
