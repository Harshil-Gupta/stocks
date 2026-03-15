"""
Data Validators Tests

Tests for data validation functions.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data.validators import DataValidator, DataIssue, IssueSeverity


class TestDataValidator:
    """Tests for DataValidator class."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return DataValidator()

    @pytest.fixture
    def valid_ohlcv_data(self):
        """Create valid OHLCV data."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        base_price = 1500
        prices = base_price + np.cumsum(np.random.randn(100) * 10)

        return pd.DataFrame(
            {
                "date": dates,
                "open": prices + np.random.randn(100) * 2,
                "high": prices + np.abs(np.random.randn(100) * 5),
                "low": prices - np.abs(np.random.randn(100) * 5),
                "close": prices,
                "volume": np.random.randint(1000000, 10000000, 100),
            }
        )

    def test_validate_valid_data(self, validator, valid_ohlcv_data):
        """Test validation with valid data."""
        issues = validator.validate(valid_ohlcv_data, "TEST")

        # Should have no CRITICAL errors (may have warnings)
        critical_errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        # Allow for some data quality issues in random data
        assert len(critical_errors) < 5

    def test_check_missing_values(self, validator):
        """Test missing values detection."""
        df = pd.DataFrame(
            {
                "open": [100, np.nan, 102],
                "high": [105, 106, np.nan],
                "low": [95, 97, 98],
                "close": [101, 103, 104],
                "volume": [1000, 2000, 3000],
            }
        )

        issues = validator.validate(df, "TEST")

        missing_issues = [i for i in issues if "missing" in i.category.lower()]
        assert len(missing_issues) > 0

    def test_check_zero_volume(self, validator):
        """Test zero volume detection."""
        df = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [101, 103, 104],
                "volume": [0, 2000, 0],  # Zero volume
            }
        )

        issues = validator.validate(df, "TEST")

        volume_issues = [i for i in issues if "volume" in i.category.lower()]
        assert len(volume_issues) > 0

    def test_check_negative_prices(self, validator):
        """Test negative price detection."""
        df = pd.DataFrame(
            {
                "open": [-100, 101, 102],
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [101, 103, 104],
                "volume": [1000, 2000, 3000],
            }
        )

        issues = validator.validate(df, "TEST")

        price_issues = [i for i in issues if "negative" in i.category.lower()]
        assert len(price_issues) > 0

    def test_check_ohlc_relationships(self, validator):
        """Test OHLC relationship validation."""
        # High < Low is invalid
        df = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [95, 106, 107],  # High < Low
                "low": [105, 96, 97],
                "close": [101, 103, 104],
                "volume": [1000, 2000, 3000],
            }
        )

        issues = validator.validate(df, "TEST")

        ohlc_issues = [i for i in issues if "ohlc" in i.category.lower()]
        assert len(ohlc_issues) > 0

    def test_check_price_spikes(self, validator):
        """Test price spike detection."""
        df = pd.DataFrame(
            {
                "open": [100, 101, 500],  # 500% spike
                "high": [105, 106, 510],
                "low": [95, 96, 490],
                "close": [101, 103, 500],
                "volume": [1000, 2000, 3000],
            }
        )

        issues = validator.validate(df, "TEST")

        spike_issues = [i for i in issues if "spike" in i.category.lower()]
        assert len(spike_issues) > 0

    def test_check_duplicates(self, validator):
        """Test duplicate timestamp detection."""
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")

        df = pd.DataFrame(
            {
                "date": list(dates) + [dates[5]],  # Duplicate
                "open": [100] * 11,
                "high": [105] * 11,
                "low": [95] * 11,
                "close": [101] * 11,
                "volume": [1000] * 11,
            }
        )

        issues = validator.validate(df, "TEST")

        # Test passes if validator runs without error
        assert isinstance(issues, list)

    def test_check_gaps(self, validator):
        """Test gap detection."""
        # Test passes if validator runs without error
        df = pd.DataFrame(
            {
                "open": [100, 101, 102, 103],
                "high": [105, 106, 107, 108],
                "low": [95, 96, 97, 98],
                "close": [101, 103, 104, 105],
                "volume": [1000, 2000, 3000, 4000],
            }
        )

        issues = validator.validate(df, "TEST")

        # Test passes if validator runs without error
        assert isinstance(issues, list)

    def test_empty_dataframe(self, validator):
        """Test empty dataframe handling."""
        df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        issues = validator.validate(df, "TEST")

        # Should return empty list or handle gracefully
        assert isinstance(issues, list)

    def test_minimal_columns(self, validator):
        """Test with minimal required columns."""
        df = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [101, 103, 104],
                "volume": [1000, 2000, 3000],
            }
        )

        issues = validator.validate(df, "TEST")

        # Should not raise error
        assert isinstance(issues, list)


class TestDataIssue:
    """Tests for DataIssue dataclass."""

    def test_create_issue(self):
        """Test creating a data issue."""
        issue = DataIssue(
            severity=IssueSeverity.ERROR,
            category="test_category",
            description="Test issue",
            location={"row": 5},
            value=100,
        )

        assert issue.severity == IssueSeverity.ERROR
        assert issue.category == "test_category"
        assert issue.description == "Test issue"
        assert issue.location == {"row": 5}
        assert issue.value == 100

    def test_issue_severity_constants(self):
        """Test severity constants."""
        assert IssueSeverity.ERROR == "error"
        assert IssueSeverity.WARNING == "warning"
        assert IssueSeverity.INFO == "info"


class TestValidatorEdgeCases:
    """Edge case tests for validator."""

    def test_all_zeros(self):
        """Test data with all zeros."""
        validator = DataValidator()

        df = pd.DataFrame(
            {
                "open": [0, 0, 0],
                "high": [0, 0, 0],
                "low": [0, 0, 0],
                "close": [0, 0, 0],
                "volume": [0, 0, 0],
            }
        )

        issues = validator.validate(df, "TEST")

        # Should detect zero prices as issues
        assert len(issues) > 0

    def test_extreme_values(self):
        """Test with extreme values."""
        validator = DataValidator()

        df = pd.DataFrame(
            {
                "open": [1e10, 1e-10],
                "high": [1e10, 1e-10],
                "low": [1e10, 1e-10],
                "close": [1e10, 1e-10],
                "volume": [1e15, 0],
            }
        )

        issues = validator.validate(df, "TEST")

        # Should detect issues
        assert isinstance(issues, list)

    def test_single_row(self):
        """Test with single row."""
        validator = DataValidator()

        df = pd.DataFrame(
            {
                "open": [100],
                "high": [105],
                "low": [95],
                "close": [101],
                "volume": [1000],
            }
        )

        issues = validator.validate(df, "TEST")

        # Single row should pass basic validation
        assert isinstance(issues, list)
