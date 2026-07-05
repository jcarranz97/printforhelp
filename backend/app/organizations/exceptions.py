"""Domain exceptions for the organizations domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class OrganizationNotFoundExceptionError(AppExceptionError):
    """Raised when an organization cannot be found by id."""

    def __init__(self, organization_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.ORGANIZATION_NOT_FOUND,
            message=f"Organization {organization_id} not found.",
            status_code=404,
        )


class OrgNameTakenExceptionError(AppExceptionError):
    """Raised when creating an organization with an in-use name."""

    def __init__(self, name: str) -> None:
        super().__init__(
            error_code=ErrorCode.ORG_NAME_TAKEN,
            message=f"Organization name '{name}' is already taken.",
            status_code=409,
        )


class OrgHandleTakenExceptionError(AppExceptionError):
    """Raised when an org handle is already used by a user or another org."""

    def __init__(self, handle: str) -> None:
        super().__init__(
            error_code=ErrorCode.ORG_HANDLE_TAKEN,
            message=f"The handle '{handle}' is already in use.",
            status_code=409,
        )


class OrgMembershipRequiredExceptionError(AppExceptionError):
    """Raised when the caller is not an active member of an org (FR convention)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.ORG_MEMBERSHIP_REQUIRED,
            message="You must be an active member of this organization.",
            status_code=403,
        )


class NotEffectiveOwnerExceptionError(AppExceptionError):
    """Raised when the caller lacks owner powers on the organization."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.NOT_EFFECTIVE_OWNER,
            message="This action requires organization owner privileges.",
            status_code=403,
        )


class OrgArchiveBlockedExceptionError(AppExceptionError):
    """Raised when archiving an org that still owns active assets (FR-104)."""

    def __init__(self, active_asset_count: int) -> None:
        super().__init__(
            error_code=ErrorCode.ORG_ARCHIVE_BLOCKED,
            message=(
                "Cannot archive an organization that still owns active "
                "assets. Transfer or archive them first."
            ),
            status_code=409,
            details={"active_asset_count": active_asset_count},
        )


class OwnerCannotLeaveExceptionError(AppExceptionError):
    """Raised when an owner tries to leave without transferring first (FR-100)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.OWNER_CANNOT_LEAVE,
            message="The owner must transfer ownership before leaving.",
            status_code=409,
        )


class NotOrgMemberExceptionError(AppExceptionError):
    """Raised when the target user is not an active member of the org."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.NOT_ORG_MEMBER,
            message="The target user is not an active member of this organization.",
            status_code=409,
        )
