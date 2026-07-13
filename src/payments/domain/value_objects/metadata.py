from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Self

from shared.domain.errors import DomainTypeError
from shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True, repr=True)
class Metadata(ValueObject[MappingProxyType[str, Any]]):
    """
    Represents immutable metadata as a read-only dictionary of JSON-serializable values.

    Wraps arbitrary JSON-compatible data (strings, numbers, booleans, lists, dicts)
    as an immutable MappingProxyType.
    All keys must be strings to ensure JSON serialization compatibility.

    Attributes:
        meta: dict[str, Any] | MappingProxyType[str, Any]
            Additional metadata for a payment. Accepts plain dicts on input
            (automatically converted to MappingProxyType) or existing MappingProxyType
            objects. All keys must be strings.

    Raises:
        DomainTypeError: If meta is not a dict/MappingProxyType, or if any
                         key is not a string.

    """

    meta: dict[str, Any] | MappingProxyType[str, Any] = field(
        metadata={"value_field": True}
    )

    def __post_init__(self):
        """
        Initialize Metadata, validating that:
        1. meta is a dict or MappingProxyType
        2. All keys are strings (for JSON serialization)
        3. Convert plain dicts to immutable MappingProxyType
        """
        if not self._rebuilding:
            # Validate type
            if not isinstance(self.meta, (dict, MappingProxyType)):
                raise DomainTypeError("Metadata must be a dictionary")

            # Validate keys are strings (before conversion)
            if not all(isinstance(k, str) for k in self.meta.keys()):
                raise DomainTypeError("Not each field serializable")

            # Explict convertion
            if isinstance(self.meta, dict) and not isinstance(
                self.meta, MappingProxyType
            ):
                object.__setattr__(self, "meta", MappingProxyType(self.meta))

            ValueObject.__post_init__(self)

    @classmethod
    def rebuild(
        cls,
        meta: dict[str, Any],
    ) -> Self:
        obj = cls(
            meta=MappingProxyType(meta),
            _rebuilding=True,
        )
        return obj
