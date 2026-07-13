from enum import Enum


class PaymentStatus(Enum):
    """
    Enumeration of payment processing states.

    Members:
        PENDING: Payment created but not yet processed by gateway.
                 Initial state for all new payments.
                 Awaiting processing or gateway response.

        CONFIRMED: Payment successfully processed and charged.
                   Final state indicating funds were captured/authorized.
                   Funds have been received or will be received.

        FAILED: Payment processing failed.
                Final state indicating the transaction was rejected.
                Possible reasons: insufficient funds, card declined,
                network error, fraud check failure, etc.
                May be retried by the client with a new idempotency key.
    """

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
