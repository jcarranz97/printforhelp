# PrintForHelp Backend

FastAPI backend for PrintForHelp. Python 3.13+, SQLAlchemy 2.0,
Pydantic 2.0, PostgreSQL.

**Phase 1 is implemented**: the `auth`, `users`, and `audit_log` domains
exist, with Alembic migrations, the default-admin bootstrap, and JWT auth
(Argon2ID). Add new domains under `app/<domain>/` following the same
module pattern used in the Colony project (router/schemas/models/service/
dependencies/exceptions/constants).

## Running Commands

```bash
# Start everything (recommended)
docker-compose up --build          # API at http://localhost:8100

# Backend only (no Docker)
cd backend
uv sync
uv run fastapi dev                 # hot reload

# Tests — PYTHONPATH=. is required
PYTHONPATH=. uv run pytest

# Linting & formatting
PYTHONPATH=. uv run ruff check . --fix
PYTHONPATH=. uv run ruff format .

# Type checking
PYTHONPATH=. uv run pyright .

# Migrations — once Alembic is initialized:
uv run alembic init alembic         # first-time setup
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

## Project Layout (current)

```text
backend/
├── alembic/             # Migrations (env.py + versions/)
├── app/
│   ├── main.py          # FastAPI app factory + lifespan bootstrap
│   ├── config.py        # Settings (Pydantic BaseSettings)
│   ├── database.py      # SQLAlchemy engine, SessionLocal, get_db()
│   ├── models.py        # Base + BaseModel (id/timestamps/active)
│   ├── exceptions.py    # AppExceptionError + global handlers
│   ├── dependencies.py  # CurrentUser/CurrentActiveUser/AdminUser
│   ├── permissions.py   # has_global_override (more lands in Phase 2)
│   ├── bootstrap.py     # Default-admin + dev-seed on startup
│   ├── auth/            # Login, JWT, password policy
│   ├── users/           # Admin user management
│   └── audit_log/       # Append-only audit trail
├── tests/               # auth/ + users/ (run against real Postgres)
├── alembic.ini
└── pyproject.toml
```

For local dev, `docker-compose` runs `alembic upgrade head` before
starting the API; the default admin and dev-seed accounts are created in
the app lifespan (`SEED_DEV_DATA=true`).

## Code Conventions (when adding code)

- **Type hints** on every function.
- **Google-style docstrings** on public functions.
- **88-character** line limit (Ruff enforces).
- **Double quotes** everywhere.
- All routes prefixed `/api/v1/`.
- Routers thin — business logic lives in `service.py`.
- Services raise domain exceptions inheriting `AppExceptionError`; never
  raise `HTTPException` directly inside services.
- Soft deletes only — set `active = False`; never `db.delete()`.
- Use `Annotated[X, Depends(Y)]` for dependency injection.

## Domain Module Layout (when adding a domain)

```text
app/<domain>/
├── router.py        # FastAPI routes — thin
├── schemas.py       # Pydantic request/response models
├── models.py        # SQLAlchemy ORM model (inherits BaseModel)
├── service.py       # All business logic; no HTTP concerns
├── dependencies.py  # Domain-level Depends() helpers
├── exceptions.py    # Domain exceptions (inherit AppExceptionError)
└── constants.py     # Enums, error codes, business constants
```

## Validation Checklist Before Finishing

Run all of the following from `backend/` and fix every error before
stopping. CI runs the same commands — if they fail locally, the PR
build will fail.

```bash
cd backend
PYTHONPATH=. uv run ruff check . --fix
PYTHONPATH=. uv run ruff format .
PYTHONPATH=. uv run pyright .
PYTHONPATH=. uv run pytest --tb=short -q
```

Pyright is strict — add type annotations to every function you write or
touch, including return types. Never use `Any` unless there is no
alternative and you add a comment explaining why.

### Pre-commit Hooks

Run pre-commit on every file you changed before finishing. Pre-commit
hooks run automatically on `git commit` and will abort the commit if
they modify any file (requiring re-staging). Catching this beforehand
avoids that disruption. Run from the **repo root** (where
`.pre-commit-config.yaml` lives), not from inside `backend/`:

```bash
# From repo root — list every backend file you changed:
pre-commit run --files backend/app/<domain>/service.py backend/AGENTS.md
```

Do **not** use `--all-files`; it processes the entire frontend too and
can run out of memory. Pass only the files you touched.

**Important**: `ruff` and `pyright` are **not** registered pre-commit
hooks in this repo. Do not run `pre-commit run ruff --files ...` — it
will fail with "No hook with id `ruff`". Run them directly:
`PYTHONPATH=. uv run ruff check . --fix`,
`PYTHONPATH=. uv run ruff format .`, and
`PYTHONPATH=. uv run pyright .`.

### Markdown Files

Pre-commit runs `markdownlint` on all `.md` files outside `docs/`. When
you create or edit any `.md` file, follow these rules or the commit
will fail:

- **80-character line limit** on prose lines (MD013).
- Code blocks (` ``` `) and table rows are exempt from the line limit.
- No trailing spaces, files must end with a newline.
- Run `pre-commit run markdownlint --files <your .md files>` to check.
