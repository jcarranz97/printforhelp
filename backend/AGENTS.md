# PrintForHelp Backend

FastAPI backend for PrintForHelp. Python 3.13+, SQLAlchemy 2.0,
Pydantic 2.0, PostgreSQL.

The backend is in **scaffold** state — only `/health` and `/` endpoints
exist. Add domains under `app/<domain>/` following the same module pattern
used in the Colony project (router/schemas/models/service/dependencies/
exceptions/constants).

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
├── app/
│   ├── main.py          # FastAPI app factory
│   ├── config.py        # Settings (Pydantic BaseSettings)
│   └── database.py      # SQLAlchemy engine, SessionLocal, get_db()
└── pyproject.toml
```

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

```bash
PYTHONPATH=. uv run ruff check . --fix
PYTHONPATH=. uv run ruff format .
PYTHONPATH=. uv run pyright .
PYTHONPATH=. uv run pytest
```
