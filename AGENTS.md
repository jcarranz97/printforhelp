# PrintForHelp

Coordination platform for the 3D printing community to help people in
need (initial focus: Venezuela earthquake ferulas; long-term: general
humanitarian 3D-print coordination).

FastAPI backend + Next.js 15 frontend, PostgreSQL database, MkDocs docs,
Docker Compose for local dev. See `backend/AGENTS.md` and
`frontend/AGENTS.md` for domain-specific instructions.

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
PYTHONPATH=. uv run ruff check . --fix
PYTHONPATH=. uv run ruff format .
PYTHONPATH=. uv run pyright .
```

### Frontend

```bash
cd frontend
npm run dev
npx tsc --noEmit
```

## Structure

```text
backend/app/          # FastAPI app (domains added as features grow)
frontend/app/         # Next.js App Router
frontend/components/  # {feature}/index.tsx pattern
frontend/lib/         # apiClient + per-domain *.api.ts
docs/                 # MkDocs Material
```

## Key Constraints

- **PYTHONPATH=.** required for all backend pytest/ruff/pyright invocations.
- **Soft deletes only** — set `active = False`; never `db.delete()`.
- **No `HTTPException` in services** — raise domain exceptions inheriting
  `AppExceptionError`; global handler converts to JSON envelope.
- **80-char prose limit** on `.md` files outside `docs/` (markdownlint MD013).
- Code blocks and table rows are exempt from the 80-char limit.

## Status

The project is in its **landing page** stage. No domains, auth, or
database models have been implemented yet. Requirements and architecture
docs will be filled in next.
