import pytest

from payments.domain.value_objects.description import Description
from shared.domain.errors import DomainValidationError

MIN_LENGTH = 3
MAX_LENGTH = 50


class TestDescriptionConstruction:
    """Tests for Description instantiation."""

    def test_valid_description(self):
        """Valid description should construct without error."""
        desc = Description(text="Valid description")
        assert desc.value == "Valid description"

    def test_description_at_min_length(self):
        """Description at minimum length should be valid."""
        desc = Description(text="abc")
        assert desc.value == "abc"
        assert len(desc.value) == MIN_LENGTH

    def test_description_at_max_length(self):
        """Description at maximum length should be valid."""
        text = "a" * MAX_LENGTH
        desc = Description(text=text)
        assert desc.value == text
        assert len(desc.value) == MAX_LENGTH

    def test_description_too_short(self):
        """Description below minimum length should raise error."""
        with pytest.raises(DomainValidationError) as exc_info:
            Description(text="ab")

        assert exc_info.value.message == "Wrong description lenth"
        assert "lenth = 2" in exc_info.value.context["details"]
        assert f"[{MIN_LENGTH}, {MAX_LENGTH}]" in exc_info.value.context["details"]

    def test_description_too_long(self):
        """Description above maximum length should raise error."""
        text = "a" * (MAX_LENGTH + 1)
        with pytest.raises(DomainValidationError) as exc_info:
            Description(text=text)

        assert exc_info.value.message == "Wrong description lenth"
        assert f"lenth = {MAX_LENGTH + 1}" in exc_info.value.context["details"]

    def test_description_with_newline(self):
        """Description containing newline should raise error."""
        with pytest.raises(DomainValidationError) as exc_info:
            Description(text="Valid\ntext")

        assert exc_info.value.message == "Description contains invalid characters"
        assert "pos=5" in exc_info.value.context["details"]

    def test_description_with_carriage_return(self):
        """Description containing carriage return should raise error."""
        with pytest.raises(DomainValidationError) as exc_info:
            Description(text="Valid\rtext")

        assert exc_info.value.message == "Description contains invalid characters"
        assert "pos=5" in exc_info.value.context["details"]

    def test_description_with_tab(self):
        """Description containing tab should raise error."""
        with pytest.raises(DomainValidationError) as exc_info:
            Description(text="Valid\ttext")

        assert exc_info.value.message == "Description contains invalid characters"
        assert "pos=5" in exc_info.value.context["details"]

    def test_description_with_null_byte(self):
        """Description containing null byte should raise error."""
        with pytest.raises(DomainValidationError) as exc_info:
            Description(text="Valid\x00text")

        assert exc_info.value.message == "Description contains invalid characters"

    def test_description_with_control_character(self):
        """Description containing control character should raise error."""
        with pytest.raises(DomainValidationError) as exc_info:
            Description(text="Valid\x1ftext")

        assert exc_info.value.message == "Description contains invalid characters"

    def test_description_with_delete_character(self):
        """Description containing DEL character (0x7f) should raise error."""
        with pytest.raises(DomainValidationError) as exc_info:
            Description(text="Valid\x7ftext")

        assert exc_info.value.message == "Description contains invalid characters"

    def test_description_immutable(self):
        """Description should be immutable."""
        desc = Description(text="Valid description")
        with pytest.raises(Exception) as exc_info:
            desc.text = "New text"

        assert (
            "cannot assign to field" in str(exc_info.value).lower()
            or "frozen" in str(exc_info.value).lower()
        )


class TestDescriptionRebuild:
    """Tests for Description.rebuild() classmethod."""

    def test_rebuild_valid_description(self):
        """rebuild() should create Description without validation."""
        desc = Description.rebuild(text="Valid description")
        assert desc.value == "Valid description"

    def test_rebuild_skips_length_validation(self):
        """rebuild() should skip length validation."""
        desc = Description.rebuild(text="ab")  # Too short
        assert desc.value == "ab"

    def test_rebuild_skips_pattern_validation(self):
        """rebuild() should skip pattern validation."""
        desc = Description.rebuild(text="Valid\ntext")  # Contains newline
        assert desc.value == "Valid\ntext"

    def test_rebuild_sets_rebuilding_flag(self):
        """rebuild() should set _rebuilding=True."""
        desc = Description.rebuild(text="Valid description")
        assert desc._rebuilding is True

    def test_rebuild_at_minimum_length(self):
        """rebuild() should accept text at minimum length."""
        desc = Description.rebuild(text="abc")
        assert desc.value == "abc"

    def test_rebuild_empty_string(self):
        """rebuild() should accept empty string."""
        desc = Description.rebuild(text="")
        assert desc.value == ""


class TestDescriptionEquality:
    """Tests for Description equality."""

    def test_equal_descriptions_same_text(self):
        """Descriptions with same text should be equal."""
        desc1 = Description(text="Same text")
        desc2 = Description(text="Same text")
        assert desc1 == desc2

    def test_unequal_descriptions_different_text(self):
        """Descriptions with different text should not be equal."""
        desc1 = Description(text="Text one")
        desc2 = Description(text="Text two")
        assert desc1 != desc2

    def test_description_hashable(self):
        """Descriptions should be hashable."""
        desc1 = Description(text="Same text")
        desc2 = Description(text="Same text")
        assert hash(desc1) == hash(desc2)

    def test_description_in_set(self):
        """Descriptions should work in sets."""
        desc1 = Description(text="Text")
        desc2 = Description(text="Text")
        desc_set = {desc1, desc2}
        assert len(desc_set) == 1
