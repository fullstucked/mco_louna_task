from abc import ABC, abstractmethod
from typing import Any, Dict

from payments.domain.enums.status import PaymentStatus
from payments.domain.events import PaymentProcessedEvent


class PayloadStrategy(ABC):
    """Abstract strategy for building notification payloads."""

    @abstractmethod
    def build(self, event: PaymentProcessedEvent) -> Dict[str, Any]:
        """Build payload for the given event."""
        ...


class ConfirmedPayloadStrategy(PayloadStrategy):
    """Payload strategy for CONFIRMED payments."""

    def build(self, event: PaymentProcessedEvent) -> Dict[str, Any]:
        return {
            "payment_id": str(event.payment_id),
            "status": event.status.value,
            "amount": str(event.amount),
            "currency": event.currency.value,
        }


class FailurePayloadStrategy(PayloadStrategy):
    """Payload strategy for FAILED/PENDING/other statuses."""

    def __init__(self, default_reason: str = "Internal error"):
        self.default_reason = default_reason

    def build(self, event: PaymentProcessedEvent) -> Dict[str, Any]:
        return {
            "payment_id": str(event.payment_id),
            "status": event.status.value,
            "reason": event.reason or self.default_reason,
        }


class PayloadStrategyFactory:
    """Factory for selecting the appropriate payload strategy."""

    _strategies = {
        PaymentStatus.CONFIRMED: ConfirmedPayloadStrategy(),
    }

    _default_strategy = FailurePayloadStrategy()

    @classmethod
    def get_strategy(cls, status: PaymentStatus) -> PayloadStrategy:
        return cls._strategies.get(status, cls._default_strategy)
