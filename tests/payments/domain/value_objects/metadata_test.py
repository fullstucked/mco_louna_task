from types import MappingProxyType

import pytest

from payments.domain.value_objects.metadata import Metadata
from shared.domain.errors import DomainTypeError


class TestMetadataConstruction:
    """Tests for Metadata instantiation."""

    def test_valid_metadata_empty_dict(self):
        """Metadata with empty dict should construct without error."""
        metadata = Metadata(meta={})
        assert metadata.value == {}
        assert isinstance(metadata.value, MappingProxyType)

    def test_valid_metadata_string_keys_only(self):
        """Metadata with string keys should construct without error."""
        meta_dict = {"key1": "value1", "key2": 42, "key3": True, "key4": None}
        metadata = Metadata(meta=meta_dict)
        assert metadata.value == meta_dict

    def test_valid_metadata_nested_dict(self):
        """Metadata with nested dicts should construct without error."""
        meta_dict = {
            "user": {
                "name": "John",
                "age": 30,
            },
            "tags": ["tag1", "tag2"],
        }
        metadata = Metadata(meta=meta_dict)
        assert metadata.value == meta_dict

    def test_valid_metadata_complex_values(self):
        """Metadata with various value types should construct without error."""
        meta_dict = {
            "string": "value",
            "number": 123,
            "float": 45.67,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"inner": "value"},
        }
        metadata = Metadata(meta=meta_dict)
        assert metadata.value == meta_dict

    def test_metadata_non_dict_raises_error(self):
        """Metadata with non-dict value should raise DomainTypeError."""
        with pytest.raises(DomainTypeError) as exc_info:
            Metadata(meta="not a dict")

        assert exc_info.value.message == "Metadata must be a dictionary"

    def test_metadata_list_raises_error(self):
        """Metadata with list instead of dict should raise DomainTypeError."""
        with pytest.raises(DomainTypeError) as exc_info:
            Metadata(meta=[1, 2, 3])

        assert exc_info.value.message == "Metadata must be a dictionary"

    def test_metadata_integer_raises_error(self):
        """Metadata with integer should raise DomainTypeError."""
        with pytest.raises(DomainTypeError) as exc_info:
            Metadata(meta=123)

        assert exc_info.value.message == "Metadata must be a dictionary"

    def test_metadata_non_string_keys_raises_error(self):
        """Metadata with non-string keys should raise DomainTypeError."""
        with pytest.raises(DomainTypeError) as exc_info:
            Metadata(meta={1: "value", 2: "another"})

        assert exc_info.value.message == "Not each field serializable"

    def test_metadata_mixed_key_types_raises_error(self):
        """Metadata with mixed key types should raise DomainTypeError."""
        with pytest.raises(DomainTypeError) as exc_info:
            Metadata(meta={"string_key": "value", 123: "number_key"})

        assert exc_info.value.message == "Not each field serializable"

    def test_metadata_tuple_key_raises_error(self):
        """Metadata with tuple keys should raise DomainTypeError."""
        with pytest.raises(DomainTypeError) as exc_info:
            Metadata(meta={(1, 2): "value"})

        assert exc_info.value.message == "Not each field serializable"

    def test_metadata_immutable(self):
        """Metadata should be immutable."""
        metadata = Metadata(meta={"key": "value"})
        with pytest.raises(Exception) as exc_info:
            metadata.meta = {"new": "dict"}

        assert (
            "cannot assign to field" in str(exc_info.value).lower()
            or "frozen" in str(exc_info.value).lower()
        )

    def test_metadata_value_property(self):
        """Metadata.value should return a dict-like MappingProxyType."""
        meta_dict = {"key": "value"}
        metadata = Metadata(meta=meta_dict)
        assert metadata.value == meta_dict
        assert isinstance(metadata.value, MappingProxyType)

    def test_metadata_empty_string_key(self):
        """Empty string should be valid key."""
        metadata = Metadata(meta={"": "value"})
        assert metadata.value == {"": "value"}

    def test_metadata_unicode_keys(self):
        """Unicode keys should be valid."""
        metadata = Metadata(meta={"名前": "Tanaka", "年齢": 30})
        assert metadata.value == {"名前": "Tanaka", "年齢": 30}

    def test_metadata_none_value_raises_error(self):
        """Metadata(meta=None) !!!"""
        # Currently, code will raise "Metadata must be a dictionary" TODO FIX
        with pytest.raises(DomainTypeError):
            Metadata(meta=None)


class TestMetadataRebuild:
    """Tests for Metadata.rebuild() classmethod."""

    def test_rebuild_valid_dict(self):
        """rebuild() should create Metadata without validation."""
        meta_dict = {"key": "value"}
        metadata = Metadata.rebuild(meta=meta_dict)
        assert metadata.value == meta_dict

    def test_rebuild_skips_dict_validation(self):
        """rebuild() should skip dict type validation."""
        metadata = Metadata.rebuild(meta="not a dict")
        assert metadata.value == "not a dict"

    def test_rebuild_skips_key_validation(self):
        """rebuild() should skip key type validation."""
        metadata = Metadata.rebuild(meta={1: "value", 2: "another"})
        assert metadata.value == {1: "value", 2: "another"}

    def test_rebuild_sets_rebuilding_flag(self):
        """rebuild() should set _rebuilding=True."""
        meta_dict = {"key": "value"}
        metadata = Metadata.rebuild(meta=meta_dict)
        assert metadata._rebuilding is True


class TestMetadataEquality:
    """Tests for Metadata equality."""

    def test_equal_metadata_same_dict(self):
        """Metadata with same dict should be equal."""
        meta_dict = {"key": "value"}
        metadata1 = Metadata(meta=meta_dict)
        metadata2 = Metadata(meta=meta_dict.copy())
        assert metadata1 == metadata2

    def test_unequal_metadata_different_dict(self):
        """Metadata with different dicts should not be equal."""
        metadata1 = Metadata(meta={"key1": "value1"})
        metadata2 = Metadata(meta={"key2": "value2"})
        assert metadata1 != metadata2

    def test_equal_metadata_different_object_same_content(self):
        """Metadata with different dict objects but same content should be equal."""
        metadata1 = Metadata(meta={"a": 1, "b": 2})
        metadata2 = Metadata(meta={"a": 1, "b": 2})
        assert metadata1 == metadata2


class TestMetadataRepr:
    """Tests for Metadata representation."""

    def test_metadata_repr(self):
        """Metadata repr should be custom formatted."""
        metadata = Metadata(meta={"key": "value"})
        repr_str = repr(metadata)

        # Should include class name
        assert "Metadata" in repr_str

    def test_metadata_json_round_trip(self):
        """Metadata should be JSON-serializable via dict conversion."""
        import json

        meta_dict = {"user_id": 123, "tags": ["a", "b"]}
        metadata = Metadata(meta=meta_dict)

        # Convert MappingProxyType to dict for JSON serialization
        json_str = json.dumps(dict(metadata.value))
        restored = json.loads(json_str)

        assert restored == meta_dict

    def test_metadata_json_serializable(self):
        """Core requirement: metadata must be JSON-serializable."""
        import json

        meta_dict = {"key": "value", "nested": {"x": 1}, "array": [1, 2, 3]}
        metadata = Metadata(meta=meta_dict)

        # This should not raise
        json_str = json.dumps(dict(metadata.value))
        assert json.loads(json_str) == meta_dict
