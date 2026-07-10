import os
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, Hashable, Self, Sequence, TypeVar, cast

from .entity import Entity
from .errors import DomainTypeError
from .event import DomainEvent
from .value_object import ValueObject

ID = TypeVar("ID", bound=Hashable)
VO = TypeVar("VO", bound=ValueObject | None)
EVENT = TypeVar("EVENT", bound=DomainEvent | None)
ENTITY = TypeVar("ENTITY", bound=Entity | None)


@dataclass(slots=True, kw_only=True, eq=False)
class Aggregate(Generic[ID, EVENT, VO, ENTITY]):
    """
    Event-drivent Domain Aggregate

    Inherited classes should also use
    `__slots__`

    attributes:
    `id` - `hashable` object identifier
    `_events` - list of `DomainEvent`

    Note: Field type validation only runs in DEV environment.
    """

    id: ID
    _events: list[EVENT] = field(default_factory=list)
    _rebuilding: bool = field(default=False, init=True, repr=False)

    def __post_init__(self):
        """
        Invariant validation
        """

        # ---------------------------------------------------------
        # DEV-CHECKS
        # ---------------------------------------------------------
        if os.getenv("ENV") == "DEV":
            if type(self) is Aggregate:
                raise DomainTypeError(
                    message="Attempt to instantiate Aggregate base directly",
                )
            self._validate_field_types()

    def _validate_field_types(self):
        """
        Checks that every fields inherited from
                [`Value Object`|| `DomainEvent` || `Enum` || `Entity`]
            or exposed as Enum
            except id - it must be `Hashable` only
        """
        for attr in dir(self):
            if not callable(getattr(self, attr)) and not attr == "id":
                field = getattr(self, attr)

                if isinstance(field, Sequence):  # deep check
                    for el in field:
                        if not isinstance(
                            el, ValueObject | Enum | DomainEvent | Entity
                        ):
                            raise DomainTypeError(
                                message="Aggregate attribute must be descendant of Value Object class in Sequences too",
                                context={
                                    "details": f"Attempt to pass inappropriate obj in {self.__class__}.",
                                },
                            )

                elif not isinstance(
                    field, ValueObject | Enum | Entity
                ):  # for non-sequence fields
                    raise DomainTypeError(
                        message="Aggregate attribute must be descendant of Value Object class",
                        context={
                            "details": f"Attempt to pass non-VO in {self.__class__}.",
                        },
                    )

    # ---------------------------------------------------------
    # Behavior
    # ---------------------------------------------------------

    @classmethod
    @abstractmethod
    def rebuild(
        cls,
        id: ID,
        events: list[EVENT] = [],  # optional fetching events from event-presistence
        **kwargs: ValueObject | Entity | Enum,
    ) -> Self:
        """
        Rebuild an `Aggregate` from "Source of Truth" bypassing any invariants
        except `ValueObject`'s - they should be rebuilded using their own methods
        """

        raise NotImplementedError("Instances should implement their own rebuild")

    # ---------------------------------------------------------
    # Properties
    # ---------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        """
        Two aggregates are considered equal if they have the same `id`,
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
                message="Changing aggregate ID is not permitted",
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

    # ---------------------------------------------------------
    # Events
    # ---------------------------------------------------------

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
