from dataclasses import field
from typing import Self
from dataclasses import dataclass
from urllib.parse import urlparse

from validators import url as url_validate

from shared.domain.errors import DomainValidationError
from shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True, repr=False)
class WebhookUrl(ValueObject[str]):
    """
    Represents URL which should accept notifications about payment changes
    """

    url: str = field(metadata={"value_field": True})

    def __post_init__(self) -> None:

        if not self._rebuilding:
            ValueObject.__post_init__(self)
            parsed = urlparse(self.value)

            # Protocol ensuring
            if parsed.scheme not in ("http", "https"):
                raise DomainValidationError("Webhook URL must be http or https")

            # Local network violation prevention
            if parsed.hostname in ("localhost", "127.0.0.1"):
                raise DomainValidationError("Webhook URL cannot point to localhost")

            # Complex validation ig host not startswith `-` for ex
            if not url_validate(self.value):
                raise DomainValidationError("Webhook URL must be valid")

    @classmethod
    def rebuild(  # pyrefly: ignore [bad-override]
        cls,
        url: str,
    ) -> Self:
        obj = cls(
            url=url,
            _rebuilding=True,
        )
        return obj
