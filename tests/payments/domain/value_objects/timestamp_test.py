from datetime import datetime, timedelta, timezone

import pytest

from payments.domain.value_objects.timestamp import Timestamp
from shared.domain.errors import DomainTypeError


class TestTimestampConstruction:
    """Tests for Timestamp instantiation."""

    def test_valid_timestamp_utc(self):
        """Timestamp with UTC datetime should construct without error."""
        dt = datetime(2026, 7, 9, 12, 30, 45, tzinfo=timezone.utc)
        timestamp = Timestamp(timestamp=dt)
        assert timestamp.value == dt

    def test_valid_timestamp_custom_timezone(self):
        """Timestamp with custom timezone should construct without error."""
        custom_tz = timezone(timedelta(hours=5, minutes=30))
        dt = datetime(2026, 7, 9, 12, 30, 45, tzinfo=custom_tz)
        timestamp = Timestamp(timestamp=dt)
        assert timestamp.value == dt

    def test_valid_timestamp_with_microseconds(self):
        """Timestamp with microseconds should construct without error."""
        dt = datetime(2026, 7, 9, 12, 30, 45, 123456, tzinfo=timezone.utc)
        timestamp = Timestamp(timestamp=dt)
        assert timestamp.value == dt

    def test_timestamp_default_factory(self):
        """Timestamp without explicit value should use current UTC time."""
        before = datetime.now(timezone.utc)
        timestamp = Timestamp()
        after = datetime.now(timezone.utc)

        assert timestamp.value.tzinfo == timezone.utc
        assert before <= timestamp.value <= after

    def test_timestamp_naive_datetime_raises_error(self):
        """Timestamp with naive (non-timezone-aware) datetime should raise DomainTypeError."""
        dt = datetime(2026, 7, 9, 12, 30, 45)  # No tzinfo
        with pytest.raises(DomainTypeError) as exc_info:
            Timestamp(timestamp=dt)

        assert exc_info.value.message == "Timestamp must be timezone-aware"

    def test_timestamp_non_datetime_raises_error(self):
        """Timestamp with non-datetime value should raise DomainTypeError."""
        with pytest.raises(DomainTypeError) as exc_info:
            Timestamp(timestamp="2026-07-09T12:30:45Z")

        assert exc_info.value.message == "Timestamp must be datetime"

    def test_timestamp_integer_raises_error(self):
        """Timestamp with integer should raise DomainTypeError."""
        with pytest.raises(DomainTypeError) as exc_info:
            Timestamp(timestamp=1720598445)

        assert exc_info.value.message == "Timestamp must be datetime"

    def test_timestamp_none_raises_error(self):
        """Timestamp with None should raise DomainTypeError."""
        with pytest.raises(DomainTypeError) as exc_info:
            Timestamp(timestamp=None)

        assert exc_info.value.message == "Timestamp must be datetime"

    def test_timestamp_immutable(self):
        """Timestamp should be immutable."""
        dt = datetime(2026, 7, 9, 12, 30, 45, tzinfo=timezone.utc)
        timestamp = Timestamp(timestamp=dt)

        with pytest.raises(Exception) as exc_info:
            timestamp.timestamp = datetime.now(timezone.utc)

        assert (
            "cannot assign to field" in str(exc_info.value).lower()
            or "frozen" in str(exc_info.value).lower()
        )

    def test_timestamp_value_property(self):
        """Timestamp.value should return the datetime."""
        dt = datetime(2026, 7, 9, 12, 30, 45, tzinfo=timezone.utc)
        timestamp = Timestamp(timestamp=dt)
        assert timestamp.value == dt


class TestTimestampNow:
    """Tests for Timestamp.now() classmethod."""

    def test_now_returns_current_utc_time(self):
        """now() should return current UTC datetime."""
        before = datetime.now(timezone.utc)
        timestamp = Timestamp.now()
        after = datetime.now(timezone.utc)

        assert timestamp.value.tzinfo == timezone.utc
        assert before <= timestamp.value <= after

    def test_now_is_timezone_aware(self):
        """now() should return timezone-aware timestamp."""
        timestamp = Timestamp.now()
        assert timestamp.value.tzinfo is not None
        assert timestamp.value.tzinfo == timezone.utc

    def test_now_returns_timestamp_instance(self):
        """now() should return Timestamp instance."""
        timestamp = Timestamp.now()
        assert isinstance(timestamp, Timestamp)


class TestTimestampIso:
    """Tests for Timestamp.iso() method."""

    def test_iso_format_utc(self):
        """iso() should return ISO format string for UTC datetime."""
        dt = datetime(2026, 7, 9, 12, 30, 45, tzinfo=timezone.utc)
        timestamp = Timestamp(timestamp=dt)
        iso_str = timestamp.iso()

        assert iso_str == "2026-07-09T12:30:45+00:00"
        assert isinstance(iso_str, str)

    def test_iso_format_custom_timezone(self):
        """iso() should return ISO format string with timezone offset."""
        custom_tz = timezone(timedelta(hours=5, minutes=30))
        dt = datetime(2026, 7, 9, 12, 30, 45, tzinfo=custom_tz)
        timestamp = Timestamp(timestamp=dt)
        iso_str = timestamp.iso()

        assert iso_str == "2026-07-09T12:30:45+05:30"

    def test_iso_format_with_microseconds(self):
        """iso() should include microseconds in ISO format."""
        dt = datetime(2026, 7, 9, 12, 30, 45, 123456, tzinfo=timezone.utc)
        timestamp = Timestamp(timestamp=dt)
        iso_str = timestamp.iso()

        assert iso_str == "2026-07-09T12:30:45.123456+00:00"

    def test_iso_format_negative_timezone(self):
        """iso() should handle negative timezone offsets."""
        custom_tz = timezone(timedelta(hours=-8))
        dt = datetime(2026, 7, 9, 12, 30, 45, tzinfo=custom_tz)
        timestamp = Timestamp(timestamp=dt)
        iso_str = timestamp.iso()

        assert iso_str == "2026-07-09T12:30:45-08:00"


class TestTimestampRebuild:
    """Tests for Timestamp.rebuild() classmethod."""

    def test_rebuild_valid_datetime(self):
        """rebuild() should create Timestamp without validation."""
        dt = datetime(2026, 7, 9, 12, 30, 45, tzinfo=timezone.utc)
        timestamp = Timestamp.rebuild(timestamp=dt)
        assert timestamp.value == dt

    def test_rebuild_skips_datetime_validation(self):
        """rebuild() should skip datetime type validation."""
        timestamp = Timestamp.rebuild(timestamp="not a datetime")
        assert timestamp.value == "not a datetime"

    def test_rebuild_skips_timezone_validation(self):
        """rebuild() should skip timezone-aware validation."""
        dt = datetime(2026, 7, 9, 12, 30, 45)  # Naive datetime
        timestamp = Timestamp.rebuild(timestamp=dt)
        assert timestamp.value == dt

    def test_rebuild_sets_rebuilding_flag(self):
        """rebuild() should set _rebuilding=True."""
        dt = datetime(2026, 7, 9, 12, 30, 45, tzinfo=timezone.utc)
        timestamp = Timestamp.rebuild(timestamp=dt)
        assert timestamp._rebuilding is True


class TestTimestampEquality:
    """Tests for Timestamp equality."""

    def test_equal_timestamp_same_datetime(self):
        """Timestamp with same datetime should be equal."""
        dt = datetime(2026, 7, 9, 12, 30, 45, tzinfo=timezone.utc)
        timestamp1 = Timestamp(timestamp=dt)
        timestamp2 = Timestamp(timestamp=dt)
        assert timestamp1 == timestamp2

    def test_unequal_timestamp_different_datetime(self):
        """Timestamp with different datetime should not be equal."""
        dt1 = datetime(2026, 7, 9, 12, 30, 45, tzinfo=timezone.utc)
        dt2 = datetime(2026, 7, 10, 12, 30, 45, tzinfo=timezone.utc)
        timestamp1 = Timestamp(timestamp=dt1)
        timestamp2 = Timestamp(timestamp=dt2)
        assert timestamp1 != timestamp2

    def test_equal_timestamp_different_timezone_same_instant(self):
        """Timestamp representing same instant in different timezones should be equal."""
        dt_utc = datetime(2026, 7, 9, 12, 30, 45, tzinfo=timezone.utc)
        custom_tz = timezone(timedelta(hours=5, minutes=30))
        dt_custom = datetime(2026, 7, 9, 18, 0, 45, tzinfo=custom_tz)

        timestamp1 = Timestamp(timestamp=dt_utc)
        timestamp2 = Timestamp(timestamp=dt_custom)
        # These represent the same instant in time
        assert timestamp1 == timestamp2


class TestTimestampRepr:
    """Tests for Timestamp representation."""

    def test_timestamp_repr(self):
        """Timestamp repr should be custom formatted."""
        dt = datetime(2026, 7, 9, 12, 30, 45, tzinfo=timezone.utc)
        timestamp = Timestamp(timestamp=dt)
        repr_str = repr(timestamp)

        # Should include class name
        assert "Timestamp" in repr_str
