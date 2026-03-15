"""
Validation Utilities Tests

Tests for input validation functions.
"""

import pytest
from datetime import datetime, timedelta
from utils.validation import (
    validate_stock_symbol,
    validate_date_range,
    validate_capital,
    sanitize_symbol,
)


class TestValidateStockSymbol:
    """Tests for stock symbol validation."""

    def test_valid_indian_symbol(self):
        """Test valid Indian stock symbols."""
        assert validate_stock_symbol("RELIANCE") is True
        assert validate_stock_symbol("TCS") is True
        assert validate_stock_symbol("HDFCBANK") is True
        assert validate_stock_symbol("A") is True

    def test_valid_symbol_with_numbers(self):
        """Test symbols with numbers are invalid (only letters allowed)."""
        assert validate_stock_symbol("ABC123") is False

    def test_invalid_symbol_too_long(self):
        """Test symbol exceeds max length."""
        assert validate_stock_symbol("RELIANCEINDUSTRIES") is False

    def test_invalid_empty_symbol(self):
        """Test empty symbol."""
        assert validate_stock_symbol("") is False
        assert validate_stock_symbol("   ") is False

    def test_invalid_none_symbol(self):
        """Test None symbol."""
        assert validate_stock_symbol(None) is False

    def test_symbol_with_spaces(self):
        """Test symbol with spaces gets stripped."""
        assert validate_stock_symbol("  RELIANCE  ") is True


class TestSanitizeSymbol:
    """Tests for symbol sanitization."""

    def test_uppercase_conversion(self):
        """Test conversion to uppercase."""
        assert sanitize_symbol("reliance") == "RELIANCE"
        assert sanitize_symbol("Reliance") == "RELIANCE"

    def test_remove_ns_suffix(self):
        """Test removing NS suffix."""
        assert sanitize_symbol("RELIANCE.NS") == "RELIANCE"
        assert sanitize_symbol("RELIANCE.NSE") == "RELIANCE"

    def test_remove_bo_suffix(self):
        """Test removing BO suffix."""
        assert sanitize_symbol("RELIANCE.BO") == "RELIANCE"
        assert sanitize_symbol("RELIANCE.BSE") == "RELIANCE"

    def test_remove_special_chars(self):
        """Test removing special characters."""
        assert sanitize_symbol("REL@#$IANCE") == "RELIANCE"
        assert sanitize_symbol("RELI-ANCE") == "RELIANCE"

    def test_empty_input(self):
        """Test empty input returns empty string."""
        assert sanitize_symbol("") == ""
        assert sanitize_symbol("   ") == ""

    def test_max_length(self):
        """Test max length is enforced."""
        long_symbol = "A" * 20
        result = sanitize_symbol(long_symbol)
        assert len(result) == 10


class TestValidateDateRange:
    """Tests for date range validation."""

    def test_valid_date_range(self):
        """Test valid date range."""
        is_valid, error = validate_date_range("2023-01-01", "2024-01-01")
        assert is_valid is True
        assert error is None

    def test_same_day(self):
        """Test same day is invalid."""
        is_valid, error = validate_date_range("2024-01-01", "2024-01-01")
        assert is_valid is False
        assert "before" in error.lower()

    def test_start_after_end(self):
        """Test start date after end date."""
        is_valid, error = validate_date_range("2024-01-01", "2023-01-01")
        assert is_valid is False

    def test_invalid_date_format(self):
        """Test invalid date format."""
        is_valid, error = validate_date_range("01-01-2024", "2024-01-01")
        assert is_valid is False
        assert "format" in error.lower()

    def test_exceeds_max_years(self):
        """Test date range exceeds 10 years."""
        is_valid, error = validate_date_range("2010-01-01", "2024-01-01")
        assert is_valid is False
        assert "10 years" in error.lower()

    def test_exactly_max_years(self):
        """Test exactly 10 years is valid."""
        start = (datetime.now() - timedelta(days=3650)).strftime("%Y-%m-%d")
        end = datetime.now().strftime("%Y-%m-%d")
        is_valid, error = validate_date_range(start, end)
        assert is_valid is True


class TestValidateCapital:
    """Tests for capital validation."""

    def test_valid_capital(self):
        """Test valid capital amounts."""
        assert validate_capital(100000) == (True, None)
        assert validate_capital(50000) == (True, None)
        assert validate_capital(1000000) == (True, None)

    def test_zero_capital(self):
        """Test zero capital is invalid."""
        is_valid, error = validate_capital(0)
        assert is_valid is False
        assert "positive" in error.lower()

    def test_negative_capital(self):
        """Test negative capital is invalid."""
        is_valid, error = validate_capital(-1000)
        assert is_valid is False

    def test_below_minimum(self):
        """Test capital below minimum."""
        is_valid, error = validate_capital(5000)
        assert is_valid is False
        assert "10,000" in error

    def test_above_maximum(self):
        """Test capital above maximum."""
        is_valid, error = validate_capital(200000000)
        assert is_valid is False
        assert "100,000,000" in error

    def test_exactly_minimum(self):
        """Test exactly minimum is valid."""
        assert validate_capital(10000) == (True, None)

    def test_exactly_maximum(self):
        """Test exactly maximum is valid."""
        assert validate_capital(100000000) == (True, None)


class TestValidationEdgeCases:
    """Tests for edge cases in validation."""

    def test_unicode_in_symbol(self):
        """Test unicode characters in symbol."""
        assert validate_stock_symbol("RELIANCE\ufeff") is False

    def test_leap_year_dates(self):
        """Test leap year date handling."""
        is_valid, _ = validate_date_range("2024-02-28", "2024-03-01")
        assert is_valid is True

    def test_decimal_capital(self):
        """Test decimal capital amounts."""
        is_valid, _ = validate_capital(100000.50)
        assert is_valid is True
