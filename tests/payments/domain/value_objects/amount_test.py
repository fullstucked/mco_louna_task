from decimal import Decimal

import pytest

from payments.domain.value_objects.amount import Amount
from shared.domain.errors import DomainTypeError, DomainValidationError


class TestAmountConstruction:
    """Test Amount value object construction and validation"""

    def test_valid_amount(self):
        """Should construct Amount with valid positive decimal"""
        amount = Amount(amount=Decimal("99.99"))
        assert amount.amount == Decimal("99.99")

    def test_valid_amount_minimum(self):
        """Should construct Amount with smallest valid positive amount"""
        amount = Amount(amount=Decimal("0.01"))
        assert amount.amount == Decimal("0.01")

    def test_rejects_zero(self):
        """Should raise DomainValidationError when amount is zero"""
        with pytest.raises(DomainValidationError) as exc_info:
            Amount(amount=Decimal("0"))
        assert "Amount must be greater than zero" in str(exc_info.value.message)

    def test_rejects_negative(self):
        """Should raise DomainValidationError when amount is negative"""
        with pytest.raises(DomainValidationError) as exc_info:
            Amount(amount=Decimal("-1.00"))
        assert "Amount must be greater than zero" in str(exc_info.value.message)

    def test_rejects_invalid_type(self):
        """Should raise DomainTypeError when value is not Decimal"""
        with pytest.raises(DomainTypeError) as exc_info:
            Amount(amount="100.00")
        assert "Amount must be a Decimal" in str(exc_info.value.message)

    def test_rejects_excessive_decimal_places(self):
        """Should raise DomainValidationError when amount has more than 2 decimal places"""
        with pytest.raises(DomainValidationError) as exc_info:
            Amount(amount=Decimal("99.999"))
        assert "Amount cannot have more than 2 decimal places" in str(
            exc_info.value.message
        )


class TestAmountRebuild:
    """Test Amount rebuild classmethod"""

    def test_rebuild_from_valid_amount(self):
        """Should rebuild Amount from valid decimal without running validations"""
        amount = Amount(amount=Decimal("45.67"))
        rebuilt = Amount.rebuild(amount=Decimal("45.67"))
        assert rebuilt == amount

    def test_rebuild_bypasses_validation(self):
        """Should rebuild Amount with _rebuilding flag set to True"""
        rebuilt = Amount.rebuild(amount=Decimal("0"))
        assert rebuilt.amount == Decimal("0")
