from dataclasses import dataclass, field
from typing import Self
from uuid import UUID, uuid4

from shared.domain.errors import DomainTypeError
from shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True, repr=False)
class PaymentID(ValueObject[UUID]):
    """
    Represents a unique identifier for a payment transaction.

    This value object encapsulates a UUID v4 to ensure type safety and
    immutability when referencing payments throughout the domain.

    Attributes:
        id: UUID
            The UUID v4 value that uniquely identifies a payment.
            Automatically generated using uuid4() if not provided.

    Raises:
        DomainTypeError: If id is not a UUID instance or is not UUID v4.
    """

    id: UUID = field(default_factory=uuid4, metadata={"value_field": True})

    def __post_init__(self) -> None:
        if not self._rebuilding:
            ValueObject.__post_init__(self)

            if not isinstance(self.id, UUID):
                raise DomainTypeError(
                    message="PaymentID must be UUID(v4)",
                )
            # Ensure that ID represened as UUID4
            if self.value.version != 4:
                raise DomainTypeError(
                    message="PaymentID must be UUID v4",
                    context={"provided_version": self.value.version},
                )

    @classmethod
    def rebuild(
        cls,
        id: UUID,
    ) -> Self:
        obj = cls(
            id=id,
            _rebuilding=True,
        )
        return obj
