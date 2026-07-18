"""In-process background drain for the notification email outbox.

A daemon thread that periodically calls
``notifications.service.send_pending_notification_emails`` so notification
emails ship without any external scheduler — the zero-infrastructure default
(``NOTIFICATION_EMAIL_INPROCESS = true``). Turn it off when a Kubernetes
CronJob drives the standalone ``python -m app.scheduled.send_notification_emails``
entrypoint instead. Running it alongside other drains is safe: the drain's
``FOR UPDATE SKIP LOCKED`` claim guarantees no row is ever sent twice.

The drain uses synchronous SQLAlchemy, so it runs on its own thread rather
than the API event loop. The API lifespan starts one worker on boot and
stops it on shutdown.
"""

import logging
import threading

from app.config import settings
from app.database import SessionLocal
from app.notifications.service import send_pending_notification_emails

logger = logging.getLogger(__name__)


class EmailOutboxWorker:
    """A daemon thread that drains the outbox on a fixed interval."""

    def __init__(self, poll_seconds: int | None = None) -> None:
        self._poll_seconds = poll_seconds or settings.NOTIFICATION_EMAIL_POLL_SECONDS
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the background thread (no-op if already running)."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="email-outbox-worker", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the thread to stop and wait briefly for it to exit."""
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=5)
        self._thread = None

    def _run(self) -> None:
        """Drain, then wait ``poll_seconds``, until stopped."""
        while not self._stop.is_set():
            try:
                db = SessionLocal()
                try:
                    send_pending_notification_emails(db)
                finally:
                    db.close()
            except Exception:
                logger.exception("Notification email drain pass failed")
            self._stop.wait(self._poll_seconds)
