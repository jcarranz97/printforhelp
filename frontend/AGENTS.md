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
│   ├── users.api.ts        # admin user CRUD (server-side)
│   └── links.ts            # external links (GitHub, Discord, API URLs)
├── i18n/                   # Translation layer (see i18n section below)
│   ├── config.ts           # LOCALES, DEFAULT_LOCALE, LOCALE_NAMES, cookie
│   ├── server.ts           # getServerI18n() for server components
│   ├── provider.tsx        # I18nProvider + useI18n() for client
│   └── dictionaries/       # es.ts (source of truth) + en.ts
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

### Internationalization (i18n) — required for every UI change

The UI is bilingual **ES/EN** (NFR-015) and **every user-facing string
must be translated in both languages**. There are **no hardcoded
user-facing strings** — all copy lives in the dictionaries under
`frontend/i18n/`:

```text
i18n/
├── config.ts             # LOCALES, DEFAULT_LOCALE ("es"), LOCALE_NAMES,
│                         #   pforh_locale cookie name, normalizeLocale
├── server.ts             # getServerI18n() — server components/actions
├── provider.tsx          # I18nProvider + useI18n() — client components
└── dictionaries/
    ├── es.ts             # Spanish — the SOURCE OF TRUTH for the shape
    └── en.ts             # English — typed as `Dictionary`
```

**How the safety net works:** `es.ts` exports the `es` object plus
`export type Dictionary = typeof es`. `en.ts` is declared
`export const en: Dictionary`, so if `en.ts` is **missing a key, has an
extra key, or has a wrong type** relative to `es.ts`, `tsc` fails.
A forgotten translation is therefore a **compile error**, not a silent
fallback — `npx tsc --noEmit` is what keeps the two languages in sync.

**Workflow whenever you add or change visible text:**

1. Add the string to **`es.ts`** under the right namespace (e.g. `nav`,
   `header`, `landing`, `about`, `contribute`, …). Group related keys
   together; never inline a literal in a component.
2. Add the **same key with the English text** to `en.ts`, keeping the
   key order aligned with `es.ts` for readability.
3. Read it in the component — never type the text inline:
   - **Server** components / actions:
     `const { dict } = await getServerI18n();` (from `@/i18n/server`).
   - **Client** components (`"use client"`):
     `const { dict, locale } = useI18n();` (from `@/i18n/provider`).
4. Localize **server-action error messages** too — pass the relevant
   `dict` slice into the `messageFor` helper; don't return raw strings.
5. Run `npx tsc --noEmit` and fix any missing/extra-key errors before
   you finish.

**Other notes:**

- The active locale comes from the `pforh_locale` cookie. On the
  **first visit** (no cookie yet) the server falls back to the
  browser's `Accept-Language` header (`localeFromAcceptLanguage` in
  `config.ts`), and `getServerI18n` returns `localeChosen: false`. The
  root layout then renders `LocaleToast`, a one-time toast letting the
  visitor switch language; choosing or dismissing writes the cookie so
  it never reappears.
- The header `LocaleToggle` (a HeroUI `Dropdown` menu) changes it later
  via the `setLocaleAction` server action and calls `router.refresh()`
  so server components re-render in the new language.
- Language endonyms shown in the picker ("Español", "English") live in
  `LOCALE_NAMES` in `config.ts`, not in the dictionaries.
- To add a **new locale**: add it to `LOCALES` and `LOCALE_NAMES` in
  `config.ts`, then create a fully-translated `dictionaries/<code>.ts`
  typed as `Dictionary` (the compiler will list every key to fill in).

## Validation Checklist Before Finishing

After implementing any frontend change, run all of the following and
fix every error before stopping. CI runs the same checks — if they
fail locally, the PR build will fail.

If you added or changed any user-facing text, **first** confirm both
`es.ts` and `en.ts` were updated (see the i18n section above). The
TypeScript check below enforces this — a missing translation key fails
the build.

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
