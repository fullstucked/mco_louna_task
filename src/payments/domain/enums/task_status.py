from enum import Enum


class TaskStatus(Enum):
    """
    Event delivery state in outbox pattern.

    PENDING: Awaiting publication to broker.
    CONFIRMED: Successfully published and acknowledged by broker.
    FAILED: Publish attempt exhausted retries; moved to dead-letter.
    IN_PROCESS: Publication in progress.
    """

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    IN_PROCESS = "INPROCESS"
