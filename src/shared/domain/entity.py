from abc import abstractmethod
import os
from dataclasses import field
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Hashable, Self, Sequence, TypeVar, cast

from .errors import DomainTypeError
from .event import DomainEvent
from .value_object import ValueObject

### Generics
ID = TypeVar("ID", bound=Hashable)
VO = TypeVar("VO", bound=ValueObject)
EVENT = TypeVar("EVENT", bound=DomainEvent | None)


@dataclass(slots=True, kw_only=True)
class Entity(Generic[ID, VO, EVENT]):
    """
    Base class for domain entities, defined by a unique (`id`).
    - `id`: Identity that remains constant throughout the entity's life cycle.
    - Entities are mutable, but are compared solely by their `id`.
    - accessible through keywords only for strict rebuilds and field access
    """

    id: ID
    _events: list[EVENT]
    _rebuilding: bool = field(default=False, init=True, repr=False)

    def __post_init__(self):
        """
        Invariant validation here
        """
        if not self._rebuilding:
            # ---------------------------------------------------------
            # DEV-CHECKS
            # ---------------------------------------------------------
            if os.getenv("ENV") == "DEV":
                if type(self) is Entity:
                    raise DomainTypeError(
                        message="Attempt to instantiate Aggregate base directly",
                    )
                self._validate_field_types()

    def _validate_field_types(self):
        """
        Checks that every fields inherited from
                [`Value Object`|| `DomainEvent` || `Enum`]
            or exposed as Enum
            except id - it must be `Hashable` only
        """
        for attr in dir(self):
            if not callable(getattr(self, attr)) and not attr == "id":
                field = getattr(self, attr)

                if isinstance(field, Sequence):  # deep check
                    for el in field:
                        if not isinstance(el, ValueObject | Enum | DomainEvent):
                            raise DomainTypeError(
                                message="Entity attribute must be descendant of Value Object class in Sequences too",
                                context={
                                    "details": f"Attempt to pass inappropriate obj in {self.__class__}.",
                                },
                            )

                elif not isinstance(
                    self, ValueObject | Enum
                ):  # for non-sequence fields
                    raise DomainTypeError(
                        message="Entity attribute must be descendant of Value Object class",
                        context={
                            "details": f"Attempt to pass non-VO in {self.__class__}.",
                        },
                    )

    @classmethod
    @abstractmethod
    def rebuild(
        cls,
        id: ID,
        events: list[EVENT] = [],  # optional fetching events from event-presistence
        **kwargs: ValueObject | Enum,
    ) -> Self:
        """
        Rebuild an `Entity` from "Source of Truth" bypassing any invariants
        except `ValueObject`'s - they should be rebuilded using their own methods
        """

        raise NotImplementedError("Instances should implement their own rebuild")

    # ---------------------------------------------------------
    # Properties
    # ---------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        """
        Two entities are considered equal if they have the same `id`,
        regardless of other attribute values.
        """
        return type(self) is type(other) and cast(Self, other).id == self.id

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Prevents modifying the `id` after it's set.
        Other attributes can be changed as usual.
        """
        if name == "id" and getattr(self, "id", None) is not None:
            raise DomainTypeError(
                message="Changing entity ID is not permitted",
                context={
                    "details": f"Attempt to rewrite ID in {self.__class__}.",
                },
            )
        object.__setattr__(self, name, value)

    def __hash__(self) -> int:
        """
        Generate a hash based on entity type and the immutable `id`.
        This allows entities to be used in hash-based collections and
        reduces the risk of hash collisions between different entity types.
        """
        return hash((type(self), self.id))

    def __repr__(self) -> str:
        return f"<{type(self).__name__}(id={self.id!r})>"

    def record_event(self, event: EVENT) -> None:
        """Record a domain event that occurred inside this aggregate."""
        self._events.append(event)

    def pull_events(self) -> list[EVENT]:
        """
        Return and clear all recorded events.
        """
        events = self._events.copy()
        self._events.clear()
        return events
