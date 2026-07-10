from enum import Enum


class TaskStatus(Enum):

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    IN_PROCESS = "INPROCESS"
