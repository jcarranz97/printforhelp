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
    SELF_REGISTER = "self_register"
    RESET_PASSWORD = "reset_password"

    # Organizations
    VERIFY_ORGANIZATION = "verify_organization"
    REVOKE_ORGANIZATION_VERIFICATION = "revoke_organization_verification"
    ORG_ADD_MEMBER = "org_add_member"
    ORG_REMOVE_MEMBER = "org_remove_member"
    ORG_TRANSFER_OWNERSHIP = "org_transfer_ownership"
    FORCE_TRANSFER_ORG_OWNERSHIP = "force_transfer_org_ownership"

    # Collection Centers
    VERIFY_COLLECTION_CENTER = "verify_collection_center"
    REVOKE_COLLECTION_CENTER = "revoke_collection_center"
    FORCE_ARCHIVE_COLLECTION_CENTER = "force_archive_collection_center"
    RESTORE_COLLECTION_CENTER = "restore_collection_center"
    ADD_CONTRIBUTOR = "add_contributor"
    REMOVE_CONTRIBUTOR = "remove_contributor"


class AuditTargetType(StrEnum):
    """Auditable target entity types."""

    USER = "User"
    ORGANIZATION = "Organization"
    ORGANIZATION_MEMBERSHIP = "OrganizationMembership"
    COLLECTION_CENTER = "CollectionCenter"
    COLLECTION_CENTER_MEMBERSHIP = "CollectionCenterMembership"
