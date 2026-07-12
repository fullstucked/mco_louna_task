import os
from abc import ABC
from dataclasses import Field, dataclass, field, fields
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any, ClassVar, Generic, Self, TypeVar, cast, final
from uuid import UUID

from shared.domain.errors import DomainTypeError, DomainValidationError

V = TypeVar("V")


@dataclass(frozen=True, slots=True, kw_only=True)
class ValueObject(ABC, Generic[V]):
    """
    Base class for immutable value objects.

    Subclasses must:
    - Be decorated with @dataclass(frozen=True, slots=True, kw_only=True)
    - Implement the rebuild() classmethod for reconstructing from persistence
    - Mark their primary field with field(metadata={'value_field': True})

    Base Validation only runs in DEV mode and is skipped during rebuild operations.
    """

    _SAFE_TYPES: ClassVar[tuple[type[Any], ...]] = (
        str,
        int,
        float,
        bool,
        type(None),
        UUID,
        datetime,
        date,
        time,
        Decimal,
        frozenset,
        tuple,
        Enum,
        MappingProxyType,
    )

    _rebuilding: bool = field(default=False, init=True, repr=False)

    def __post_init__(self):

        # ---------------------------------------------------------
        # DEV-TIME CHECKS
        # ---------------------------------------------------------
        if os.getenv("ENV") == "DEV" and not self._rebuilding:

            # Check direct instantiation
            if type(self) is ValueObject:
                raise DomainTypeError(
                    message="Attempt to instantiate ValueObject base directly",
                )

            self._validate_fields()

    def _validate_fields(self):

        fs: tuple[Field[Any], ...] = fields(self)
        if len(fs) < 2:  # 1st field is _rebuilding flag
            raise DomainTypeError(
                message=f"{type(self).__name__} must be defined by at least one field",
            )

        for f in fs:
            # Skip internal fields
            if f.name.startswith("_"):
                continue

            value = getattr(self, f.name)

            if not isinstance(value, self._SAFE_TYPES):
                raise DomainTypeError(
                    message=f"{type(self).__name__}.{f.name} has unsafe type {type(value).__name__}"
                )

    @classmethod
    def rebuild(
        cls,
        *args,
        **kwargs,
    ) -> Self:
        """Rebuild a value object from "Source of Truth" bypassing invariants."""

        raise NotImplementedError("Instances should implement their own rebuild")

    # ---------------------------------------------------------
    # Properties
    # ---------------------------------------------------------

    @property
    @final
    def value(self) -> V:
        """return value of value object"""
        for f in fields(self):
            if f.metadata.get("value_field"):
                return getattr(self, f.name)

        raise DomainValidationError(
            f"{type(self).__name__} has no field marked with value_field=True. "
            "Mark your primary field with field(metadata={'value_field': True})"
        )

    def __repr__(self):
        cls = type(self).__name__
        visible = [(f.name, getattr(self, f.name)) for f in fields(self) if f.repr]

        if not visible:
            return f"{cls}(<hidden>)"

        args = ", ".join(f"{k}={v!r}" for k, v in visible)
        return f"{cls}({args})"

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.value == cast(Self, other).value
