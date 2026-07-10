from shared.domain.errors import DomainTypeError
from shared.domain.value_object import ValueObject
import os
import pytest
from decimal import Decimal
from enum import Enum
from uuid import UUID
from dataclasses import dataclass, field

# ===== TEST FIXTURES & HELPERS =====


class Color(Enum):
    RED = "red"
    BLUE = "blue"


@dataclass(frozen=True, slots=True, kw_only=True)
class Money(ValueObject):
    """Simple value object with single value field"""

    amount: Decimal = field(metadata={"value_field": True})

    @classmethod
    def rebuild(cls, **kwargs):
        return cls(**kwargs)


@dataclass(frozen=True, slots=True, kw_only=True)
class UserId(ValueObject):
    """Value object with UUID"""

    id: UUID = field(metadata={"value_field": True})

    @classmethod
    def rebuild(cls, **kwargs):
        return cls(**kwargs)


@dataclass(frozen=True, slots=True, kw_only=True)
class Address(ValueObject):
    """Value object with multiple fields"""

    street: str = field(metadata={"value_field": True})
    city: str = field(metadata={"value_field": True})
    postal_code: str = field(metadata={"value_field": True})

    @classmethod
    def rebuild(cls, **kwargs):
        return cls(**kwargs)


@dataclass(frozen=True, slots=True, kw_only=True)
class Product(ValueObject):
    """Value object with enum"""

    name: str = field(metadata={"value_field": True})
    color: Color = field(metadata={"value_field": True})

    @classmethod
    def rebuild(cls, **kwargs):
        return cls(**kwargs)


# ===== TESTS =====


class TestValueObjectInstantiation:
    """Test creating valid value object instances"""

    def test_create_simple_value_object(self):
        money = Money(amount=Decimal("100.50"))
        assert money.amount == Decimal("100.50")

    def test_create_uuid_value_object(self):
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        user_id = UserId(id=test_uuid)
        assert user_id.id == test_uuid

    def test_create_multi_field_value_object(self):
        addr = Address(street="123 Main", city="Anytown", postal_code="12345")
        assert addr.street == "123 Main"
        assert addr.city == "Anytown"

    def test_create_enum_value_object(self):
        product = Product(name="Widget", color=Color.RED)
        assert product.name == "Widget"
        assert product.color == Color.RED


class TestValueObjectImmutability:
    """Test that value objects are truly immutable"""

    def test_cannot_modify_after_creation(self):
        money = Money(amount=Decimal("50"))
        with pytest.raises(AttributeError, match="cannot assign to field"):
            money.amount = Decimal("100")

    def test_cannot_modify_multi_field_object(self):
        addr = Address(street="123 Main", city="Anytown", postal_code="12345")
        with pytest.raises(AttributeError, match="cannot assign to field"):
            addr.street = "456 Oak"


class TestValueObjectDevChecks:
    """Test dev-mode validation checks"""

    @pytest.fixture(autouse=True)
    def set_dev_mode(self):
        """Set ENV to DEV for these tests"""
        os.environ["ENV"] = "DEV"
        yield
        # Cleanup
        if "ENV" in os.environ:
            del os.environ["ENV"]

    def test_cannot_instantiate_base_class_directly(self):
        with pytest.raises(DomainTypeError, match="base directly"):
            ValueObject(_rebuilding=False)

    def test_subclass_with_no_value_fields_fails(self):
        with pytest.raises(DomainTypeError, match="must define at least one field"):

            @dataclass(frozen=True, slots=True, kw_only=True)
            class Empty(ValueObject):
                @classmethod
                def rebuild(cls, **kwargs):
                    return cls(**kwargs)

            Empty()

    def test_mutable_field_raises_error(self):
        with pytest.raises(DomainTypeError, match="must be immutable"):

            @dataclass(frozen=True, slots=True, kw_only=True)
            class BadVO(ValueObject):
                items: list = field(metadata={"value_field": True})

                @classmethod
                def rebuild(cls, **kwargs):
                    return cls(**kwargs)

            BadVO(items=[1, 2, 3])

    def test_mutable_dict_field_raises_error(self):
        with pytest.raises(DomainTypeError, match="must be immutable"):

            @dataclass(frozen=True, slots=True, kw_only=True)
            class BadVO2(ValueObject):
                data: dict = field(metadata={"value_field": True})

                @classmethod
                def rebuild(cls, **kwargs):
                    return cls(**kwargs)

            BadVO2(data={"key": "value"})


class TestValueProperty:
    """Test the value property"""

    def test_single_value_field_extraction(self):
        money = Money(amount=Decimal("75.25"))
        assert money.value == Decimal("75.25")

    def test_no_marked_value_fields_returns_first_real_field(self):
        """When no fields marked as value_field, should return first non-_rebuilding field"""

        @dataclass(frozen=True, slots=True, kw_only=True)
        class UnmarkedVO(ValueObject):
            name: str

            @classmethod
            def rebuild(cls, **kwargs):
                return cls(**kwargs)

        vo = UnmarkedVO(name="Test")
        # Should return the first real field (name) since none are marked
        assert vo.value == "Test"


class TestRebuild:
    """Test the rebuild classmethod"""

    def test_rebuild_simple_object(self):
        original = Money(amount=Decimal("100"))
        rebuilt = Money.rebuild(amount=Decimal("100"))
        assert rebuilt == original

    def test_rebuild_multi_field_object(self):
        rebuilt = Address.rebuild(street="789 Oak", city="NewCity", postal_code="54321")
        assert rebuilt.street == "789 Oak"
        assert rebuilt.city == "NewCity"
        assert rebuilt.postal_code == "54321"

    def test_rebuild_preserves_type(self):
        rebuilt = UserId.rebuild(id=UUID("87654321-4321-8765-4321-876543218765"))
        assert isinstance(rebuilt, UserId)
        assert isinstance(rebuilt.id, UUID)


class TestRepr:
    """Test custom __repr__ implementation"""

    def test_repr_single_field(self):
        money = Money(amount=Decimal("50.99"))
        # Should show the amount since it's marked repr=True by default
        assert "Money" in repr(money)
        assert "50.99" in repr(money)

    def test_repr_multi_field(self):
        addr = Address(street="123 Main", city="Springfield", postal_code="12345")
        repr_str = repr(addr)
        assert "Address" in repr_str
        assert "123 Main" in repr_str
        assert "Springfield" in repr_str

    def test_repr_with_enum(self):
        product = Product(name="Item", color=Color.RED)
        repr_str = repr(product)
        assert "Product" in repr_str


class TestIsMutable:
    """Test the _is_mutable static helper"""

    def test_immutable_types(self):
        assert not ValueObject._is_mutable("string")
        assert not ValueObject._is_mutable(42)
        assert not ValueObject._is_mutable(3.14)
        assert not ValueObject._is_mutable(Decimal("10"))
        assert not ValueObject._is_mutable(UUID("00000000-0000-0000-0000-000000000000"))
        assert not ValueObject._is_mutable(True)
        assert not ValueObject._is_mutable(None)
        assert not ValueObject._is_mutable(frozenset([1, 2]))

    def test_immutable_enum(self):
        assert not ValueObject._is_mutable(Color.RED)

    def test_frozen_dataclass_is_immutable(self):
        money = Money(amount=Decimal("100"))
        assert not ValueObject._is_mutable(money)

    def test_mutable_types(self):
        assert ValueObject._is_mutable([1, 2, 3])
        assert ValueObject._is_mutable({"key": "value"})
        assert ValueObject._is_mutable({1, 2, 3})

    def test_non_frozen_dataclass_is_mutable(self):
        @dataclass(slots=True, kw_only=True)
        class Mutable:
            value: int

        mutable = Mutable(value=10)
        assert ValueObject._is_mutable(mutable)


class TestValueObjectEquality:
    """Test equality behavior (default dataclass behavior)"""

    def test_same_values_are_equal(self):
        money1 = Money(amount=Decimal("100"))
        money2 = Money(amount=Decimal("100"))
        assert money1 == money2

    def test_different_values_not_equal(self):
        money1 = Money(amount=Decimal("100"))
        money2 = Money(amount=Decimal("200"))
        assert money1 != money2

    def test_hashable(self):
        money = Money(amount=Decimal("100"))
        # Frozen dataclasses are hashable by default
        assert hash(money) is not None

        # Can use in set
        money_set = {money}
        assert money in money_set
