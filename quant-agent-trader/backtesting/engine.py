"""
Backtesting Engine - Historical simulation engine for trading strategies.

This module provides the BacktestEngine class for running historical
simulations of multi-agent trading strategies with comprehensive
performance metrics calculation and equity curve generation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
import numpy as np
import logging

from signals.signal_schema import AgentSignal, AggregatedSignal, TradeResult
from agents.base_agent import BaseAgent
from signals.signal_aggregator import SignalAggregator
from config.settings import BacktestConfig

logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """Position direction enumeration."""

    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass
class BacktestPosition:
    """Represents a position during backtesting."""

    symbol: str
    side: PositionSide
    entry_price: float
    quantity: float
    entry_date: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class BacktestTrade:
    """Represents a completed trade in backtesting."""

    symbol: str
    entry_price: float
    exit_price: float
    quantity: float
    side: PositionSide
    entry_date: datetime
    exit_date: datetime
    pnl: float
    pnl_percent: float
    commission: float
    slippage: float
    return_percent: float
    holding_days: int


@dataclass
class BacktestMetrics:
    """Comprehensive performance metrics from backtesting."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    average_trade_return: float
    median_trade_return: float
    cumulative_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_percent: float
    calmar_ratio: float
    avg_holding_period: float
    total_commission: float
    total_slippage: float
    final_equity: float
    starting_capital: float


@dataclass
class BacktestResult:
    """Complete backtest result with equity curve and trades."""

    metrics: BacktestMetrics
    equity_curve: pd.DataFrame
    trades: List[BacktestTrade]
    daily_returns: pd.Series
    drawdown_series: pd.Series


@dataclass
class BacktestConfigExtended:
    """Extended backtest configuration."""

    initial_capital: float = 100000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    position_sizing_method: str = "fixed"
    max_position_size: float = 0.1
    risk_free_rate: float = 0.02
    trading_days_per_year: int = 252
    allow_shorting: bool = True
    exit_on_end: bool = True


class BacktestEngine:
    """
    Backtesting Engine for historical simulation of trading strategies.

    This engine supports:
    - Multiple symbols and agents
    - Configurable commission and slippage
    - Various position sizing methods
    - Comprehensive performance metrics
    - Equity curve generation

    Attributes:
        config: Backtest configuration
        aggregator: Signal aggregator for combining agent signals
    """

    def __init__(
        self,
        config: Optional[BacktestConfigExtended] = None,
        aggregator: Optional[SignalAggregator] = None,
    ):
        """
        Initialize the BacktestEngine.

        Args:
            config: Backtest configuration. Uses defaults if not provided.
            aggregator: Signal aggregator for combining agent signals.
        """
        self.config = config or BacktestConfigExtended()
        self.aggregator = aggregator or SignalAggregator()
        self._reset()

    def _reset(self) -> None:
        """Reset internal state for new backtest."""
        self.equity_curve: List[Dict] = []
        self.trades: List[BacktestTrade] = []
        self.positions: Dict[str, BacktestPosition] = {}
        self.current_equity: float = self.config.initial_capital
        self.cash: float = self.config.initial_capital
        self.total_commission: float = 0.0
        self.total_slippage: float = 0.0

    def run_backtest(
        self,
        data: Dict[str, pd.DataFrame],
        agents: List[BaseAgent],
        start_date: datetime,
        end_date: datetime,
        regime: str = "sideways",
    ) -> BacktestResult:
        """
        Run historical backtest for multiple symbols with multiple agents.

        Args:
            data: Dictionary mapping symbols to DataFrames with OHLCV data
            agents: List of trading agents to generate signals
            start_date: Start date for backtest
            end_date: End date for backtest

        Returns:
            BacktestResult containing metrics, equity curve, and trades
        """
        self._reset()

        logger.info(
            f"Starting backtest: {len(data)} symbols, {len(agents)} agents, "
            f"{start_date.date()} to {end_date.date()}"
        )

        all_dates = self._get_common_trading_dates(data, start_date, end_date)

        if not all_dates:
            logger.warning("No common trading dates found between symbols")
            return self._generate_results()

        for current_date in all_dates:
            self._process_date(
                data=data, agents=agents, current_date=current_date, regime=regime
            )

        if self.config.exit_on_end:
            self._close_all_positions(data, all_dates[-1])

        return self._generate_results()

    def _get_common_trading_dates(
        self, data: Dict[str, pd.DataFrame], start_date: datetime, end_date: datetime
    ) -> List[datetime]:
        """Get common trading dates across all symbols."""
        date_sets = []

        for symbol, df in data.items():
            if df.empty:
                continue

            symbol_dates = df.index[(df.index >= start_date) & (df.index <= end_date)]
            date_sets.append(set(symbol_dates))

        if not date_sets:
            return []

        common_dates = (
            set.intersection(*date_sets) if len(date_sets) > 1 else date_sets[0]
        )

        return sorted(list(common_dates))

    def _process_date(
        self,
        data: Dict[str, pd.DataFrame],
        agents: List[BaseAgent],
        current_date: datetime,
        regime: str,
    ) -> None:
        """Process a single date in the backtest."""
        current_prices = {}

        for symbol in data.keys():
            if current_date in data[symbol].index:
                current_prices[symbol] = data[symbol].loc[current_date, "close"]

        self._check_exit_conditions(data, current_date, current_prices)

        for symbol in data.keys():
            if symbol in self.positions:
                continue

            if current_date not in data[symbol].index:
                continue

            signals = self.generate_signals_for_symbol(
                data=data[symbol],
                agents=agents,
                current_date=current_date,
                symbol=symbol,
            )

            if signals:
                aggregated = self.aggregator.aggregate_signals(
                    signals=signals, regime=regime, stock_symbol=symbol
                )

                if aggregated.is_buy:
                    self._execute_entry(
                        symbol=symbol,
                        decision=aggregated.decision,
                        confidence=aggregated.confidence,
                        current_price=current_prices.get(symbol),
                        current_date=current_date,
                        data=data[symbol],
                    )

        self._update_equity(current_date, current_prices)

    def generate_signals_for_symbol(
        self,
        data: pd.DataFrame,
        agents: List[BaseAgent],
        current_date: datetime,
        symbol: str,
    ) -> List[AgentSignal]:
        """
        Generate trading signals for a symbol up to a specific date.

        Args:
            data: Historical price data for the symbol
            agents: List of agents to generate signals
            current_date: Current date in the backtest
            symbol: Stock symbol

        Returns:
            List of AgentSignal objects
        """
        if current_date not in data.index:
            return []

        historical_data = data.loc[:current_date]

        if len(historical_data) < 50:
            return []

        signals = []

        for agent in agents:
            try:
                features = self._prepare_features(historical_data)
                signal = agent.run(features, use_cache=False)
                signals.append(signal)
            except Exception as e:
                logger.warning(f"Agent {agent.agent_name} failed for {symbol}: {e}")
                continue

        return signals

    def generate_signals_for_period(
        self, data: pd.DataFrame, agents: List[BaseAgent], end_date: datetime
    ) -> List[AgentSignal]:
        """
        Generate signals for all data up to end_date.

        Args:
            data: Historical price data
            agents: List of agents
            end_date: End date for signal generation

        Returns:
            List of AgentSignal objects
        """
        if end_date not in data.index:
            end_date = data.index[data.index <= end_date][-1]

        historical_data = data.loc[:end_date]

        if len(historical_data) < 50:
            return []

        signals = []

        for agent in agents:
            try:
                features = self._prepare_features(historical_data)
                signal = agent.run(features, use_cache=False)
                signals.append(signal)
            except Exception as e:
                logger.warning(f"Agent {agent.agent_name} failed: {e}")
                continue

        return signals

    def _prepare_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Prepare features from price data for agent consumption.

        Uses pre-calculated features from TechnicalFeatures.calculate_all()
        if available, otherwise calculates basic features.
        """
        recent = data.iloc[-1]

        features = {
            "close": float(recent.get("close", recent.get("Price", 0))),
            "open": float(recent.get("open", recent.get("Open", 0))),
            "high": float(recent.get("high", recent.get("High", 0))),
            "low": float(recent.get("low", recent.get("Low", 0))),
            "volume": float(recent.get("volume", recent.get("Volume", 0))),
        }

        # Try to get all pre-calculated features from the dataframe
        for col in data.columns:
            if col not in ["open", "high", "low", "close", "volume", "date"]:
                try:
                    features[col] = float(recent[col])
                except (TypeError, KeyError):
                    pass

        # Fallback: calculate basic features if not already in dataframe
        if "sma_20" not in features and len(data) >= 20:
            features["sma_20"] = float(data["close"].iloc[-20:].mean())

        if "sma_50" not in features and len(data) >= 50:
            features["sma_50"] = float(data["close"].iloc[-50:].mean())

        if "rsi" not in features and len(data) >= 14:
            delta = data["close"].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            features["rsi"] = float((100 - (100 / (1 + rs))).iloc[-1])

        if "macd" not in features and len(data) >= 26:
            ema_12 = data["close"].ewm(span=12, adjust=False).mean()
            ema_26 = data["close"].ewm(span=26, adjust=False).mean()
            features["macd"] = float((ema_12 - ema_26).iloc[-1])
            features["macd_signal"] = float(
                (ema_12 - ema_26).ewm(span=9, adjust=False).mean().iloc[-1]
            )
            features["macd_hist"] = float((features["macd"] - features["macd_signal"]))

        # Add price position for RSI agent
        if len(data) >= 20:
            sma_20 = data["close"].rolling(20).mean().iloc[-1]
            features["price_position_20"] = (
                float((recent["close"] - sma_20) / sma_20) if sma_20 else 0.5
            )

        # Add ATR if not present
        if "atr" not in features and len(data) >= 14:
            high_low = data["high"] - data["low"]
            high_close = abs(data["high"] - data["close"].shift())
            low_close = abs(data["low"] - data["close"].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            features["atr"] = float(tr.rolling(14).mean().iloc[-1])

        return features

    def _execute_entry(
        self,
        symbol: str,
        decision: str,
        confidence: float,
        current_price: float,
        current_date: datetime,
        data: pd.DataFrame,
    ) -> None:
        """Execute a trade entry."""
        if symbol in self.positions:
            return

        position_size = self._calculate_position_size(
            confidence=confidence, current_price=current_price, symbol=symbol
        )

        if position_size <= 0:
            return

        slippage_cost = current_price * self.config.slippage_rate
        execution_price = current_price + slippage_cost

        commission_cost = execution_price * position_size * self.config.commission_rate

        if self.cash < (execution_price * position_size + commission_cost):
            logger.warning(f"Insufficient cash for {symbol}")
            return

        self.cash -= commission_cost
        self.total_commission += commission_cost
        self.total_slippage += slippage_cost * position_size

        atr = (
            self._calculate_atr(data, current_date)
            if len(data) >= 14
            else current_price * 0.02
        )

        stop_loss = execution_price * (1 - 2 * atr / current_price) if atr > 0 else None
        take_profit = (
            execution_price * (1 + 3 * atr / current_price) if atr > 0 else None
        )

        self.positions[symbol] = BacktestPosition(
            symbol=symbol,
            side=PositionSide.LONG if decision == "buy" else PositionSide.SHORT,
            entry_price=execution_price,
            quantity=position_size,
            entry_date=current_date,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        self.cash -= execution_price * position_size

    def _calculate_position_size(
        self, confidence: float, current_price: float, symbol: str
    ) -> float:
        """Calculate position size based on configuration."""
        if self.config.position_sizing_method == "fixed":
            base_size = self.config.initial_capital * 0.1
        elif self.config.position_sizing_method == "risk_based":
            base_size = self.cash * self.config.max_position_size * (confidence / 100)
        elif self.config.position_sizing_method == "kelly":
            base_size = self.cash * 0.25
        else:
            base_size = self.cash * self.config.max_position_size

        position_value = min(base_size, self.cash * self.config.max_position_size)

        return position_value / current_price if current_price > 0 else 0

    def _calculate_atr(self, data: pd.DataFrame, current_date: datetime) -> float:
        """Calculate Average True Range."""
        if current_date not in data.index:
            return 0.0

        window_data = data.loc[:current_date].iloc[-14:]

        if len(window_data) < 14:
            return 0.0

        high = window_data["high"]
        low = window_data["low"]
        close = window_data["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        return float(tr.mean())

    def _check_exit_conditions(
        self,
        data: Dict[str, pd.DataFrame],
        current_date: datetime,
        current_prices: Dict[str, float],
    ) -> None:
        """Check and execute exit conditions for open positions."""
        positions_to_close = []

        for symbol, position in self.positions.items():
            if symbol not in current_prices:
                continue

            current_price = current_prices[symbol]
            should_exit = False

            if position.side == PositionSide.LONG:
                if position.stop_loss and current_price <= position.stop_loss:
                    should_exit = True
                elif position.take_profit and current_price >= position.take_profit:
                    should_exit = True

            if should_exit:
                positions_to_close.append(symbol)

        for symbol in positions_to_close:
            self._execute_exit(
                symbol=symbol,
                exit_price=current_prices[symbol],
                exit_date=current_date,
                reason="signal",
            )

    def _execute_exit(
        self, symbol: str, exit_price: float, exit_date: datetime, reason: str
    ) -> None:
        """Execute a trade exit."""
        if symbol not in self.positions:
            return

        position = self.positions[symbol]

        slippage_cost = exit_price * self.config.slippage_rate
        execution_price = exit_price - slippage_cost

        commission_cost = (
            execution_price * position.quantity * self.config.commission_rate
        )

        entry_cost = position.entry_price * position.quantity
        exit_value = execution_price * position.quantity

        pnl = exit_value - entry_cost - commission_cost
        pnl_percent = (pnl / entry_cost) * 100 if entry_cost > 0 else 0

        trade = BacktestTrade(
            symbol=symbol,
            entry_price=position.entry_price,
            exit_price=execution_price,
            quantity=position.quantity,
            side=position.side,
            entry_date=position.entry_date,
            exit_date=exit_date,
            pnl=pnl,
            pnl_percent=pnl_percent,
            commission=commission_cost,
            slippage=slippage_cost * position.quantity,
            return_percent=pnl_percent,
            holding_days=(exit_date - position.entry_date).days,
        )

        self.trades.append(trade)

        self.cash += exit_value - commission_cost
        self.total_commission += commission_cost
        self.total_slippage += slippage_cost * position.quantity

        del self.positions[symbol]

    def _close_all_positions(
        self, data: Dict[str, pd.DataFrame], end_date: datetime
    ) -> None:
        """Close all open positions at the end of backtest."""
        for symbol in list(self.positions.keys()):
            if symbol in data and end_date in data[symbol].index:
                exit_price = data[symbol].loc[end_date, "close"]
                self._execute_exit(
                    symbol=symbol,
                    exit_price=exit_price,
                    exit_date=end_date,
                    reason="end_of_backtest",
                )

    def _update_equity(
        self, current_date: datetime, current_prices: Dict[str, float]
    ) -> None:
        """Update equity curve with current values."""
        positions_value = 0.0

        for symbol, position in self.positions.items():
            if symbol in current_prices:
                positions_value += position.quantity * current_prices[symbol]

        self.current_equity = self.cash + positions_value

        self.equity_curve.append(
            {
                "date": current_date,
                "equity": self.current_equity,
                "cash": self.cash,
                "positions_value": positions_value,
                "num_positions": len(self.positions),
            }
        )

    def simulate_trades(
        self,
        signals: Dict[str, AggregatedSignal],
        prices: pd.DataFrame,
        initial_capital: float,
    ) -> Tuple[List[BacktestTrade], List[Dict]]:
        """
        Simulate trades based on signals and price data.

        Args:
            signals: Dictionary mapping symbols to AggregatedSignal
            prices: DataFrame with price data indexed by date
            initial_capital: Starting capital

        Returns:
            Tuple of (list of trades, equity curve)
        """
        self._reset()

        trades = []
        equity_curve = []
        cash = initial_capital

        dates = sorted(prices.index)

        for i, date in enumerate(dates[:-1]):
            current_prices = prices.loc[date]
            next_date = dates[i + 1]

            for symbol, signal in signals.items():
                if symbol not in current_prices:
                    continue

                current_price = current_prices[symbol]

                if signal.is_buy and symbol not in self.positions:
                    position_size = min(
                        cash * signal.confidence / 100 * 0.1, cash * 0.1
                    )

                    if position_size > 0:
                        quantity = position_size / current_price
                        commission = (
                            quantity * current_price * self.config.commission_rate
                        )

                        cash -= commission
                        self.total_commission += commission

                        self.positions[symbol] = BacktestPosition(
                            symbol=symbol,
                            side=PositionSide.LONG,
                            entry_price=current_price,
                            quantity=quantity,
                            entry_date=date,
                        )

                elif signal.is_sell and symbol in self.positions:
                    position = self.positions[symbol]
                    exit_value = position.quantity * current_price
                    commission = exit_value * self.config.commission_rate

                    pnl = (
                        exit_value
                        - (position.entry_price * position.quantity)
                        - commission
                    )

                    trade = BacktestTrade(
                        symbol=symbol,
                        entry_price=position.entry_price,
                        exit_price=current_price,
                        quantity=position.quantity,
                        side=position.side,
                        entry_date=position.entry_date,
                        exit_date=date,
                        pnl=pnl,
                        pnl_percent=pnl
                        / (position.entry_price * position.quantity)
                        * 100,
                        commission=commission,
                        slippage=0.0,
                        return_percent=pnl
                        / (position.entry_price * position.quantity)
                        * 100,
                        holding_days=(date - position.entry_date).days,
                    )

                    trades.append(trade)
                    cash += exit_value - commission
                    self.cash = cash

                    del self.positions[symbol]

            positions_value = sum(
                pos.quantity * current_prices.get(pos.symbol, pos.entry_price)
                for pos in self.positions.values()
            )

            equity_curve.append(
                {
                    "date": date,
                    "equity": cash + positions_value,
                    "cash": cash,
                    "positions_value": positions_value,
                }
            )

        self.trades = trades
        self.equity_curve = equity_curve

        return trades, equity_curve

    def calculate_metrics(self, equity_curve: List[Dict]) -> BacktestMetrics:
        """
        Calculate comprehensive performance metrics from equity curve.

        Args:
            equity_curve: List of dictionaries with equity values

        Returns:
            BacktestMetrics with all performance calculations
        """
        if not equity_curve:
            return self._empty_metrics()

        equity_df = pd.DataFrame(equity_curve)
        equity_df.set_index("date", inplace=True)

        equity_values = equity_df["equity"].values
        returns = np.diff(equity_values) / equity_values[:-1]
        returns = returns[~np.isnan(returns)]

        if len(returns) == 0:
            return self._empty_metrics()

        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]

        total_wins = len(winning_trades)
        total_losses = len(losing_trades)
        total_trades = len(self.trades)

        win_rate = total_wins / total_trades if total_trades > 0 else 0.0

        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        trade_returns = [t.return_percent for t in self.trades]
        avg_trade_return = np.mean(trade_returns) if trade_returns else 0.0
        median_trade_return = np.median(trade_returns) if trade_returns else 0.0

        starting_equity = equity_values[0]
        final_equity = equity_values[-1]
        cumulative_return = (
            (final_equity - starting_equity) / starting_equity
            if starting_equity > 0
            else 0.0
        )

        num_years = len(equity_df) / self.config.trading_days_per_year
        annualized_return = (
            (1 + cumulative_return) ** (1 / num_years) - 1 if num_years > 0 else 0.0
        )

        annualized_volatility = (
            np.std(returns) * np.sqrt(self.config.trading_days_per_year)
            if len(returns) > 0
            else 0.0
        )

        risk_free_daily = self.config.risk_free_rate / self.config.trading_days_per_year
        excess_returns = returns - risk_free_daily

        sharpe_ratio = (
            np.mean(excess_returns)
            / np.std(excess_returns)
            * np.sqrt(self.config.trading_days_per_year)
            if np.std(excess_returns) > 0
            else 0.0
        )

        downside_returns = returns[returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 1.0

        sortino_ratio = (
            np.mean(excess_returns)
            / downside_std
            * np.sqrt(self.config.trading_days_per_year)
            if downside_std > 0
            else 0.0
        )

        running_max = np.maximum.accumulate(equity_values)
        drawdowns = (running_max - equity_values) / running_max
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0.0
        max_drawdown_value = max_drawdown * running_max[np.argmax(drawdowns)]

        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0.0

        holding_periods = [t.holding_days for t in self.trades]
        avg_holding_period = np.mean(holding_periods) if holding_periods else 0.0

        return BacktestMetrics(
            total_trades=total_trades,
            winning_trades=total_wins,
            losing_trades=total_losses,
            win_rate=win_rate,
            profit_factor=profit_factor,
            average_trade_return=avg_trade_return,
            median_trade_return=median_trade_return,
            cumulative_return=cumulative_return,
            annualized_return=annualized_return,
            annualized_volatility=annualized_volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_value,
            calmar_ratio=calmar_ratio,
            avg_holding_period=avg_holding_period,
            total_commission=self.total_commission,
            total_slippage=self.total_slippage,
            final_equity=final_equity,
            starting_capital=starting_equity,
        )

    def _empty_metrics(self) -> BacktestMetrics:
        """Return empty metrics when no data available."""
        return BacktestMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            average_trade_return=0.0,
            median_trade_return=0.0,
            cumulative_return=0.0,
            annualized_return=0.0,
            annualized_volatility=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            max_drawdown_percent=0.0,
            calmar_ratio=0.0,
            avg_holding_period=0.0,
            total_commission=0.0,
            total_slippage=0.0,
            final_equity=self.config.initial_capital,
            starting_capital=self.config.initial_capital,
        )

    def _generate_results(self) -> BacktestResult:
        """Generate complete backtest results."""
        metrics = self.calculate_metrics(self.equity_curve)

        equity_df = pd.DataFrame(self.equity_curve)

        if not equity_df.empty:
            equity_df.set_index("date", inplace=True)

            running_max = equity_df["equity"].expanding().max()
            drawdowns = (running_max - equity_df["equity"]) / running_max

            daily_returns = equity_df["equity"].pct_change().dropna()
        else:
            equity_df = pd.DataFrame(
                columns=["date", "equity", "cash", "positions_value", "num_positions"]
            )
            drawdowns = pd.Series(dtype=float)
            daily_returns = pd.Series(dtype=float)

        return BacktestResult(
            metrics=metrics,
            equity_curve=equity_df,
            trades=self.trades,
            daily_returns=daily_returns,
            drawdown_series=drawdowns,
        )

    def get_results_summary(self, result: BacktestResult) -> Dict[str, Any]:
        """
        Get summary of backtest results in readable format.

        Args:
            result: BacktestResult from run_backtest

        Returns:
            Dictionary with formatted summary
        """
        m = result.metrics

        return {
            "Performance Summary": {
                "Total Return": f"{m.cumulative_return * 100:.2f}%",
                "Annualized Return": f"{m.annualized_return * 100:.2f}%",
                "Annualized Volatility": f"{m.annualized_volatility * 100:.2f}%",
                "Sharpe Ratio": f"{m.sharpe_ratio:.2f}",
                "Sortino Ratio": f"{m.sortino_ratio:.2f}",
                "Calmar Ratio": f"{m.calmar_ratio:.2f}",
            },
            "Risk Metrics": {
                "Max Drawdown": f"{m.max_drawdown * 100:.2f}%",
                "Max Drawdown Value": f"₹{m.max_drawdown_percent:.2f}",
            },
            "Trade Statistics": {
                "Total Trades": m.total_trades,
                "Winning Trades": m.winning_trades,
                "Losing Trades": m.losing_trades,
                "Win Rate": f"{m.win_rate * 100:.2f}%",
                "Profit Factor": f"{m.profit_factor:.2f}",
                "Avg Trade Return": f"{m.average_trade_return:.2f}%",
                "Avg Holding Period": f"{m.avg_holding_period:.1f} days",
            },
            "Costs": {
                "Total Commission": f"₹{m.total_commission:.2f}",
                "Total Slippage": f"₹{m.total_slippage:.2f}",
            },
            "Capital": {
                "Starting Capital": f"₹{m.starting_capital:,.2f}",
                "Final Equity": f"₹{m.final_equity:,.2f}",
            },
        }

    def plot_equity_curve(
        self, result: BacktestResult, benchmark: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """
        Generate equity curve DataFrame for plotting.

        Args:
            result: BacktestResult from run_backtest
            benchmark: Optional benchmark returns for comparison

        Returns:
            DataFrame ready for plotting
        """
        plot_df = result.equity_curve.copy()

        if not plot_df.empty:
            plot_df["equity_normalized"] = (
                plot_df["equity"] / plot_df["equity"].iloc[0] * 100
            )

            if benchmark is not None:
                plot_df["benchmark_normalized"] = benchmark / benchmark.iloc[0] * 100

        return plot_df

    def export_trades_csv(self, result: BacktestResult, filepath: str) -> None:
        """
        Export trades to CSV file.

        Args:
            result: BacktestResult from run_backtest
            filepath: Path to save CSV file
        """
        trades_data = []

        for trade in result.trades:
            trades_data.append(
                {
                    "symbol": trade.symbol,
                    "entry_date": trade.entry_date,
                    "exit_date": trade.exit_date,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "quantity": trade.quantity,
                    "side": trade.side.value,
                    "pnl": trade.pnl,
                    "pnl_percent": trade.pnl_percent,
                    "commission": trade.commission,
                    "slippage": trade.slippage,
                    "holding_days": trade.holding_days,
                }
            )

        trades_df = pd.DataFrame(trades_data)
        trades_df.to_csv(filepath, index=False)

        logger.info(f"Exported {len(trades_data)} trades to {filepath}")

    def export_equity_csv(self, result: BacktestResult, filepath: str) -> None:
        """
        Export equity curve to CSV file.

        Args:
            result: BacktestResult from run_backtest
            filepath: Path to save CSV file
        """
        result.equity_curve.to_csv(filepath)

        logger.info(f"Exported equity curve to {filepath}")
