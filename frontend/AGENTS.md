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
