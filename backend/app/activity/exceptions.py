"""Domain exceptions for the activity / comments domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class CommentNotFoundExceptionError(AppExceptionError):
    """Raised when a comment cannot be found by id."""

    def __init__(self, comment_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.COMMENT_NOT_FOUND,
            message=f"Comment {comment_id} not found.",
            status_code=404,
        )


class CommentNotAuthorExceptionError(AppExceptionError):
    """Raised when a non-author tries to edit a comment (FR-132)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.COMMENT_NOT_AUTHOR,
            message="Only the author can edit this comment.",
            status_code=403,
        )


class CommentDeleteForbiddenExceptionError(AppExceptionError):
    """Raised when a non-author / non-admin tries to delete a comment."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.COMMENT_DELETE_FORBIDDEN,
            message="Only the author or a maintainer/admin can delete this comment.",
            status_code=403,
        )


class InvalidReplyParentExceptionError(AppExceptionError):
    """Raised when a reply's parent comment is missing or on another entity."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.INVALID_REPLY_PARENT,
            message="The comment being replied to does not exist here.",
            status_code=404,
        )


class InvalidEntityReferenceExceptionError(AppExceptionError):
    """Raised when a comment targets a non-existent entity (FR-131)."""

    def __init__(self, entity_type: str, entity_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.INVALID_ENTITY_REFERENCE,
            message=f"No {entity_type} found with id {entity_id}.",
            status_code=404,
        )
