from typing import Self
from dataclasses import dataclass, field
from datetime import datetime, timezone

from shared.domain.errors import DomainTypeError
from shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class Timestamp(ValueObject[datetime]):
    """
    Represent datetime object, timezone awared
    """

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
        metadata={"value_field": True},
    )

    def __post_init__(self):
        if not self._rebuilding:
            ValueObject.__post_init__(self)

            # Type ensure
            if not isinstance(self.value, datetime):
                raise DomainTypeError("Timestamp must be datetime")

            # Timezone awareness
            if self.value.tzinfo is None:
                raise DomainTypeError("Timestamp must be timezone-aware")

    @classmethod
    def now(cls) -> "Timestamp":
        """Return Timestamp obj with current datetime"""
        return cls(datetime.now(timezone.utc))

    def iso(self) -> str:
        """Returns datetime in iso format"""
        return self.value.isoformat()

    @classmethod
    def rebuild(
        cls,
        timestamp: datetime,
    ) -> Self:
        obj = cls(
            timestamp=timestamp,
            _rebuilding=True,
        )
        return obj
