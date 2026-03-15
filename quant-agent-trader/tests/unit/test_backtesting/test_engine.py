"""
Backtesting Engine Tests

Tests for backtesting functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np


class TestBacktestEngine:
    """Tests for BacktestEngine class."""

    @pytest.fixture
    def engine(self):
        """Create backtest engine instance."""
        from backtesting.engine import BacktestEngine, BacktestConfigExtended

        config = BacktestConfigExtended()
        return BacktestEngine(config=config)

    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data."""
        dates = pd.date_range(start="2024-01-01", periods=200, freq="D")
        base_price = 1500
        prices = base_price + np.cumsum(np.random.randn(200) * 10)

        return pd.DataFrame(
            {
                "date": dates,
                "open": prices + np.random.randn(200) * 2,
                "high": prices + np.abs(np.random.randn(200) * 5),
                "low": prices - np.abs(np.random.randn(200) * 5),
                "close": prices,
                "volume": np.random.randint(1000000, 10000000, 200),
            }
        )

    def test_engine_initialization(self, engine):
        """Test backtest engine initializes."""
        assert engine.config is not None
        assert engine.initial_capital == 100000.0

    def test_initial_capital(self, engine):
        """Test initial capital is set."""
        assert engine.initial_capital > 0

    def test_commission_calculation(self, engine):
        """Test commission calculation."""
        trade_value = 100000
        commission = engine._calculate_commission(trade_value)

        assert commission > 0

    def test_slippage_calculation(self, engine):
        """Test slippage calculation."""
        price = 1000
        quantity = 100

        slippage = engine._calculate_slippage(price, quantity)

        assert slippage >= 0

    def test_entry_signals(self, engine, sample_price_data):
        """Test entry signal generation."""
        # Create simple indicators
        df = sample_price_data.copy()
        df["sma_20"] = df["close"].rolling(20).mean()
        df["sma_50"] = df["close"].rolling(50).mean()

        # Buy when price crosses above SMA20
        df["signal"] = 0
        df.loc[df["close"] > df["sma_20"], "signal"] = 1

        signals = engine._generate_entry_signals(df)

        assert "buy" in signals or "sell" in signals or "hold" in signals

    def test_exit_signals(self, engine, sample_price_data):
        """Test exit signal generation."""
        df = sample_price_data.copy()
        df["rsi"] = 50
        df.loc[df.index[-10:], "rsi"] = 70

        signals = engine._generate_exit_signals(df)

        assert isinstance(signals, list)

    def test_calculate_pnl(self, engine):
        """Test PnL calculation."""
        entry_price = 100
        exit_price = 110
        quantity = 100

        pnl = engine._calculate_pnl(entry_price, exit_price, quantity)

        assert pnl == 1000  # (110-100) * 100

    def test_calculate_pnl_short(self, engine):
        """Test PnL calculation for short."""
        entry_price = 100
        exit_price = 90
        quantity = 100

        pnl = engine._calculate_pnl(entry_price, exit_price, quantity, side="short")

        assert pnl == 1000  # (100-90) * 100

    def test_position_sizing(self, engine):
        """Test position sizing."""
        capital = 100000
        risk_pct = 0.02
        entry = 100
        stop_loss = 90

        size = engine._calculate_position_size(capital, risk_pct, entry, stop_loss)

        assert size > 0

    def test_position_sizing_zero_risk(self, engine):
        """Test position sizing with zero risk."""
        capital = 100000
        risk_pct = 0.02
        entry = 100
        stop_loss = 100

        size = engine._calculate_position_size(capital, risk_pct, entry, stop_loss)

        assert size == 0

    def test_equity_curve_update(self, engine):
        """Test equity curve updates."""
        engine.equity_curve = [100000]

        engine._update_equity_curve(101000)

        assert engine.equity_curve[-1] == 101000

    def test_max_drawdown_calculation(self, engine):
        """Test max drawdown calculation."""
        equity = [100000, 110000, 105000, 115000, 100000]

        max_dd = engine._calculate_max_drawdown(equity)

        assert max_dd > 0

    def test_sharpe_ratio(self, engine):
        """Test Sharpe ratio calculation."""
        returns = [0.01, 0.02, -0.005, 0.015, 0.01]

        sharpe = engine._calculate_sharpe_ratio(returns)

        assert isinstance(sharpe, float)

    def test_run_backtest_empty_data(self, engine):
        """Test running backtest with empty data."""
        data = {}

        result = engine.run_backtest(
            data=data,
            agents=[],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            regime="sideways",
        )

        assert hasattr(result, "trades")
        assert hasattr(result, "equity_curve")

    def test_run_backtest_with_data(self, engine, sample_price_data):
        """Test running backtest with data."""
        data = {"RELIANCE": sample_price_data}

        mock_agent = Mock()
        mock_agent.analyze = Mock(return_value={"signal": "buy", "confidence": 75.0})

        result = engine.run_backtest(
            data=data,
            agents=[mock_agent],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            regime="sideways",
        )

        assert hasattr(result, "trades")

    def test_get_results_summary(self, engine):
        """Test results summary generation."""
        from dataclasses import dataclass, field

        @dataclass
        class MockBacktestResult:
            trades: list = field(default_factory=list)
            equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
            positions: list = field(default_factory=list)

        result = MockBacktestResult()
        result.equity_curve = pd.DataFrame({"equity": [100000, 105000, 110000]})

        summary = engine.get_results_summary(result)

        assert "Performance Summary" in summary


class TestBacktestEngineEdgeCases:
    """Edge case tests for backtest engine."""

    def test_zero_capital(self):
        """Test with zero capital."""
        from backtesting.engine import BacktestEngine, BacktestConfigExtended

        config = BacktestConfigExtended(initial_capital=0)
        engine = BacktestEngine(config=config)

        assert engine.initial_capital == 0

    def test_negative_prices(self):
        """Test handling of negative prices."""
        from backtesting.engine import BacktestEngine, BacktestConfigExtended

        config = BacktestConfigExtended()
        engine = BacktestEngine(config=config)

        pnl = engine._calculate_pnl(-100, -90, 100)

        assert pnl == -1000

    def test_single_trade(self):
        """Test with single trade."""
        from backtesting.engine import BacktestEngine, BacktestConfigExtended

        config = BacktestConfigExtended()
        engine = BacktestEngine(config=config)

        engine.trades = [
            {
                "symbol": "RELIANCE",
                "entry_date": datetime(2024, 1, 1),
                "exit_date": datetime(2024, 1, 15),
                "quantity": 100,
                "entry_price": 100,
                "exit_price": 110,
                "pnl": 1000,
            }
        ]

        assert len(engine.trades) == 1

    def test_no_trades(self):
        """Test with no trades."""
        from backtesting.engine import BacktestEngine, BacktestConfigExtended

        config = BacktestConfigExtended()
        engine = BacktestEngine(config=config)

        engine.trades = []

        assert len(engine.trades) == 0


class TestBacktestConfig:
    """Tests for backtest configuration."""

    def test_default_config(self):
        """Test default configuration."""
        from backtesting.engine import BacktestConfigExtended

        config = BacktestConfigExtended()

        assert config.initial_capital == 100000.0
        assert config.commission_rate > 0

    def test_custom_config(self):
        """Test custom configuration."""
        from backtesting.engine import BacktestConfigExtended

        config = BacktestConfigExtended(
            initial_capital=500000.0, commission_rate=0.002, slippage=0.001
        )

        assert config.initial_capital == 500000.0
        assert config.commission_rate == 0.002
