import re
from dataclasses import dataclass, field
from typing import Self

from shared.domain.errors import DomainValidationError
from shared.domain.value_object import ValueObject

MIN_LENTH = 3
MAX_LENTH = 50

# Except any carriage symbols
VALID_PATTERN = r"^[^\n\r\t\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]*$"

# To show user wrong symbol
INVALID_PATTERN = r"[\n\r\t\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]"


@dataclass(frozen=True, slots=True, repr=True)
class Description(ValueObject[str]):
    text: str = field(metadata={"value_field": True})

    def __post_init__(self):
        if not self._rebuilding:
            ValueObject.__post_init__(self)
            self._validate_lenth()
            self._validate_pattern()

    def _validate_lenth(self):
        if len(self.value) > MAX_LENTH or len(self.value) < MIN_LENTH:
            raise DomainValidationError(
                message="Wrong description lenth",
                context={
                    "details": f"Description lenth = {len(self.value)} must be in [{MIN_LENTH}, {MAX_LENTH}] constraints"
                },
            )

    def _validate_pattern(self):
        if not bool(re.match(VALID_PATTERN, self.value)):
            match = re.search(INVALID_PATTERN, self.value)

            if match:
                char = match.group()
                position = match.start()

                raise DomainValidationError(
                    message="Description contains invalid characters",
                    context={
                        "details": f"Description = {self.value} contains invalid characters at pos={position}, char={char}"
                    },
                )
            else:
                raise DomainValidationError(
                    message="Description contains invalid characters",
                    context={
                        "details": f"Description = {self.value} contains invalid characters"
                    },
                )

    @classmethod
    def rebuild(
        cls,
        text: str,
    ) -> Self:
        obj = cls(
            text=text,
            _rebuilding=True,
        )
        return obj
