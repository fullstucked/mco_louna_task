from dataclasses import dataclass, field
from typing import Self
from uuid import UUID

from shared.domain.errors import DomainTypeError
from shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True, repr=False)
class IdempotencyKey(ValueObject[UUID]):
    """
    Payment Idemporency key should prevent duplicates
    """

    key: UUID = field(metadata={"value_field": True})

    def __post_init__(self) -> None:
        if not self._rebuilding:
            ValueObject.__post_init__(self)

            # Ensure that ID represened as UUID4
            if self.value.version != 4:
                raise DomainTypeError(
                    message="IdempotencyKey must be UUID v4",
                    context={"provided_version": self.value.version},
                )

    @classmethod
    def rebuild(  # pyrefly: ignore [bad-override]
        cls,
        key: UUID,
    ) -> Self:
        obj = cls(
            key=key,
            _rebuilding=True,
        )
        return obj
