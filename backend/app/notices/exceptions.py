"""Domain exceptions for the notices domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class NoticeNotFoundExceptionError(AppExceptionError):
    """Raised when a Notice cannot be found by id."""

    def __init__(self, notice_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.NOTICE_NOT_FOUND,
            message=f"Notice {notice_id} not found.",
            status_code=404,
        )


class NotEntityOwnerExceptionError(AppExceptionError):
    """Raised when the caller does not effectively own the target entity."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.NOT_ENTITY_OWNER,
            message="You can only request a notice on an item you own.",
            status_code=403,
        )


class InvalidNoticeModeExceptionError(AppExceptionError):
    """Raised when a notice is not exactly one of page mode / entity mode."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.INVALID_NOTICE_MODE,
            message=(
                "A notice must target either pages (scopes) or one entity "
                "(target_type + target_id), but not both."
            ),
            status_code=422,
        )


class TranslationsRequiredExceptionError(AppExceptionError):
    """Raised when a notice is created without at least one translation."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.TRANSLATIONS_REQUIRED,
            message="A notice needs at least one language translation.",
            status_code=422,
        )


class DuplicateLanguageExceptionError(AppExceptionError):
    """Raised when two translations share the same language code."""

    def __init__(self, language: str) -> None:
        super().__init__(
            error_code=ErrorCode.DUPLICATE_LANGUAGE,
            message=f"Duplicate translation for language '{language}'.",
            status_code=422,
        )


class NoticeNotPendingExceptionError(AppExceptionError):
    """Raised when approving/declining a notice that is not pending."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.NOTICE_NOT_PENDING,
            message="Only a pending notice can be approved or declined.",
            status_code=409,
        )
