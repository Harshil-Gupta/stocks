"""
Backtesting Module - Historical simulation engine for trading strategies.

Provides:
- BacktestEngine: Event-driven backtesting
- VectorizedBacktestEngine: Fast pandas-native backtesting
"""

from backtesting.engine import (
    BacktestEngine,
    BacktestConfigExtended,
    BacktestMetrics,
    BacktestResult,
    BacktestTrade,
    BacktestPosition,
    PositionSide,
)

from backtesting.vectorized import (
    VectorizedBacktestEngine,
    BacktestConfig,
    PerformanceMetrics,
    PositionSizingMethod,
    create_signals_from_indicator,
)

__all__ = [
    "BacktestEngine",
    "BacktestConfigExtended",
    "BacktestMetrics",
    "BacktestResult",
    "BacktestTrade",
    "BacktestPosition",
    "PositionSide",
    "VectorizedBacktestEngine",
    "BacktestConfig",
    "PerformanceMetrics",
    "PositionSizingMethod",
    "create_signals_from_indicator",
]
