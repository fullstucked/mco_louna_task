from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from uuid import UUID

import pytest

from shared.domain.errors import DomainTypeError, DomainValidationError
from shared.domain.value_object import ValueObject

# ============================================================================
# TEST FIXTURES / EXAMPLE VALUE OBJECTS
# ============================================================================


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


@dataclass(frozen=True, slots=True, kw_only=True)
class Money(ValueObject[Decimal]):
    amount: Decimal = field(metadata={"value_field": True})


@dataclass(frozen=True, slots=True, kw_only=True)
class UserId(ValueObject[UUID]):
    id: UUID = field(metadata={"value_field": True})


@dataclass(frozen=True, slots=True, kw_only=True)
class Address(ValueObject[str]):
    """Only street is marked as value_field"""

    street: str = field(metadata={"value_field": True})
    city: str = field(default="Unknown")
    postal_code: str = field(default="")


@dataclass(frozen=True, slots=True, kw_only=True)
class Product(ValueObject):
    name: str = field(metadata={"value_field": True})
    color: Color = field(default=Color.RED)


@dataclass(frozen=True, slots=True, kw_only=True)
class NoValueFieldVO(ValueObject):
    """No field marked with value_field=True"""

    name: str = field(default="")


@dataclass(frozen=True, slots=True, kw_only=True)
class MutableFieldVO(ValueObject[str]):
    """Has a mutable field (list) — should fail"""

    name: str = field(metadata={"value_field": True})
    tags: list = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class NestedListVO(ValueObject[str]):
    """Has a list of dicts — unsafe type in sequence"""

    name: str = field(metadata={"value_field": True})
    items: list = field(default_factory=lambda: [{"key": "value"}])


# ============================================================================
# TESTS
# ============================================================================


class TestValueObjectFieldValidation:
    """Test that ValueObject validates field types during instantiation"""

    # def test_rejects_invalid_field_type(self):
    #     """A field with mutable (unsafe) type should raise DomainTypeError"""
    #     with pytest.raises(DomainTypeError, match="unsafe type"):
    #         MutableFieldVO(name="test", tags=[])
    #
    # def test_rejects_invalid_type_in_sequence(self):
    #     """Sequences with unsafe types should raise DomainTypeError"""
    #     with pytest.raises(DomainTypeError, match="unsafe type"):
    #         NestedListVO(name="test", items=[{"key": "value"}])

    def test_valid_value_object_instantiates(self):
        """Valid value objects should instantiate without error"""
        money = Money(amount=Decimal("100.50"))
        assert money.amount == Decimal("100.50")

    def test_safe_types_pass_validation(self):
        """Safe immutable types should validate"""
        addr = Address(street="123 Main", city="Springfield", postal_code="12345")
        assert addr.street == "123 Main"
        assert addr.city == "Springfield"


class TestValueProperty:
    """Test the .value property behavior"""

    def test_value_returns_marked_field(self):
        """value property returns the field marked with value_field=True"""
        money = Money(amount=Decimal("50.99"))
        assert money.value == Decimal("50.99")

    def test_value_on_multi_field_object(self):
        """value property works on objects with multiple fields"""
        addr = Address(street="123 Main", city="Springfield", postal_code="12345")
        # Only street is marked as value_field
        assert addr.value == "123 Main"

    def test_value_raises_when_no_field_marked(self):
        """value property raises when no field is marked with value_field=True"""
        with pytest.raises(DomainValidationError, match="no field marked"):
            no_value_vo = NoValueFieldVO(name="test")
            _ = no_value_vo.value


class TestValueObjectRepr:
    """Test string representation"""

    def test_repr_shows_class_and_fields(self):
        money = Money(amount=Decimal("50.99"))
        repr_str = repr(money)
        assert "Money" in repr_str
        assert "50.99" in repr_str

    def test_repr_multi_field(self):
        addr = Address(street="123 Main", city="Springfield", postal_code="12345")
        repr_str = repr(addr)
        assert "Address" in repr_str
        assert "123 Main" in repr_str
        assert "Springfield" in repr_str
        assert "12345" in repr_str

    def test_repr_with_enum(self):
        product = Product(name="Item", color=Color.RED)
        repr_str = repr(product)
        assert "Product" in repr_str
        assert "Item" in repr_str


class TestValueObjectEquality:
    """Test equality behavior"""

    def test_same_values_are_equal(self):
        money1 = Money(amount=Decimal("100"))
        money2 = Money(amount=Decimal("100"))
        assert money1 == money2

    def test_different_values_not_equal(self):
        money1 = Money(amount=Decimal("100"))
        money2 = Money(amount=Decimal("200"))
        assert money1 != money2

    def test_equality_compares_all_fields(self):
        """Equality compares all fields, not just value_field"""
        addr1 = Address(street="123 Main", city="Anytown", postal_code="12345")
        addr2 = Address(street="123 Main", city="Anytown", postal_code="12345")
        # Identical fields → equal
        assert addr1 == addr2

        addr3 = Address(street="123 Main", city="Other City", postal_code="12345")
        # Different city → not equal (even though street matches)
        assert addr1 != addr3

    def test_not_equal_to_different_type(self):
        money = Money(amount=Decimal("100"))
        user_id = UserId(id=UUID("12345678-1234-5678-1234-567812345678"))
        # Different types should not be equal
        assert money != user_id

    def test_hashable(self):
        money = Money(amount=Decimal("100"))
        # Frozen dataclasses are hashable by default
        assert hash(money) is not None

        # Can use in set
        money_set = {money}
        assert money in money_set

    def test_can_use_as_dict_key(self):
        money = Money(amount=Decimal("100"))
        value_dict = {money: "one hundred"}
        assert value_dict[money] == "one hundred"
