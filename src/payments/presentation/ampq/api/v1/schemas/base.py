from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class EventData(BaseModel, Generic[T]):
    id: str
    occurred_at: str
    queue: str
    payload: T


def event(cls: type[T]) -> type[EventData[T]]:
    """Convert data model to EventSchema class"""
    return EventData[cls]
