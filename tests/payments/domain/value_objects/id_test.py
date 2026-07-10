from uuid import UUID, uuid4

import pytest

from payments.domain.value_objects.id import PaymentID
from shared.domain.errors import DomainTypeError


class TestPaymentIDConstruction:
    """Tests for PaymentID instantiation."""

    def test_valid_payment_id_default(self):
        """PaymentID with default uuid4 should construct without error."""
        payment_id = PaymentID()
        assert isinstance(payment_id.value, UUID)
        assert payment_id.value.version == 4

    def test_valid_payment_id_uuid4(self):
        """PaymentID with explicit UUID v4 should construct without error."""
        uuid_v4 = uuid4()
        payment_id = PaymentID(id=uuid_v4)
        assert payment_id.value == uuid_v4
        assert payment_id.value.version == 4

    def test_payment_id_uuid1_raises_error(self):
        """PaymentID with UUID v1 should raise DomainTypeError."""
        from uuid import uuid1

        uuid_v1 = uuid1()

        with pytest.raises(DomainTypeError) as exc_info:
            PaymentID(id=uuid_v1)

        assert exc_info.value.message == "PaymentID must be UUID v4"
        assert exc_info.value.context["provided_version"] == 1

    def test_payment_id_uuid3_raises_error(self):
        """PaymentID with UUID v3 should raise DomainTypeError."""
        from uuid import NAMESPACE_DNS, uuid3

        uuid_v3 = uuid3(NAMESPACE_DNS, "example.com")

        with pytest.raises(DomainTypeError) as exc_info:
            PaymentID(id=uuid_v3)

        assert exc_info.value.message == "PaymentID must be UUID v4"
        assert exc_info.value.context["provided_version"] == 3

    def test_payment_id_uuid5_raises_error(self):
        """PaymentID with UUID v5 should raise DomainTypeError."""
        from uuid import NAMESPACE_DNS, uuid5

        uuid_v5 = uuid5(NAMESPACE_DNS, "example.com")

        with pytest.raises(DomainTypeError) as exc_info:
            PaymentID(id=uuid_v5)

        assert exc_info.value.message == "PaymentID must be UUID v4"
        assert exc_info.value.context["provided_version"] == 5

    def test_payment_id_immutable(self):
        """PaymentID should be immutable."""
        payment_id = PaymentID()
        with pytest.raises(Exception) as exc_info:
            payment_id.id = uuid4()

        assert (
            "cannot assign to field" in str(exc_info.value).lower()
            or "frozen" in str(exc_info.value).lower()
        )

    def test_payment_id_value_property(self):
        """PaymentID.value should return the UUID."""
        uuid_v4 = uuid4()
        payment_id = PaymentID(id=uuid_v4)
        assert payment_id.value == uuid_v4


class TestPaymentIDRebuild:
    """Tests for PaymentID.rebuild() classmethod."""

    def test_rebuild_valid_uuid4(self):
        """rebuild() should create PaymentID without validation."""
        uuid_v4 = uuid4()
        payment_id = PaymentID.rebuild(id=uuid_v4)
        assert payment_id.value == uuid_v4

    def test_rebuild_skips_version_validation(self):
        """rebuild() should skip UUID version validation."""
        from uuid import uuid1

        uuid_v1 = uuid1()

        payment_id = PaymentID.rebuild(id=uuid_v1)
        assert payment_id.value == uuid_v1
        assert payment_id.value.version == 1  # Should accept non-v4

    def test_rebuild_sets_rebuilding_flag(self):
        """rebuild() should set _rebuilding=True."""
        uuid_v4 = uuid4()
        payment_id = PaymentID.rebuild(id=uuid_v4)
        assert payment_id._rebuilding is True


class TestPaymentIDEquality:
    """Tests for PaymentID equality."""

    def test_equal_payment_ids_same_uuid(self):
        """PaymentIDs with same UUID should be equal."""
        uuid_v4 = uuid4()
        payment_id1 = PaymentID(id=uuid_v4)
        payment_id2 = PaymentID(id=uuid_v4)
        assert payment_id1 == payment_id2

    def test_unequal_payment_ids_different_uuid(self):
        """PaymentIDs with different UUIDs should not be equal."""
        payment_id1 = PaymentID()
        payment_id2 = PaymentID()
        assert payment_id1 != payment_id2

    def test_payment_id_hashable(self):
        """PaymentIDs should be hashable."""
        uuid_v4 = uuid4()
        payment_id1 = PaymentID(id=uuid_v4)
        payment_id2 = PaymentID(id=uuid_v4)
        assert hash(payment_id1) == hash(payment_id2)

    def test_payment_id_in_set(self):
        """PaymentIDs should work in sets."""
        uuid_v4 = uuid4()
        payment_id1 = PaymentID(id=uuid_v4)
        payment_id2 = PaymentID(id=uuid_v4)
        payment_id_set = {payment_id1, payment_id2}
        assert len(payment_id_set) == 1

    def test_payment_id_as_dict_key(self):
        """PaymentIDs should work as dictionary keys."""
        uuid_v4 = uuid4()
        payment_id1 = PaymentID(id=uuid_v4)
        payment_id2 = PaymentID(id=uuid_v4)

        payment_dict = {payment_id1: "payment_data"}
        assert payment_dict[payment_id2] == "payment_data"
