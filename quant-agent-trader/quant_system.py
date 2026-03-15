"""
Professional Quantitative Trading System.

A modular, production-ready quant trading system following institutional standards.

Architecture:
┌─────────────────────────────────────────────────────────────────────┐
│                         QUANT TRADING SYSTEM                        │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │    DATA      │  │   FEATURES   │  │       STRATEGIES        │ │
│  │  INGESTION   │→ │  ENGINEERING  │→ │      (Signals)          │ │
│  │              │  │              │  │                          │ │
│  │ - API fetch  │  │ - Indicators │  │ - MA Crossover          │ │
│  │ - Caching    │  │ - Factors    │  │ - RSI Mean Reversion   │ │
│  │ - Validation │  │ - Labels     │  │ - Breakout             │ │
│  └──────────────┘  └──────────────┘  │ - Momentum              │ │
│                                       └──────────────────────────┘ │
│                                              ↓                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │    RISK      │  │  PORTFOLIO   │  │      EXECUTION          │ │
│  │  MANAGEMENT  │← │ CONSTRUCTION  │← │      (Backtest)         │ │
│  │              │  │              │  │                          │ │
│  │ - Position   │  │ - Optimizer   │  │ - Order simulation      │ │
│  │ - Limits     │  │ - Weights    │  │ - Costs                │ │
│  │ - Exposure   │  │ - Rebalance   │  │ - Slippage             │ │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘ │
│                                              ↓                    │
│                    ┌──────────────────────────────────────┐       │
│                    │        ANALYTICS & RESEARCH          │       │
│                    │  - Performance metrics                │       │
│                    │  - Strategy comparison               │       │
│                    │  - Hyperparameter tuning            │       │
│                    └──────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘

Usage:
    from quant_system import QuantSystem

    system = QuantSystem()

    # Run backtest
    results = system.backtest(
        symbols=["RELIANCE", "TCS"],
        start_date="2023-01-01",
        end_date="2024-01-01",
        strategy="ma_crossover",
    )

    # Run live simulation
    signals = system.run("RELIANCE")
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class SystemConfig:
    """Configuration for the quant system."""

    data_dir: str = "data"
    cache_dir: str = "data/cache"
    models_dir: str = "models"
    results_dir: str = "research/results"
    logs_dir: str = "logs"

    initial_capital: float = 100000
    risk_free_rate: float = 0.06
    max_position_size: float = 0.25
    max_portfolio_risk: float = 0.20

    default_strategy: str = "ma_crossover"
    enable_caching: bool = True
    cache_ttl_hours: int = 24

    enable_research: bool = True


@dataclass
class BacktestResult:
    """Results from backtest."""

    strategy_name: str
    symbols: List[str]
    start_date: str
    end_date: str

    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    metrics: Dict[str, float]

    parameters: Dict[str, Any]
    duration_seconds: float


@dataclass
class LiveSignal:
    """Signal from live run."""

    symbol: str
    signal: str
    confidence: float
    price: float
    timestamp: datetime
    strategy: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class QuantSystem:
    """
    Professional Quantitative Trading System.

    Orchestrates the entire pipeline:
    1. Data Ingestion
    2. Feature Engineering
    3. Strategy Execution
    4. Portfolio Construction
    5. Risk Management
    6. Backtesting/Execution
    7. Analytics & Reporting
    """

    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or SystemConfig()
        self._init_directories()
        self._init_components()

        logger.info("Quant Trading System initialized")

    def _init_directories(self):
        """Create necessary directories."""
        for dir_path in [
            self.config.data_dir,
            self.config.cache_dir,
            self.config.models_dir,
            self.config.results_dir,
            self.config.logs_dir,
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    def _init_components(self):
        """Initialize system components."""
        from data.cache import MarketDataCache
        from features import FeaturePipeline, FeatureConfig, FeatureMode
        from strategies import create_strategy, StrategyRegistry
        from backtesting import VectorizedBacktestEngine, BacktestConfig
        from portfolio.optimization import PortfolioOptimizer, OptimizationMethod
        from risk.risk_engine import RiskEngine
        from analytics.performance_metrics import PerformanceAnalyzer
        from research import ExperimentTracker

        self.cache = MarketDataCache(
            cache_dir=self.config.cache_dir,
            default_ttl_hours=self.config.cache_ttl_hours,
            enable_incremental=True,
        )

        self.feature_config = FeatureConfig(min_history=200)
        self.feature_pipeline = FeaturePipeline(self.feature_config)

        self.backtest_config = BacktestConfig(
            initial_capital=self.config.initial_capital,
            commission_rate=0.001,
            slippage_bps=5.0,
        )

        self.portfolio_optimizer = PortfolioOptimizer(
            method=OptimizationMethod.MAX_SHARPE
        )

        self.risk_engine = RiskEngine(
            max_position_size=self.config.max_position_size,
            max_portfolio_risk=self.config.max_portfolio_risk,
        )

        self.performance_analyzer = PerformanceAnalyzer(
            risk_free_rate=self.config.risk_free_rate
        )

        if self.config.enable_research:
            self.experiment_tracker = ExperimentTracker(self.config.results_dir)

    def get_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get market data with caching from Upstox API.

        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            OHLCV DataFrame with lowercase columns
        """
        from data.ingestion.upstox_v3 import UpstoxClient

        def fetch_data():
            client = UpstoxClient()

            end = end_date or datetime.now().strftime("%Y-%m-%d")
            start = start_date or (datetime.now() - timedelta(days=365)).strftime(
                "%Y-%m-%d"
            )

            df = client.get_historical(
                symbol=symbol,
                unit="days",
                interval="1",
                to_date=end,
                from_date=start,
            )

            if df is not None and not df.empty:
                df.columns = df.columns.str.lower()
                return df

            logger.warning(f"Upstox fetch failed for {symbol}, using fallback")
            return self._get_fallback_data(symbol, start, end)

        if self.config.enable_caching:
            data = self.cache.get(
                symbol,
                fetch_func=fetch_data,
                start_date=start_date,
                end_date=end_date,
            )
            if data is not None:
                return data

        return fetch_data()

    def _get_fallback_data(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Fallback to yfinance if Upstox fails."""
        try:
            import yfinance as yf

            yahoo_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
            ticker = yf.Ticker(yahoo_symbol)
            df = ticker.history(start=start_date, end=end_date)

            if df.empty:
                raise ValueError("No data from yfinance")

            df = df.reset_index()
            df.columns = df.columns.str.lower()

            return df
        except Exception as e:
            logger.error(f"Fallback data fetch failed: {e}")
            raise ValueError(f"Cannot fetch data for {symbol}")

    def generate_features(
        self,
        data: pd.DataFrame,
        features: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Generate features from price data."""
        from features import FeatureMode

        if features:
            self.feature_config.features = features

        return self.feature_pipeline.compute_features(data, mode=FeatureMode.INFERENCE)

    def run_strategy(
        self, data: pd.DataFrame, strategy_name: str, **strategy_params
    ) -> LiveSignal:
        """Run a single strategy on data."""
        from strategies import create_strategy

        strategy = create_strategy(strategy_name, **strategy_params)

        signal_obj = strategy.generate_signals(data)

        return LiveSignal(
            symbol="UNKNOWN",
            signal=signal_obj.signal.value,
            confidence=signal_obj.confidence,
            price=data["close"].iloc[-1] if "close" in data.columns else 0,
            timestamp=datetime.now(),
            strategy=strategy_name,
            metadata=signal_obj.metadata,
        )

    def backtest(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        strategy: str = "ma_crossover",
        strategy_params: Optional[Dict] = None,
        portfolio_method: str = "equal_weight",
        initial_capital: Optional[float] = None,
    ) -> BacktestResult:
        """
        Run backtest for symbols.

        Args:
            symbols: List of stock symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            strategy: Strategy name
            strategy_params: Strategy parameters
            portfolio_method: Portfolio construction method
            initial_capital: Starting capital

        Returns:
            BacktestResult with metrics and data
        """
        import time
        from strategies import SignalType

        start_time = time.time()

        logger.info(f"Starting backtest: {symbols} from {start_date} to {end_date}")

        all_data = {}
        all_signals = {}

        for symbol in symbols:
            data = self.get_data(symbol, start_date, end_date)

            if data is None or data.empty:
                logger.warning(f"No data for {symbol}, skipping")
                continue

            all_data[symbol] = data

            strategy_obj = create_strategy(strategy, **(strategy_params or {}))

            signal_series = []
            for i in range(len(data)):
                window_data = data.iloc[: i + 1]
                signal_obj = strategy_obj.generate_signals(window_data)

                direction = signal_obj.signal.direction
                signal_series.append(direction)

            signals = pd.DataFrame(
                {
                    "date": data.index,
                    "symbol": symbol,
                    "signal": signal_series,
                }
            ).set_index("date")

            all_signals[symbol] = signals

        if not all_data:
            raise ValueError("No data available for any symbol")

        from backtesting import VectorizedBacktestEngine, BacktestConfig

        config = BacktestConfig(
            initial_capital=initial_capital or self.config.initial_capital,
        )

        engine = VectorizedBacktestEngine(config)

        if len(all_data) == 1:
            symbol = list(all_data.keys())[0]
            result = engine.run(all_data[symbol], all_signals[symbol])
        else:
            result = engine.run_portfolio(all_data, all_signals)

        duration = time.time() - start_time

        logger.info(f"Backtest completed in {duration:.2f}s")
        logger.info(f"Total Return: {result.metrics.total_return * 100:.2f}%")
        logger.info(f"Sharpe: {result.metrics.sharpe_ratio:.2f}")
        logger.info(f"Max DD: {result.metrics.max_drawdown * 100:.2f}%")

        return BacktestResult(
            strategy_name=strategy,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            equity_curve=result.equity_curve,
            trades=result.trades,
            metrics=result.metrics.to_dict(),
            parameters={
                "strategy": strategy,
                "strategy_params": strategy_params or {},
                "portfolio_method": portfolio_method,
            },
            duration_seconds=duration,
        )

    def optimize_portfolio(
        self,
        expected_returns: pd.Series,
        covariance: pd.DataFrame,
        method: str = "max_sharpe",
    ) -> pd.Series:
        """Optimize portfolio weights."""
        from portfolio.optimization import OptimizationMethod

        method_map = {
            "max_sharpe": OptimizationMethod.MAX_SHARPE,
            "min_variance": OptimizationMethod.MIN_VARIANCE,
            "risk_parity": OptimizationMethod.RISK_PARITY,
            "equal_weight": OptimizationMethod.EQUAL_WEIGHT,
        }

        optimizer = PortfolioOptimizer(
            method=method_map.get(method, OptimizationMethod.MAX_SHARPE)
        )

        result = optimizer.optimize(expected_returns, covariance)

        return result.weights

    def analyze_performance(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict[str, float]:
        """Analyze strategy performance."""
        metrics = self.performance_analyzer.compute_metrics(returns, benchmark_returns)

        return {
            "total_return": metrics.total_return,
            "cagr": metrics.cagr,
            "sharpe_ratio": metrics.sharpe_ratio,
            "sortino_ratio": metrics.sortino_ratio,
            "max_drawdown": metrics.max_drawdown,
            "calmar_ratio": metrics.calmar_ratio,
            "win_rate": metrics.win_rate,
            "profit_factor": metrics.profit_factor,
        }

    def run_live(
        self,
        symbol: str,
        strategy: Optional[str] = None,
    ) -> LiveSignal:
        """
        Generate live signal for symbol.

        Args:
            symbol: Stock symbol
            strategy: Strategy name (uses default if not specified)

        Returns:
            LiveSignal
        """
        strategy = strategy or self.config.default_strategy

        data = self.get_data(symbol)

        return self.run_strategy(data, strategy)

    def run_research(
        self,
        experiment_name: str,
        strategy_func: callable,
        parameter_grid: Dict[str, List],
        symbols: List[str],
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Run research experiment with parameter sweep."""
        from research import HyperparameterOptimizer

        optimizer = HyperparameterOptimizer(
            strategy_func=strategy_func,
            parameter_grid=parameter_grid,
            optimization_metric="sharpe_ratio",
            method="grid",
        )

        result = optimizer.optimize(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
        )

        return result

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            "status": "ready",
            "config": {
                "data_dir": self.config.data_dir,
                "cache_dir": self.config.cache_dir,
                "initial_capital": self.config.initial_capital,
                "default_strategy": self.config.default_strategy,
            },
            "cache": self.cache.get_stats(),
            "timestamp": datetime.now().isoformat(),
        }


def create_system(config: Optional[SystemConfig] = None, **kwargs) -> QuantSystem:
    """
    Factory function to create QuantSystem.

    Args:
        config: SystemConfig object
        **kwargs: Override config values

    Returns:
        QuantSystem instance
    """
    if config is None:
        config = SystemConfig(**kwargs)

    return QuantSystem(config)


__all__ = [
    "QuantSystem",
    "SystemConfig",
    "BacktestResult",
    "LiveSignal",
    "create_system",
]
