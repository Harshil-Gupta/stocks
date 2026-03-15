"""
Risk Engine Tests

Tests for risk management functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np


class TestRiskEngine:
    """Tests for RiskEngine class."""

    @pytest.fixture
    def risk_engine(self):
        """Create risk engine instance."""
        from risk.risk_engine import RiskEngine

        return RiskEngine()

    def test_engine_initialization(self, risk_engine):
        """Test risk engine initializes."""
        assert risk_engine is not None

    def test_max_position_size(self, risk_engine):
        """Test max position size calculation."""
        portfolio_value = 100000
        max_pct = 0.10

        max_size = risk_engine.get_max_position_size(portfolio_value, max_pct)

        assert max_size == 10000

    def test_position_risk_calculation(self, risk_engine):
        """Test position risk calculation."""
        entry_price = 100
        stop_loss = 90
        quantity = 100

        risk = risk_engine.calculate_position_risk(entry_price, stop_loss, quantity)

        assert risk == 1000  # (100-90) * 100

    def test_risk_per_trade(self, risk_engine):
        """Test risk per trade calculation."""
        portfolio_value = 100000
        risk_pct = 0.02

        risk_amount = risk_engine.get_risk_per_trade(portfolio_value, risk_pct)

        assert risk_amount == 2000

    def test_position_size_from_risk(self, risk_engine):
        """Test position size from risk amount."""
        risk_amount = 1000
        entry_price = 100
        stop_loss = 90

        quantity = risk_engine.get_position_size_from_risk(
            risk_amount, entry_price, stop_loss
        )

        assert quantity == 100

    def test_position_size_zero_risk(self, risk_engine):
        """Test position size with zero risk (entry == stop)."""
        risk_amount = 1000
        entry_price = 100
        stop_loss = 100

        quantity = risk_engine.get_position_size_from_risk(
            risk_amount, entry_price, stop_loss
        )

        assert quantity == 0

    def test_validate_position_buy(self, risk_engine):
        """Test position validation for buy."""
        position = {
            "symbol": "RELIANCE",
            "entry_price": 2950,
            "current_price": 3000,
            "quantity": 100,
            "side": "long",
        }

        validation = risk_engine.validate_position(position)

        assert "valid" in validation
        assert validation["valid"] is True

    def test_validate_position_sell(self, risk_engine):
        """Test position validation for sell."""
        position = {
            "symbol": "RELIANCE",
            "entry_price": 2950,
            "current_price": 2900,
            "quantity": 100,
            "side": "short",
        }

        validation = risk_engine.validate_position(position)

        assert "valid" in validation

    def test_validate_position_excessive_loss(self, risk_engine):
        """Test position validation with excessive loss."""
        position = {
            "symbol": "RELIANCE",
            "entry_price": 2950,
            "current_price": 2000,
            "quantity": 100,
            "side": "long",
        }

        validation = risk_engine.validate_position(position)

        # Should flag excessive loss
        assert validation["valid"] is False

    def test_portfolio_risk_metrics(self, risk_engine):
        """Test portfolio risk metrics calculation."""
        positions = [
            {
                "symbol": "RELIANCE",
                "quantity": 100,
                "current_price": 3000,
                "entry_price": 2950,
                "side": "long",
            },
            {
                "symbol": "TCS",
                "quantity": 50,
                "current_price": 3800,
                "entry_price": 3750,
                "side": "long",
            },
        ]

        metrics = risk_engine.calculate_portfolio_risk(positions, 100000)

        assert "total_exposure" in metrics
        assert "total_pnl" in metrics
        assert "max_position_loss" in metrics

    def test_correlation_risk(self, risk_engine):
        """Test correlation risk calculation."""
        returns_df = pd.DataFrame(
            {
                "RELIANCE": np.random.randn(100) * 0.02,
                "TCS": np.random.randn(100) * 0.02,
                "INFY": np.random.randn(100) * 0.02,
            }
        )

        risk = risk_engine.calculate_correlation_risk(returns_df)

        assert "max_correlation" in risk
        assert "portfolio_diversification" in risk

    def test_var_calculation(self, risk_engine):
        """Test Value at Risk calculation."""
        returns = np.random.randn(1000) * 0.02

        var_95 = risk_engine.calculate_var(returns, confidence=0.95)
        var_99 = risk_engine.calculate_var(returns, confidence=0.99)

        assert var_95 > 0
        assert var_99 > var_95

    def test_sharpe_ratio(self, risk_engine):
        """Test Sharpe ratio calculation."""
        returns = np.array([0.01, 0.02, -0.005, 0.015, 0.01])
        risk_free = 0.06

        sharpe = risk_engine.calculate_sharpe_ratio(returns, risk_free)

        assert isinstance(sharpe, float)

    def test_max_drawdown(self, risk_engine):
        """Test maximum drawdown calculation."""
        equity_curve = np.array([100, 110, 105, 120, 115, 130, 125])

        drawdown = risk_engine.calculate_max_drawdown(equity_curve)

        assert drawdown >= 0


class TestRiskEngineEdgeCases:
    """Edge case tests for risk engine."""

    def test_zero_portfolio_value(self):
        """Test with zero portfolio value."""
        from risk.risk_engine import RiskEngine

        engine = RiskEngine()

        max_size = engine.get_max_position_size(0, 0.10)
        risk_amount = engine.get_risk_per_trade(0, 0.02)

        assert max_size == 0
        assert risk_amount == 0

    def test_negative_prices(self):
        """Test with negative prices."""
        from risk.risk_engine import RiskEngine

        engine = RiskEngine()

        risk = engine.calculate_position_risk(-100, -90, 100)

        assert risk == -1000

    def test_empty_positions(self):
        """Test with empty positions."""
        from risk.risk_engine import RiskEngine

        engine = RiskEngine()

        metrics = engine.calculate_portfolio_risk([], 100000)

        assert metrics["total_exposure"] == 0
        assert metrics["total_pnl"] == 0

    def test_single_position(self):
        """Test with single position."""
        from risk.risk_engine import RiskEngine

        engine = RiskEngine()

        positions = [
            {
                "symbol": "RELIANCE",
                "quantity": 100,
                "current_price": 3000,
                "entry_price": 2950,
                "side": "long",
            }
        ]

        metrics = engine.calculate_portfolio_risk(positions, 100000)

        assert metrics["total_exposure"] > 0


class TestRiskEngineMockedAPI:
    """Tests with mocked external API calls."""

    @pytest.mark.asyncio
    async def test_fetch_market_data_mock(self):
        """Test market data fetching with mock."""
        from risk.risk_engine import RiskEngine

        engine = RiskEngine()

        mock_data = pd.DataFrame(
            {
                "close": [100, 102, 101, 103, 105],
                "volume": [1000, 1100, 900, 1200, 1300],
            }
        )

        with patch.object(engine, "_fetch_historical_data", return_value=mock_data):
            data = await engine._fetch_historical_data("RELIANCE")
            assert data is not None

    def test_risk_alerts(self):
        """Test risk alert generation."""
        from risk.risk_engine import RiskEngine

        engine = RiskEngine()

        positions = [
            {
                "symbol": "RELIANCE",
                "quantity": 50000,
                "current_price": 3000,
                "entry_price": 2950,
                "side": "long",
            }
        ]

        alerts = engine.check_risk_alerts(positions, 100000)

        assert isinstance(alerts, list)
