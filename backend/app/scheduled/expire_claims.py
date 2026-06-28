"""FR-055: auto-expire stale ``claimed`` Contributions.

The release logic lives in ``contributions.service.expire_stale_claims`` so
it is unit-testable without a scheduler. This module is the runnable
entrypoint: a deploy wires it to a periodic trigger (cron or APScheduler).
Run manually with ``python -m app.scheduled.expire_claims``.
"""

from app.contributions.service import expire_stale_claims
from app.database import SessionLocal


def run() -> int:
    """Open a session, expire stale claims, and return the count."""
    db = SessionLocal()
    try:
        return expire_stale_claims(db)
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover - manual / cron entrypoint
    count = run()
    print(f"Expired {count} stale claimed contribution(s).")  # noqa: T201
