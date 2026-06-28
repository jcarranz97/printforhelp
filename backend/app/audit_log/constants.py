"""Documented action and target-type values for the audit log.

``action`` and ``target_type`` are stored as ``VARCHAR(64)`` (not ENUMs)
so new auditable actions can be introduced without a schema migration.
The values below are the source of truth for the service layer.
"""

from enum import StrEnum


class AuditAction(StrEnum):
    """Auditable actions (extend as new domains land)."""

    # Roles & users
    CHANGE_ROLE = "change_role"
    DEACTIVATE_USER = "deactivate_user"
    REACTIVATE_USER = "reactivate_user"
    CREATE_USER = "create_user"
    RESET_PASSWORD = "reset_password"


class AuditTargetType(StrEnum):
    """Auditable target entity types."""

    USER = "User"
