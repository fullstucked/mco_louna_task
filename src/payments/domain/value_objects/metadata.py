from dataclasses import field
from typing import Self
from dataclasses import dataclass
from typing import Any

from shared.domain.errors import DomainTypeError
from shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True, repr=False)
class Metadata(ValueObject[dict[str, Any]]):
    """
    Metadata represents JSON object which stores additional info for Payment
    """

    meta: dict[str, Any] = field(metadata={"value_field": True})

    def __post_init__(self):
        if not self._rebuilding:
            ValueObject.__post_init__(self)

            if not isinstance(self.value, dict):
                raise DomainTypeError("Metadata must be a dictionary")

            if not all(isinstance(k, str) for k in self.value):
                raise DomainTypeError("Not each field serializable")

    @classmethod
    def rebuild(  # pyrefly: ignore [bad-override]
        cls,
        meta: dict[str, Any],
    ) -> Self:
        obj = cls(
            meta=meta,
            _rebuilding=True,
        )
        return obj
