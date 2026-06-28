"""Audit-log write helper called by every mutating domain service."""

from uuid import UUID

from sqlalchemy.orm import Session

from . import models


def write_audit(
    db: Session,
    actor_id: UUID,
    action: str,
    target_type: str,
    target_id: UUID,
    reason: str | None = None,
) -> models.AuditLog:
    """Stage an audit entry on the session.

    The entry is added to the session but **not** committed; the calling
    service commits it in the same transaction as the mutation it records.
    """
    entry = models.AuditLog(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
    )
    db.add(entry)
    return entry
