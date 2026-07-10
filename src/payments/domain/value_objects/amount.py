from dataclasses import dataclass, field
from decimal import Decimal
from typing import Self

from shared.domain.errors import DomainTypeError, DomainValidationError
from shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True, repr=True, eq=False)
class Amount(ValueObject[Decimal]):
    """
    Class represent imutable count of money which should be processed
    via gatway;
    `Decimal` for precise value
    """

    amount: Decimal = field(metadata={"value_field": True})

    def __post_init__(self) -> None:
        if not self._rebuilding:
            ValueObject.__post_init__(self)

            # Ensure value is Decimal
            if not isinstance(self.value, Decimal):
                raise DomainTypeError("Amount must be a Decimal")

            # Greater than zero
            if self.value <= Decimal("0"):
                raise DomainValidationError("Amount must be greater than zero")

            # Max 2 decimal places
            exponent = int(self.value.as_tuple().exponent)
            if exponent < -2:
                raise DomainValidationError(
                    "Amount cannot have more than 2 decimal places"
                )

    @classmethod
    def rebuild(  # pyrefly: ignore [bad-override]
        cls,
        amount: Decimal,
    ) -> Self:
        obj = cls(
            amount=amount,
            _rebuilding=True,
        )
        return obj
