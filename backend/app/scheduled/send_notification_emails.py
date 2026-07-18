"""Drain the notification email outbox (send queued notification emails).

The send logic lives in
``notifications.service.send_pending_notification_emails`` so it is
unit-testable without a scheduler, and its ``FOR UPDATE SKIP LOCKED`` claim
makes it safe to run in parallel. This module is the standalone runnable
entrypoint for an external periodic trigger (e.g. a Kubernetes CronJob):
point a CronJob at ``python -m app.scheduled.send_notification_emails`` and
set ``NOTIFICATION_EMAIL_INPROCESS=false`` so the app does not also drain it
in-process. Run manually with ``python -m app.scheduled.send_notification_emails``.
"""

from app.database import SessionLocal
from app.notifications.service import send_pending_notification_emails


def run() -> int:
    """Open a session, send one batch of pending emails, return the count."""
    db = SessionLocal()
    try:
        return send_pending_notification_emails(db)
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover - manual / cron entrypoint
    count = run()
    print(f"Sent {count} notification email(s).")  # noqa: T201
