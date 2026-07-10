from typing import cast
import os
from abc import ABC
from dataclasses import Field, dataclass, field, fields
from decimal import Decimal
from enum import Enum
from typing import Generic, Self, TypeVar, final
from uuid import UUID

from shared.domain.errors import DomainTypeError

V = TypeVar("V")


@dataclass(frozen=True, slots=True, kw_only=True)
class ValueObject(ABC, Generic[V]):
    """
    Base class for immutable value objects.
    In implementations should force frosen=True and explictly declare `rebuild` method
    Current base class have no fields, so it uses gettattr and setattr to implement intenional behavior
    """

    _rebuilding: bool = field(default=False, init=True, repr=False)

    def __post_init__(self):

        # ---------------------------------------------------------
        # DEV-CHECKS
        # ---------------------------------------------------------
        if os.getenv("ENV") == "DEV":

            if type(self) is ValueObject:
                raise DomainTypeError(
                    message="Attempt to instantiate ValueObject base directly",
                )

            fs: tuple[Field[bool | V]] = fields(  # pyrefly: ignore [bad-assignment]
                self
            )
            if len(fs) < 2:  # 1st field is _rebuilding flag
                raise DomainTypeError(
                    message=f"{type(self).__name__} must define at least one field",
                )

            for f in fs:
                value = getattr(self, f.name)
                if self._is_mutable(value):
                    raise DomainTypeError(
                        message=f"Field '{f.name}' in {type(self).__name__} must be immutable"
                    )

    @classmethod
    def rebuild(cls, **kwargs: V) -> Self:
        """Rebuild a value object from "Source of Truth" bypassing invariants."""

        raise NotImplementedError("Instances should implement their own rebuild")

    # ---------------------------------------------------------
    # Properties
    # ---------------------------------------------------------

    @property
    @final
    def value(self) -> V:
        for f in fields(self):
            if f.metadata.get("value_field"):
                return getattr(self, f.name)

        return getattr(self, fields(self)[1].name)

    def __repr__(self):
        cls = type(self).__name__
        visible = [(f.name, getattr(self, f.name)) for f in fields(self) if f.repr]

        if not visible:
            return f"{cls}(<hidden>)"

        if len(visible) == 1:
            return f"{cls}({visible[0][1]!r})"

        args = ", ".join(f"{k}={v!r}" for k, v in visible)
        return f"{cls}({args})"

    def __eq__(self, other: object) -> bool:
        return self.value == cast(Self, other).value

    @staticmethod  # NOT USES IN PROD - DEV-ONLY
    def _is_mutable(val: V) -> bool:
        """Check if a value is mutable by type, not by attempting mutation."""
        IMMUTABLE_TYPES = (str, int, float, Decimal, UUID, bool, type(None), frozenset)
        if isinstance(val, IMMUTABLE_TYPES):
            return False
        if isinstance(val, Enum):
            return False
        if hasattr(val, "__frozen__") or hasattr(val, "__dataclass_fields__"):
            # Check if it's a frozen dataclass
            try:

                return (
                    not val.__dataclass_params__.frozen  # pyrefly: ignore [missing-attribute]
                )
            except:  # noqa: E722
                pass
        return True  # Assume mutable if uncertain
