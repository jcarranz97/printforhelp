"""Domain exceptions for the reactions domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class InvalidReactionTargetExceptionError(AppExceptionError):
    """Raised when a reaction targets a non-reactable, missing, or hidden entity."""

    def __init__(self, entity_type: str, entity_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.INVALID_REACTION_TARGET,
            message=f"Cannot react to {entity_type} {entity_id}.",
            status_code=404,
        )
