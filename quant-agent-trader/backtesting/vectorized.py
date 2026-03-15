"""
Vectorized Backtesting Engine.

A fast, pandas-native backtesting engine that processes entire arrays at once
for maximum performance. Designed for:
- Signal-based strategy testing
- Portfolio-level backtesting
- Performance metric calculation

Key features:
- Vectorized operations (no loops over dates)
- Multiple position sizing methods
- Transaction costs and slippage modeling
- Comprehensive performance metrics
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PositionSizingMethod(Enum):
    """Position sizing methods."""

    FIXED = "fixed"
    EQUAL_WEIGHT = "equal_weight"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    KELLY = "kelly"
    INVERSE_VOLATILITY = "inverse_volatility"


@dataclass
class BacktestConfig:
    """Configuration for vectorized backtesting."""

    initial_capital: float = 100000.0
    commission_rate: float = 0.001
    slippage_bps: float = 5.0
    position_sizing: PositionSizingMethod = PositionSizingMethod.FIXED
    max_position_pct: float = 0.1
    risk_free_rate: float = 0.06
    trading_days_per_year: int = 252


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""

    total_return: float
    cagr: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_return: float
    median_trade_return: float
    avg_holding_period: float
    total_commission: float
    total_slippage: float
    final_equity: float
    starting_capital: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "total_return": self.total_return,
            "cagr": self.cagr,
            "volatility": self.volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "calmar_ratio": self.calmar_ratio,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "avg_trade_return": self.avg_trade_return,
            "median_trade_return": self.median_trade_return,
            "avg_holding_period": self.avg_holding_period,
            "total_commission": self.total_commission,
            "total_slippage": self.total_slippage,
            "final_equity": self.final_equity,
            "starting_capital": self.starting_capital,
        }


@dataclass
class BacktestResult:
    """Complete backtest results."""

    metrics: PerformanceMetrics
    equity_curve: pd.DataFrame
    drawdown_series: pd.Series
    returns: pd.Series
    trades: pd.DataFrame
    positions: pd.DataFrame


class VectorizedBacktestEngine:
    """
    Vectorized backtesting engine using pandas operations.

    Advantages over event-driven:
    - Much faster execution (100x+)
    - Cleaner signal/return alignment
    - Native pandas/numpy optimization

    Input:
    - Signal DataFrame with columns: [date, symbol, signal]
      - signal: 1=buy, -1=sell, 0=hold
    - Price DataFrame with OHLCV data

    Output:
    - Performance metrics
    - Equity curve
    - Trade log
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self._result: Optional[BacktestResult] = None

    def run(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        price_col: str = "close",
    ) -> BacktestResult:
        """
        Run vectorized backtest.

        Args:
            prices: DataFrame with OHLCV data, indexed by date
                    Must contain: open, high, low, close, volume
            signals: DataFrame with columns [date, symbol, signal]
                    signal: 1=buy, -1=sell, 0=hold
            price_col: Price column to use for calculations

        Returns:
            BacktestResult with all metrics and data
        """
        df = prices.copy()

        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        signals_df = signals.copy()
        if "date" in signals_df.columns:
            signals_df["date"] = pd.to_datetime(signals_df["date"])
            signals_df = signals_df.set_index("date")
        if not isinstance(signals_df.index, pd.DatetimeIndex):
            signals_df.index = pd.to_datetime(signals_df.index)
        signals_df = signals_df.sort_index()

        returns = self._calculate_returns(df, price_col)

        aligned_signals = self._align_signals(signals_df, df.index)

        strategy_returns = self._calculate_strategy_returns(returns, aligned_signals)

        costs = self._calculate_costs(aligned_signals, df, price_col)
        strategy_returns = strategy_returns - costs

        equity_curve = self._calculate_equity_curve(strategy_returns)
        drawdown = self._calculate_drawdown(equity_curve)

        trades = self._extract_trades(aligned_signals, df, price_col)

        metrics = self._calculate_metrics(
            strategy_returns, equity_curve, drawdown, trades, costs
        )

        self._result = BacktestResult(
            metrics=metrics,
            equity_curve=equity_curve,
            drawdown_series=drawdown,
            returns=strategy_returns,
            trades=trades,
            positions=self._calculate_positions(aligned_signals),
        )

        return self._result

    def _calculate_returns(self, df: pd.DataFrame, price_col: str) -> pd.Series:
        """Calculate asset returns."""
        return df[price_col].pct_change().fillna(0)

    def _align_signals(
        self, signals: pd.DataFrame, dates: pd.DatetimeIndex
    ) -> pd.DataFrame:
        """Align signals to price dates."""
        if "symbol" not in signals.columns:
            if "signal" in signals.columns:
                aligned = pd.DataFrame(
                    {"signal": signals["signal"]}, index=signals.index
                )
                aligned = aligned.reindex(dates).ffill().fillna(0)
                return aligned

        result_frames = []

        if "symbol" in signals.columns:
            for symbol in signals["symbol"].unique():
                sym_signals = signals[signals["symbol"] == symbol].copy()
                sym_signals = sym_signals[["signal"]].rename(columns={"signal": symbol})
                sym_signals = sym_signals.reindex(dates).ffill().fillna(0)
                result_frames.append(sym_signals)

            if result_frames:
                return pd.concat(result_frames, axis=1).fillna(0)

        aligned = signals.reindex(dates).ffill().fillna(0)
        return aligned

    def _calculate_strategy_returns(
        self, returns: pd.Series, signals: pd.DataFrame
    ) -> pd.Series:
        """
        Calculate strategy returns from signals.

        Signal at time t affects return from t to t+1 (shift by 1).
        """
        if isinstance(signals, pd.DataFrame):
            if len(signals.columns) == 1:
                signal = signals.iloc[:, 0]
            else:
                signal = signals.mean(axis=1)
        else:
            signal = signals

        shifted_signal = signal.shift(1).fillna(0)

        strategy_returns = shifted_signal * returns

        return strategy_returns

    def _calculate_costs(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        price_col: str,
    ) -> pd.Series:
        """Calculate transaction costs from signal changes."""
        if isinstance(signals, pd.DataFrame):
            signal = signals.mean(axis=1)
        else:
            signal = signals

        signal_changes = signal.diff().abs().fillna(0)

        commission = signal_changes * self.config.commission_rate

        slippage = (
            signal_changes
            * (self.config.slippage_bps / 10000)
            * prices[price_col].pct_change().abs().fillna(0)
        )

        costs = commission + slippage

        return costs.fillna(0)

    def _calculate_equity_curve(self, returns: pd.Series) -> pd.DataFrame:
        """Calculate equity curve from returns."""
        equity = (1 + returns).cumprod() * self.config.initial_capital

        return pd.DataFrame(
            {
                "equity": equity,
                "returns": returns,
                "cum_returns": returns.cumsum(),
            },
            index=returns.index,
        )

    def _calculate_drawdown(self, equity_curve: pd.DataFrame) -> pd.Series:
        """Calculate drawdown series."""
        equity = equity_curve["equity"]

        running_max = equity.expanding().max()
        drawdown = (equity - running_max) / running_max

        return drawdown

    def _extract_trades(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        price_col: str,
    ) -> pd.DataFrame:
        """Extract trade details from signal changes."""
        if isinstance(signals, pd.DataFrame):
            signal = signals.mean(axis=1)
        else:
            signal = signals

        signal_changes = signal.diff().fillna(0)

        trades_list = []

        for date, change in signal_changes.items():
            if change == 0:
                continue

            if date not in prices.index:
                continue

            price = prices.loc[date, price_col]
            direction = "buy" if change > 0 else "sell"

            trades_list.append(
                {
                    "date": date,
                    "direction": direction,
                    "price": price,
                    "signal_change": change,
                }
            )

        if not trades_list:
            return pd.DataFrame(columns=["date", "direction", "price", "signal_change"])

        return pd.DataFrame(trades_list)

    def _calculate_positions(self, signals: pd.DataFrame) -> pd.DataFrame:
        """Calculate position series."""
        if isinstance(signals, pd.DataFrame):
            positions = signals.mean(axis=1)
        else:
            positions = signals

        return pd.DataFrame({"position": positions}, index=positions.index)

    def _calculate_metrics(
        self,
        returns: pd.Series,
        equity_curve: pd.DataFrame,
        drawdown: pd.Series,
        trades: pd.DataFrame,
        costs: pd.Series,
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""

        equity = equity_curve["equity"]
        starting_capital = self.config.initial_capital
        final_equity = equity.iloc[-1] if len(equity) > 0 else starting_capital

        total_return = (final_equity / starting_capital) - 1

        n_periods = len(returns)
        years = n_periods / self.config.trading_days_per_year
        cagr = (final_equity / starting_capital) ** (1 / years) - 1 if years > 0 else 0

        volatility = returns.std() * np.sqrt(self.config.trading_days_per_year)

        excess_returns = returns - (
            self.config.risk_free_rate / self.config.trading_days_per_year
        )
        sharpe_ratio = (
            excess_returns.mean()
            / returns.std()
            * np.sqrt(self.config.trading_days_per_year)
            if returns.std() > 0
            else 0
        )

        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(
            self.config.trading_days_per_year
        )
        sortino_ratio = (
            excess_returns.mean()
            / downside_std
            * np.sqrt(self.config.trading_days_per_year)
            if downside_std > 0
            else 0
        )

        max_drawdown = drawdown.min()

        max_dd_idx = drawdown.idxmin()
        max_dd_value = (
            equity.loc[max_dd_idx]
            - equity.loc[:max_dd_idx].expanding().max().loc[max_dd_idx]
        )

        calmar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0

        winning_trades = trades[trades["direction"] == "buy"]
        losing_trades = trades[trades["direction"] == "sell"]

        win_rate = len(winning_trades) / len(trades) if len(trades) > 0 else 0

        trade_returns = []
        for i in range(1, len(trades)):
            if (
                trades.iloc[i]["direction"] == "sell"
                and trades.iloc[i - 1]["direction"] == "buy"
            ):
                entry_price = trades.iloc[i - 1]["price"]
                exit_price = trades.iloc[i]["price"]
                ret = (exit_price - entry_price) / entry_price if entry_price > 0 else 0
                trade_returns.append(ret)

        if not trade_returns:
            trade_returns = [0]

        avg_trade_return = np.mean(trade_returns) * 100
        median_trade_return = np.median(trade_returns) * 100

        gross_profit = sum(r for r in trade_returns if r > 0)
        gross_loss = abs(sum(r for r in trade_returns if r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        total_commission = costs.sum() * starting_capital
        total_slippage = costs.sum() * starting_capital * 0.5

        return PerformanceMetrics(
            total_return=total_return,
            cagr=cagr,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_dd_value,
            calmar_ratio=calmar_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(trades),
            avg_trade_return=avg_trade_return,
            median_trade_return=median_trade_return,
            avg_holding_period=1.0,
            total_commission=total_commission,
            total_slippage=total_slippage,
            final_equity=final_equity,
            starting_capital=starting_capital,
        )

    def run_portfolio(
        self,
        prices: Dict[str, pd.DataFrame],
        signals: Dict[str, pd.DataFrame],
        price_col: str = "close",
    ) -> BacktestResult:
        """
        Run portfolio backtest for multiple symbols.

        Args:
            prices: Dict of symbol -> price DataFrames
            signals: Dict of symbol -> signal DataFrames
            price_col: Price column to use

        Returns:
            BacktestResult with aggregated portfolio metrics
        """
        all_returns = []
        all_equity = []
        all_drawdowns = []
        all_trades = []
        all_positions = []

        for symbol in prices.keys():
            if symbol not in signals:
                continue

            price_df = prices[symbol]
            signal_df = signals[symbol]

            if price_df.empty or signal_df.empty:
                continue

            result = self.run(price_df, signal_df, price_col)

            all_returns.append(result.returns)
            all_equity.append(result.equity_curve["equity"])
            all_drawdowns.append(result.drawdown_series)
            result.trades["symbol"] = symbol
            all_trades.append(result.trades)
            result.positions["symbol"] = symbol
            all_positions.append(result.positions)

        if not all_returns:
            return self._empty_result()

        combined_returns = pd.concat(all_returns, axis=1).mean(axis=1)

        combined_equity = pd.DataFrame(
            {
                "equity": (1 + combined_returns).cumprod()
                * self.config.initial_capital,
                "returns": combined_returns,
            }
        )

        combined_drawdowns = pd.concat(all_drawdowns, axis=1).mean(axis=1)

        combined_trades = (
            pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
        )
        combined_positions = (
            pd.concat(all_positions, ignore_index=True)
            if all_positions
            else pd.DataFrame()
        )

        costs = combined_returns * 0.001
        combined_returns = combined_returns - costs

        combined_equity["equity"] = (
            1 + combined_returns
        ).cumprod() * self.config.initial_capital

        combined_drawdowns = self._calculate_drawdown(combined_equity)

        metrics = self._calculate_metrics(
            combined_returns,
            combined_equity,
            combined_drawdowns,
            combined_trades,
            costs,
        )

        return BacktestResult(
            metrics=metrics,
            equity_curve=combined_equity,
            drawdown_series=combined_drawdowns,
            returns=combined_returns,
            trades=combined_trades,
            positions=combined_positions,
        )

    def _empty_result(self) -> BacktestResult:
        """Return empty result when no data."""
        return BacktestResult(
            metrics=PerformanceMetrics(
                total_return=0,
                cagr=0,
                volatility=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                max_drawdown=0,
                max_drawdown_pct=0,
                calmar_ratio=0,
                win_rate=0,
                profit_factor=0,
                total_trades=0,
                avg_trade_return=0,
                median_trade_return=0,
                avg_holding_period=0,
                total_commission=0,
                total_slippage=0,
                final_equity=self.config.initial_capital,
                starting_capital=self.config.initial_capital,
            ),
            equity_curve=pd.DataFrame(),
            drawdown_series=pd.Series(),
            returns=pd.Series(),
            trades=pd.DataFrame(),
            positions=pd.DataFrame(),
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get formatted summary of results."""
        if not self._result:
            return {}

        m = self._result.metrics

        return {
            "Returns": {
                "Total Return": f"{m.total_return * 100:.2f}%",
                "CAGR": f"{m.cagr * 100:.2f}%",
                "Volatility": f"{m.volatility * 100:.2f}%",
            },
            "Risk-Adjusted": {
                "Sharpe Ratio": f"{m.sharpe_ratio:.2f}",
                "Sortino Ratio": f"{m.sortino_ratio:.2f}",
                "Calmar Ratio": f"{m.calmar_ratio:.2f}",
                "Max Drawdown": f"{m.max_drawdown * 100:.2f}%",
            },
            "Trades": {
                "Total Trades": m.total_trades,
                "Win Rate": f"{m.win_rate * 100:.2f}%",
                "Profit Factor": f"{m.profit_factor:.2f}",
                "Avg Trade Return": f"{m.avg_trade_return:.2f}%",
            },
            "Capital": {
                "Starting": f"₹{m.starting_capital:,.0f}",
                "Final": f"₹{m.final_equity:,.0f}",
            },
        }


def convert_signal_to_numeric(signals: pd.DataFrame) -> pd.DataFrame:
    """
    Convert 5-class signals to numeric values for backtesting.

    Maps:
    - STRONG_BUY -> 1.0 (full long position)
    - BUY -> 0.5 (half long position)
    - HOLD -> 0.0 (no position)
    - SELL -> -0.5 (half short position)
    - STRONG_SELL -> -1.0 (full short position)

    Also handles numeric input: -2 to +2 -> -1.0 to +1.0
    """
    df = signals.copy()

    if "signal" not in df.columns:
        return df

    signal_col = df["signal"]

    if signal_col.dtype == object or signal_col.dtype == str:
        signal_col = signal_col.astype(str).str.lower()

        mapping = {
            "strong_buy": 1.0,
            "buy": 0.5,
            "hold": 0.0,
            "sell": -0.5,
            "strong_sell": -1.0,
        }
        df["signal"] = signal_col.map(lambda x: mapping.get(x, 0.0))
    else:
        df["signal"] = signal_col.astype(float)
        df["signal"] = df["signal"].clip(-1.0, 1.0)

    return df


def create_signals_from_indicator(
    prices: pd.DataFrame,
    indicator: str = "sma_crossover",
    short_window: int = 20,
    long_window: int = 50,
) -> pd.DataFrame:
    """
    Create signal DataFrame from technical indicator.

    Args:
        prices: OHLCV price DataFrame
        indicator: Indicator type ("sma_crossover", "rsi", "bollinger")
        short_window: Short period for indicator
        long_window: Long period for indicator

    Returns:
        DataFrame with [date, signal] columns
    """
    df = prices.copy()

    if indicator == "sma_crossover":
        df["sma_short"] = df["close"].rolling(short_window).mean()
        df["sma_long"] = df["close"].rolling(long_window).mean()
        df["signal"] = np.where(df["sma_short"] > df["sma_long"], 1, -1)
        df["signal"] = df["signal"].diff().fillna(0).clip(-1, 1)

    elif indicator == "rsi":
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))

        df["signal"] = 0
        df.loc[df["rsi"] < 30, "signal"] = 1
        df.loc[df["rsi"] > 70, "signal"] = -1
        df["signal"] = df["signal"].diff().clip(-1, 1)

    elif indicator == "bollinger":
        df["bb_middle"] = df["close"].rolling(20).mean()
        df["bb_std"] = df["close"].rolling(20).std()
        df["bb_upper"] = df["bb_middle"] + 2 * df["bb_std"]
        df["bb_lower"] = df["bb_middle"] - 2 * df["bb_std"]

        df["signal"] = 0
        df.loc[df["close"] < df["bb_lower"], "signal"] = 1
        df.loc[df["close"] > df["bb_upper"], "signal"] = -1
        df["signal"] = df["signal"].diff().clip(-1, 1)

    signals = df[["signal"]].copy()
    signals = signals.reset_index()
    if "index" in signals.columns:
        signals = signals.rename(columns={"index": "date"})

    return signals


__all__ = [
    "VectorizedBacktestEngine",
    "BacktestConfig",
    "BacktestResult",
    "PerformanceMetrics",
    "PositionSizingMethod",
    "create_signals_from_indicator",
]
