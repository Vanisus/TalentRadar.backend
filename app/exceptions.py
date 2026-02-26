from typing import Any, Optional


class DomainError(Exception):
    """
    Базовый класс для доменных ошибок.
    Не знает про HTTP, только про бизнес-логику.
    """

    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class ValidationError(DomainError):
    pass

class BadRequestError(DomainError):
    pass