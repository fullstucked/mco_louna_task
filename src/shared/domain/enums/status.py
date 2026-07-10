from enum import Enum


class Status(str, Enum):
    PENDING = "pending"
    OK = "success"
    FAIL = "failed"
    IN_PROCESS = "in_process"
