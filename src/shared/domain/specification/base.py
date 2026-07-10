from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Generic, Iterator, TypeVar

SPEC = TypeVar("SPEC", bound="BaseSpecification")


@dataclass(frozen=True, slots=True, repr=True)
class BaseSpecification(ABC, Generic[SPEC]):
    """
    Base class for each entity-related field
    Defines &&;||;! methods to bulk search in spec

    Implementation should explictly define logical operations to seek for satisfied result
    """

    def __and__(self, other: SPEC) -> BaseSpecification[SPEC]:
        return AndSpecification(self, other)

    def __or__(self, other: SPEC) -> BaseSpecification[SPEC]:
        return OrSpecification(self, other)

    def __not__(self) -> BaseSpecification[SPEC]:
        return NotSpecification(self)

    def get_leaf_specifications(self) -> Iterator[BaseSpecification[SPEC]]:
        """Recursively yield all leaf (non-composite) specifications"""
        if isinstance(self, (AndSpecification, OrSpecification)):
            yield from self.left.get_leaf_specifications()
            yield from self.right.get_leaf_specifications()
        elif isinstance(self, NotSpecification):
            yield from self.spec.get_leaf_specifications()
        else:
            yield self

    def is_composite(self) -> bool:
        """Check if this is a composite specification"""
        return isinstance(self, (AndSpecification, OrSpecification, NotSpecification))


@dataclass(frozen=True, slots=True, repr=False)
class AndSpecification(BaseSpecification, Generic[SPEC]):
    left: SPEC
    right: SPEC


@dataclass(frozen=True, slots=True, repr=False)
class OrSpecification(BaseSpecification, Generic[SPEC]):
    left: SPEC
    right: SPEC


@dataclass(frozen=True, slots=True, repr=False)
class NotSpecification(BaseSpecification, Generic[SPEC]):
    spec: SPEC
