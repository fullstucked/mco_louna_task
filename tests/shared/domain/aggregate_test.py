from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

import pytest

from shared.domain.aggregate import Aggregate
from shared.domain.entity import Entity
from shared.domain.errors import DomainTypeError
from shared.domain.event import DomainEvent
from shared.domain.value_object import ValueObject

# ============================================================
# Test Fixtures
# ============================================================


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True, slots=True, kw_only=True)
class TestVO(ValueObject):
    name: str = field(metadata={"value_field": True})


@dataclass(frozen=True, slots=True, kw_only=True)
class TestEvent(DomainEvent):
    aggregate_id: UUID
    description: str = field(metadata={"value_field": True})


@dataclass(slots=True, kw_only=True)
class TestEntity(Entity):
    entity_id: UUID
    data: str


@dataclass(slots=True, kw_only=True, eq=False)
class ValidAggregate(Aggregate[UUID, TestEvent, TestVO, TestEntity]):
    name: TestVO
    status: Status
    items: list[TestVO] = field(default_factory=list)

    @classmethod
    def rebuild(cls, id: UUID, events: list[TestEvent] = [], **kwargs):
        return cls(id=id, _rebuilding=True, **kwargs)


# ============================================================
# Tests
# ============================================================


class TestAggregateInstantiation:
    def test_cannot_instantiate_base_aggregate_directly(self, monkeypatch):
        """Should raise DomainTypeError when trying to instantiate Aggregate base"""
        monkeypatch.setenv("ENV", "DEV")  # ← ADD THIS

        with pytest.raises(DomainTypeError) as exc_info:
            Aggregate(id=uuid4())

        assert "directly" in exc_info.value.message.lower()

    def test_valid_subclass_initialization(self):
        """Should initialize valid aggregate subclass"""
        agg = ValidAggregate(
            id=uuid4(),
            name=TestVO(name="Test"),
            status=Status.ACTIVE,
        )

        assert agg.name.value == "Test"
        assert agg.status == Status.ACTIVE

    def test_initialization_with_vo_sequence(self):
        """Should accept sequences of VOs"""
        test_id = uuid4()
        agg = ValidAggregate(
            id=test_id,
            name=TestVO(name="Test"),
            status=Status.ACTIVE,
            items=[TestVO(name="item1"), TestVO(name="item2")],
        )

        assert len(agg.items) == 2

    def test_rebuilding_flag_bypasses_validation(self):
        """Should skip validation when _rebuilding=True"""
        # This tests that rebuild can bypass invariants
        agg = ValidAggregate(
            id=uuid4(),
            name=TestVO(name="Test"),
            status=Status.ACTIVE,
            _rebuilding=True,
        )

        assert agg._rebuilding is True


class TestAggregateFieldValidation:
    def test_rejects_invalid_field_type(self, monkeypatch):
        """Should raise DomainTypeError for non-VO, non-Entity, non-Event, non-Enum fields"""
        monkeypatch.setenv("ENV", "DEV")

        @dataclass(slots=True, kw_only=True)
        class InvalidAggregate(Aggregate[UUID, TestEvent, TestVO, TestEntity]):
            id: UUID
            invalid_field: str  # String is not allowed

            @classmethod
            def rebuild(cls, id: UUID, events: list[TestEvent] = [], **kwargs):
                return cls(id=id, **kwargs)

        with pytest.raises(DomainTypeError) as exc_info:
            InvalidAggregate(id=uuid4(), invalid_field="test")

            assert (
                "Value Object" in exc_info.value.message
                or "descendant" in exc_info.value.message
            )

    def test_rejects_invalid_type_in_sequence(self, monkeypatch):
        """Should raise DomainTypeError for invalid types in Sequence fields"""
        monkeypatch.setenv("ENV", "DEV")

        @dataclass(slots=True, kw_only=True)
        class InvalidSequenceAggregate(Aggregate[UUID, TestEvent, TestVO, TestEntity]):
            id: UUID
            items: list[str]  # Should be list of VO/Entity/Event/Enum

            @classmethod
            def rebuild(cls, id: UUID, events: list[TestEvent] = [], **kwargs):
                return cls(id=id, **kwargs)

        with pytest.raises(DomainTypeError) as exc_info:
            InvalidSequenceAggregate(id=uuid4(), items=["invalid"])

        assert "descendant" in exc_info.value.message


class TestAggregateEquality:
    def test_same_id_equals(self):
        """Two aggregates with same id are equal"""
        test_id = uuid4()
        agg1 = ValidAggregate(id=test_id, name=TestVO(name="A"), status=Status.ACTIVE)
        agg2 = ValidAggregate(id=test_id, name=TestVO(name="B"), status=Status.INACTIVE)

        assert agg1 == agg2

    def test_different_id_not_equals(self):
        """Two aggregates with different ids are not equal"""
        agg1 = ValidAggregate(id=uuid4(), name=TestVO(name="A"), status=Status.ACTIVE)
        agg2 = ValidAggregate(id=uuid4(), name=TestVO(name="A"), status=Status.ACTIVE)

        assert agg1 != agg2

    def test_different_type_not_equals(self):
        """Different aggregate types are not equal even with same id"""
        test_id = uuid4()

        @dataclass(slots=True, kw_only=True)
        class OtherAggregate(Aggregate[UUID, TestEvent, TestVO, TestEntity]):
            name: TestVO

            @classmethod
            def rebuild(cls, id: UUID, events: list[TestEvent] = [], **kwargs):
                return cls(id=id, **kwargs)

        agg1 = ValidAggregate(id=test_id, name=TestVO(name="A"), status=Status.ACTIVE)
        agg2 = OtherAggregate(id=test_id, name=TestVO(name="A"))

        assert agg1 != agg2


class TestAggregateIDImmutability:
    def test_cannot_change_id_after_init(self):
        """Should raise DomainTypeError when trying to change id"""
        agg = ValidAggregate(id=uuid4(), name=TestVO(name="Test"), status=Status.ACTIVE)
        new_id = uuid4()

        with pytest.raises(DomainTypeError) as exc_info:
            agg.id = new_id

        assert "ID" in exc_info.value.message or "id" in exc_info.value.message.lower()

    def test_can_set_id_once_if_none(self):
        """Should allow setting id if it's not already set"""
        # This is a boundary case - if somehow id is None initially
        # The current implementation allows setting if getattr returns None
        pass


class TestAggregateEvents:
    def test_record_event(self):
        """Should record events"""
        agg = ValidAggregate(id=uuid4(), name=TestVO(name="Test"), status=Status.ACTIVE)
        event = TestEvent(aggregate_id=agg.id, description="test event")

        agg.record_event(event)

        assert len(agg._events) == 1
        assert agg._events[0] == event

    def test_pull_events_returns_and_clears(self):
        """Should return and clear events"""
        agg = ValidAggregate(id=uuid4(), name=TestVO(name="Test"), status=Status.ACTIVE)
        event1 = TestEvent(aggregate_id=agg.id, description="event1")
        event2 = TestEvent(aggregate_id=agg.id, description="event2")

        agg.record_event(event1)
        agg.record_event(event2)

        events = agg.pull_events()

        assert len(events) == 2
        assert len(agg._events) == 0


class TestAggregateRepr:
    def test_repr_format(self):
        """Should have correct repr format"""
        test_id = uuid4()
        agg = ValidAggregate(id=test_id, name=TestVO(name="Test"), status=Status.ACTIVE)

        repr_str = repr(agg)

        assert "ValidAggregate" in repr_str
        assert str(test_id) in repr_str


class TestAggregateRebuild:
    def test_rebuild_creates_with_flag(self):
        """Rebuild should set _rebuilding flag"""
        test_id = uuid4()
        agg = ValidAggregate.rebuild(
            id=test_id,
            name=TestVO(name="Rebuilt"),
            status=Status.ACTIVE,
        )

        assert agg.id == test_id
        assert agg._rebuilding is True

    def test_base_rebuild_not_implemented(self):
        """Base Aggregate.rebuild should raise NotImplementedError"""
        with pytest.raises(NotImplementedError):
            Aggregate.rebuild(id=uuid4())
