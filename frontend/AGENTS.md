# PrintForHelp Frontend

This is **Next.js 15 with App Router**, React 19, Tailwind CSS v4,
HeroUI v3. The frontend is currently in **landing page** state — no
authenticated app, no API client layer yet.

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
│   ├── layout.tsx       # Root layout with metadata
│   ├── page.tsx         # Landing page
│   ├── globals.css      # Tailwind + theme variables
│   └── providers.tsx    # next-themes provider
├── public/              # Static assets
├── next.config.ts
└── tsconfig.json
```

## When Adding Features

Adopt the same conventions used in the Colony project:

- Single-file component pattern: `components/{feature}/index.tsx` plus an
  `actions.ts` for API-call wrappers.
- `lib/*.api.ts` for raw `apiClient` calls.
- `actions/auth.action.ts` is the only file allowed to use `"use server"`
  (cookie reads are server-only). Do **not** add `"use server"` to
  `components/*/actions.ts` — `apiClient` must run in the browser to
  reach the backend container.
- Public routes go under `app/(public)/` and protected routes under
  `app/(app)/` once auth is added.

## Validation Checklist Before Finishing

```bash
cd frontend && npx tsc --noEmit
# From repo root:
pre-commit run prettier --files frontend/app/page.tsx frontend/app/globals.css
```
