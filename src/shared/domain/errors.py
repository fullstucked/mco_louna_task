from typing import Any

from .enums.scope import Scope


class DomainError(Exception):
    """
    Base class for all domain-specific errors.
    """

    message: str
    scope: Scope
    context: dict[str, Any]

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        scope: Scope = Scope.private,
    ) -> None:
        super().__init__(message)
        self.message = message  # To access explictly without self.args[0]
        self.scope = scope
        self.context = context or {}
        self.context.setdefault("status", 400)

    def __repr__(self) -> str:
        ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        return f"{self.__class__.__name__}(message={self.message!r}, scope={self.scope!r}, context={{{ctx if self.scope == Scope.public else {}}}})"

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "scope": self.scope,
            "context": self.context,
        }


class DomainInvariantError(DomainError):
    """Raised when a domain invariant is violated."""

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        scope: Scope = Scope.private,
    ) -> None:
        super().__init__(message, context)
        self.scope = scope
        self.context["status"] = 422


class DomainValidationError(DomainError):
    """Raised when validation of a value object fails."""

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        scope: Scope = Scope.private,
    ) -> None:
        super().__init__(message, context)
        self.scope = scope
        self.context["status"] = 422


class DomainTypeError(DomainError):
    """Raised when a value has incorrect type or format."""

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        scope: Scope = Scope.private,
    ) -> None:
        super().__init__(message, context)
        self.scope = scope
        self.context["status"] = 422


class DomainBusinessRuleError(DomainInvariantError):
    """Raised when a business rule is violated."""

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        scope: Scope = Scope.private,
    ) -> None:
        super().__init__(message, context)
        self.scope = scope
        self.context["status"] = 422


class DomainResourceNotFoundError(DomainError):
    """Raised when a domain resource is not found."""

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        scope: Scope = Scope.private,
    ) -> None:
        super().__init__(message, context)
        self.scope = scope

        self.context["status"] = 404


class DomainResourceExistsError(DomainError):
    """Raised at attempt to create already existing uinque domain resource."""

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        scope: Scope = Scope.private,
    ) -> None:
        super().__init__(message, context)
        self.scope = scope

        self.context["status"] = 403
