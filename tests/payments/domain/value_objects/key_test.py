from uuid import uuid4

import pytest

from payments.domain.value_objects.key import IdempotencyKey
from shared.domain.errors import DomainTypeError


class TestIdempotencyKeyConstruction:
    """Tests for IdempotencyKey instantiation."""

    def test_valid_payment_key_uuid4(self):
        """IdempotencyKey with explicit UUID v4 should construct without error."""
        uuid_v4 = uuid4()
        payment_id = IdempotencyKey(key=uuid_v4)
        assert payment_id.value == uuid_v4
        assert payment_id.value.version == 4

    def test_payment_key_uuid1_raises_error(self):
        """IdempotencyKey with UUID v1 should raise DomainTypeError."""
        from uuid import uuid1

        uuid_v1 = uuid1()

        with pytest.raises(DomainTypeError) as exc_info:
            IdempotencyKey(key=uuid_v1)

        assert exc_info.value.message == "IdempotencyKey must be UUID v4"
        assert exc_info.value.context["provided_version"] == 1

    def test_payment_key_uuid3_raises_error(self):
        """IdempotencyKey with UUID v3 should raise DomainTypeError."""
        from uuid import NAMESPACE_DNS, uuid3

        uuid_v3 = uuid3(NAMESPACE_DNS, "example.com")

        with pytest.raises(DomainTypeError) as exc_info:
            IdempotencyKey(key=uuid_v3)

        assert exc_info.value.message == "IdempotencyKey must be UUID v4"
        assert exc_info.value.context["provided_version"] == 3

    def test_payment_key_uuid5_raises_error(self):
        """IdempotencyKey with UUID v5 should raise DomainTypeError."""
        from uuid import NAMESPACE_DNS, uuid5

        uuid_v5 = uuid5(NAMESPACE_DNS, "example.com")

        with pytest.raises(DomainTypeError) as exc_info:
            IdempotencyKey(key=uuid_v5)

        assert exc_info.value.message == "IdempotencyKey must be UUID v4"
        assert exc_info.value.context["provided_version"] == 5

    def test_payment_key_value_property(self):
        """IdempotencyKey.value should return the UUID."""
        uuid_v4 = uuid4()
        payment_id = IdempotencyKey(key=uuid_v4)
        assert payment_id.value == uuid_v4


class TestIdempotencyKeyRebuild:
    """Tests for IdempotencyKey.rebuild() classmethod."""

    def test_rebuild_valid_uuid4(self):
        """rebuild() should create IdempotencyKey without validation."""
        uuid_v4 = uuid4()
        payment_id = IdempotencyKey.rebuild(key=uuid_v4)
        assert payment_id.value == uuid_v4

    def test_rebuild_skips_version_validation(self):
        """rebuild() should skip UUID version validation."""
        from uuid import uuid1

        uuid_v1 = uuid1()

        payment_id = IdempotencyKey.rebuild(key=uuid_v1)
        assert payment_id.value == uuid_v1
        assert payment_id.value.version == 1  # Should accept non-v4

    def test_rebuild_sets_rebuilding_flag(self):
        """rebuild() should set _rebuilding=True."""
        uuid_v4 = uuid4()
        payment_id = IdempotencyKey.rebuild(key=uuid_v4)
        assert payment_id._rebuilding is True


class TestIdempotencyKeyEquality:
    """Tests for IdempotencyKey equality."""

    def test_equal_payment_ids_same_uuid(self):
        """IdempotencyKeys with same UUID should be equal."""
        uuid_v4 = uuid4()
        payment_id1 = IdempotencyKey(key=uuid_v4)
        payment_id2 = IdempotencyKey(key=uuid_v4)
        assert payment_id1 == payment_id2

    def test_unequal_payment_ids_different_uuid(self):
        """IdempotencyKeys with different UUIDs should not be equal."""
        payment_id1 = IdempotencyKey(key=uuid4())
        payment_id2 = IdempotencyKey(key=uuid4())
        assert payment_id1 != payment_id2

    def test_payment_key_hashable(self):
        """IdempotencyKeys should be hashable."""
        uuid_v4 = uuid4()
        payment_id1 = IdempotencyKey(key=uuid_v4)
        payment_id2 = IdempotencyKey(key=uuid_v4)
        assert hash(payment_id1) == hash(payment_id2)

    def test_payment_key_in_set(self):
        """IdempotencyKeys should work in sets."""
        uuid_v4 = uuid4()
        payment_id1 = IdempotencyKey(key=uuid_v4)
        payment_id2 = IdempotencyKey(key=uuid_v4)
        payment_key_set = {payment_id1, payment_id2}
        assert len(payment_key_set) == 1

    def test_payment_key_as_dict_key(self):
        """IdempotencyKeys should work as dictionary keys."""
        uuid_v4 = uuid4()
        payment_id1 = IdempotencyKey(key=uuid_v4)
        payment_id2 = IdempotencyKey(key=uuid_v4)

        payment_dict = {payment_id1: "payment_data"}
        assert payment_dict[payment_id2] == "payment_data"
