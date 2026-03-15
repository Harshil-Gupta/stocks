"""
Strategy Module - Trading strategy implementations and plugin system.

Provides:
- BaseStrategy interface
- Strategy implementations (MA Crossover, RSI, Breakout, Momentum, Bollinger)
- StrategyRegistry for plugin discovery
- Strategy ensemble (voting, weighted)
- CLI integration

Usage:
    from strategies import create_strategy, list_available_strategies

    # Create strategy
    strategy = create_strategy("ma_crossover", short_window=20, long_window=50)

    # Generate signals
    signals = strategy.generate_signals(price_data)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Union
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
import logging
import argparse

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Trading signal types with 5-level classification."""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

    @property
    def direction(self) -> int:
        """Convert signal to position direction (-2 to +2)."""
        mapping = {
            SignalType.STRONG_BUY: 2,
            SignalType.BUY: 1,
            SignalType.HOLD: 0,
            SignalType.SELL: -1,
            SignalType.STRONG_SELL: -2,
        }
        return mapping.get(self, 0)

    @property
    def is_buy(self) -> bool:
        return self in (SignalType.BUY, SignalType.STRONG_BUY)

    @property
    def is_sell(self) -> bool:
        return self in (SignalType.SELL, SignalType.STRONG_SELL)


@dataclass
class Signal:
    """Trading signal output."""

    signal: SignalType
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal": self.signal.value,
            "confidence": self.confidence,
            **self.metadata,
        }


@dataclass
class StrategyConfig:
    """Configuration for a trading strategy."""

    name: str
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    risk_limits: Dict[str, float] = field(default_factory=dict)


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.

    All strategies must implement:
    - generate_signals()
    - validate_parameters()
    """

    def __init__(self, config: Optional[StrategyConfig] = None, **params):
        if config is None:
            config = StrategyConfig(name=self.__class__.__name__)

        self.config = config
        self.name = config.name
        self.params = {**config.parameters, **params}
        self.risk_limits = config.risk_limits
        self._is_initialized = False
        self._data_cache = {}

    @abstractmethod
    def generate_signals(self, data: Union[pd.DataFrame, pd.Series]) -> Signal:
        """
        Generate trading signals from market data.

        Args:
            data: Market data (OHLCV DataFrame)

        Returns:
            Signal object with signal type, confidence, and metadata
        """
        pass

    def validate_parameters(self) -> bool:
        """Validate strategy parameters."""
        return True

    def initialize(self) -> None:
        """Initialize strategy."""
        if not self.validate_parameters():
            raise ValueError(f"Invalid parameters for strategy {self.name}")
        self._is_initialized = True
        logger.info(f"Initialized strategy: {self.name}")

    def get_required_columns(self) -> List[str]:
        """List columns required by this strategy."""
        return ["close"]

    def __call__(self, data: Union[pd.DataFrame, pd.Series]) -> Signal:
        """Convenience method to generate signals."""
        if not self._is_initialized:
            self.initialize()
        return self.generate_signals(data)


class MACrossoverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy.

    Buy when short MA crosses above long MA, sell when it crosses below.
    """

    def __init__(self, short_window: int = 20, long_window: int = 50, **kwargs):
        super().__init__(**kwargs)
        self.short_window = self.params.get("short_window", short_window)
        self.long_window = self.params.get("long_window", long_window)

    def validate_parameters(self) -> bool:
        return self.short_window > 0 and self.long_window > self.short_window

    def generate_signals(self, data: Union[pd.DataFrame, pd.Series]) -> Signal:
        if not self._is_initialized:
            self.initialize()

        if isinstance(data, pd.Series):
            close = data
            df = pd.DataFrame({"close": data})
        else:
            df = data
            close = df["close"]

        short_ma = close.rolling(self.short_window).mean()
        long_ma = close.rolling(self.long_window).mean()

        current_short = short_ma.iloc[-1]
        current_long = long_ma.iloc[-1]
        prev_short = short_ma.iloc[-2]
        prev_long = long_ma.iloc[-2]

        if pd.isna(current_short) or pd.isna(current_long):
            return Signal(SignalType.HOLD, 50.0, {"reason": "insufficient_data"})

        if prev_short <= prev_long and current_short > current_long:
            distance = (current_short - current_long) / current_long
            confidence = min(50 + distance * 500, 95)

            # 5-level classification based on crossover strength
            if distance > 0.02:
                signal_type = SignalType.STRONG_BUY
            elif distance > 0.01:
                signal_type = SignalType.BUY
            else:
                signal_type = SignalType.BUY

            return Signal(
                signal_type,
                confidence,
                {
                    "short_ma": current_short,
                    "long_ma": current_long,
                    "crossover": "bullish",
                    "strength": "strong" if distance > 0.02 else "moderate",
                },
            )

        elif prev_short >= prev_long and current_short < current_long:
            distance = (current_long - current_short) / current_short
            confidence = min(50 + distance * 500, 95)

            # 5-level classification based on crossover strength
            if distance > 0.02:
                signal_type = SignalType.STRONG_SELL
            elif distance > 0.01:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.SELL

            return Signal(
                signal_type,
                confidence,
                {
                    "short_ma": current_short,
                    "long_ma": current_long,
                    "crossover": "bearish",
                    "strength": "strong" if distance > 0.02 else "moderate",
                },
            )

        return Signal(
            SignalType.HOLD, 50.0, {"short_ma": current_short, "long_ma": current_long}
        )


class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI Mean Reversion Strategy.

    Buy when oversold (RSI < 30), sell when overbought (RSI > 70).
    """

    def __init__(
        self, period: int = 14, oversold: float = 30, overbought: float = 70, **kwargs
    ):
        super().__init__(**kwargs)
        self.period = self.params.get("period", period)
        self.oversold = self.params.get("oversold", oversold)
        self.overbought = self.params.get("overbought", overbought)

    def validate_parameters(self) -> bool:
        return self.period > 0 and self.oversold < self.overbought

    def get_required_columns(self) -> List[str]:
        return ["close"]

    def _calculate_rsi(self, close: pd.Series) -> float:
        """Calculate RSI."""
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.period).mean()

        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def generate_signals(self, data: Union[pd.DataFrame, pd.Series]) -> Signal:
        if not self._is_initialized:
            self.initialize()

        if isinstance(data, pd.Series):
            close = data
        else:
            close = data["close"]

        rsi = self._calculate_rsi(close)

        if pd.isna(rsi):
            return Signal(SignalType.HOLD, 50.0, {"reason": "insufficient_data"})

        if rsi < self.oversold:
            distance = (self.oversold - rsi) / self.oversold
            confidence = min(60 + distance * 40, 95)

            # 5-level classification
            if rsi < 15:
                signal_type = SignalType.STRONG_BUY
            else:
                signal_type = SignalType.BUY

            return Signal(
                signal_type,
                confidence,
                {
                    "rsi": rsi,
                    "zone": "oversold",
                    "severity": "extreme" if rsi < 15 else "moderate",
                },
            )

        elif rsi > self.overbought:
            distance = (rsi - self.overbought) / (100 - self.overbought)
            confidence = min(60 + distance * 40, 95)

            # 5-level classification
            if rsi > 85:
                signal_type = SignalType.STRONG_SELL
            else:
                signal_type = SignalType.SELL

            return Signal(
                signal_type,
                confidence,
                {
                    "rsi": rsi,
                    "zone": "overbought",
                    "severity": "extreme" if rsi > 85 else "moderate",
                },
            )

        return Signal(SignalType.HOLD, 50.0, {"rsi": rsi, "zone": "neutral"})


class BreakoutStrategy(BaseStrategy):
    """
    Breakout Strategy.

    Buy when price breaks above recent high, sell when breaks below recent low.
    """

    def __init__(self, lookback: int = 20, **kwargs):
        super().__init__(**kwargs)
        self.lookback = self.params.get("lookback", lookback)

    def validate_parameters(self) -> bool:
        return self.lookback > 0

    def get_required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def generate_signals(self, data: Union[pd.DataFrame, pd.Series]) -> Signal:
        if not self._is_initialized:
            self.initialize()

        if isinstance(data, pd.Series):
            return Signal(SignalType.HOLD, 50.0, {"reason": "requires_ohlc"})

        close = data["close"]
        high = data["high"]
        low = data["low"]

        rolling_high = high.rolling(self.lookback).max()
        rolling_low = low.rolling(self.lookback).min()

        current_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        current_high = rolling_high.iloc[-1]
        prev_high = rolling_high.iloc[-2]
        current_low = rolling_low.iloc[-1]

        if pd.isna(current_high):
            return Signal(SignalType.HOLD, 50.0, {"reason": "insufficient_data"})

        if prev_close <= prev_high and current_close > current_high:
            distance = (current_close - current_high) / current_high
            confidence = min(60 + distance * 400, 95)

            # 5-level classification
            if distance > 0.03:
                signal_type = SignalType.STRONG_BUY
            else:
                signal_type = SignalType.BUY

            return Signal(
                signal_type,
                confidence,
                {
                    "breakout_level": current_high,
                    "type": "upper_breakout",
                    "strength": "strong" if distance > 0.03 else "moderate",
                },
            )

        elif prev_close >= rolling_low.iloc[-2] and current_close < current_low:
            distance = (current_low - current_close) / current_close
            confidence = min(60 + distance * 400, 95)

            # 5-level classification
            if distance > 0.03:
                signal_type = SignalType.STRONG_SELL
            else:
                signal_type = SignalType.SELL

            return Signal(
                signal_type,
                confidence,
                {
                    "breakout_level": current_low,
                    "type": "lower_breakout",
                    "strength": "strong" if distance > 0.03 else "moderate",
                },
            )

        return Signal(SignalType.HOLD, 50.0, {"high": current_high, "low": current_low})


class MomentumStrategy(BaseStrategy):
    """
    Momentum Strategy.

    Buy when price momentum is positive and strong, sell when negative.
    """

    def __init__(self, lookback: int = 20, threshold: float = 0.05, **kwargs):
        super().__init__(**kwargs)
        self.lookback = self.params.get("lookback", lookback)
        self.threshold = self.params.get("threshold", threshold)

    def validate_parameters(self) -> bool:
        return self.lookback > 0

    def get_required_columns(self) -> List[str]:
        return ["close"]

    def generate_signals(self, data: Union[pd.DataFrame, pd.Series]) -> Signal:
        if not self._is_initialized:
            self.initialize()

        if isinstance(data, pd.Series):
            close = data
        else:
            close = data["close"]

        momentum = close.pct_change(self.lookback).iloc[-1]

        if pd.isna(momentum):
            return Signal(SignalType.HOLD, 50.0, {"reason": "insufficient_data"})

        if momentum > self.threshold:
            confidence = min(50 + abs(momentum) * 500, 95)

            # 5-level classification based on momentum strength
            if momentum > self.threshold * 2:
                signal_type = SignalType.STRONG_BUY
            else:
                signal_type = SignalType.BUY

            return Signal(
                signal_type,
                confidence,
                {
                    "momentum": momentum,
                    "threshold": self.threshold,
                    "strength": "strong"
                    if momentum > self.threshold * 2
                    else "moderate",
                },
            )

        elif momentum < -self.threshold:
            confidence = min(50 + abs(momentum) * 500, 95)

            # 5-level classification
            if momentum < -self.threshold * 2:
                signal_type = SignalType.STRONG_SELL
            else:
                signal_type = SignalType.SELL

            return Signal(
                signal_type,
                confidence,
                {
                    "momentum": momentum,
                    "threshold": self.threshold,
                    "strength": "strong"
                    if abs(momentum) > self.threshold * 2
                    else "moderate",
                },
            )

        return Signal(SignalType.HOLD, 50.0, {"momentum": momentum})


class BollingerBandStrategy(BaseStrategy):
    """
    Bollinger Band Strategy.

    Buy at lower band, sell at upper band.
    """

    def __init__(self, period: int = 20, num_std: float = 2.0, **kwargs):
        super().__init__(**kwargs)
        self.period = self.params.get("period", period)
        self.num_std = self.params.get("num_std", num_std)

    def validate_parameters(self) -> bool:
        return self.period > 0 and self.num_std > 0

    def get_required_columns(self) -> List[str]:
        return ["close"]

    def generate_signals(self, data: Union[pd.DataFrame, pd.Series]) -> Signal:
        if not self._is_initialized:
            self.initialize()

        if isinstance(data, pd.Series):
            close = data
        else:
            close = data["close"]

        sma = close.rolling(self.period).mean()
        std = close.rolling(self.period).std()

        upper_band = sma + (std * self.num_std)
        lower_band = sma - (std * self.num_std)

        current = close.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]

        if pd.isna(current_upper):
            return Signal(SignalType.HOLD, 50.0, {"reason": "insufficient_data"})

        if current < current_lower:
            distance = (current_lower - current) / current
            confidence = min(60 + distance * 300, 95)
            return Signal(
                SignalType.BUY,
                confidence,
                {
                    "position": "below_lower_band",
                    "bb_position": (current - current_lower)
                    / (current_upper - current_lower),
                },
            )

        elif current > current_upper:
            distance = (current - current_upper) / current
            confidence = min(60 + distance * 300, 95)
            return Signal(
                SignalType.SELL,
                confidence,
                {
                    "position": "above_upper_band",
                    "bb_position": (current - current_lower)
                    / (current_upper - current_lower),
                },
            )

        bb_position = (current - current_lower) / (current_upper - current_lower)
        return Signal(
            SignalType.HOLD,
            50.0,
            {"position": "within_bands", "bb_position": bb_position},
        )


class StrategyRegistry:
    """
    Registry for managing strategies.

    Allows dynamic strategy registration and discovery.
    """

    _strategies: Dict[str, Type[BaseStrategy]] = {}
    _instances: Dict[str, BaseStrategy] = {}

    @classmethod
    def register(cls, name: str, strategy_class: Type[BaseStrategy]) -> None:
        """Register a strategy class."""
        cls._strategies[name] = strategy_class
        logger.info(f"Registered strategy: {name}")

    @classmethod
    def create(cls, name: str, **params) -> BaseStrategy:
        """Create a strategy instance."""
        if name not in cls._strategies:
            raise ValueError(
                f"Unknown strategy: {name}. Available: {cls.list_strategies()}"
            )

        instance = cls._strategies[name](**params)
        cls._instances[name] = instance
        return instance

    @classmethod
    def get_strategy(cls, name: str) -> Optional[BaseStrategy]:
        """Get strategy instance by name."""
        return cls._instances.get(name)

    @classmethod
    def list_strategies(cls) -> List[str]:
        """List all registered strategies."""
        return list(cls._strategies.keys())


# Register built-in strategies
StrategyRegistry.register("ma_crossover", MACrossoverStrategy)
StrategyRegistry.register("rsi", RSIMeanReversionStrategy)
StrategyRegistry.register("breakout", BreakoutStrategy)
StrategyRegistry.register("momentum", MomentumStrategy)
StrategyRegistry.register("bollinger", BollingerBandStrategy)


def create_strategy(name: str, **params) -> BaseStrategy:
    """Factory function to create strategies."""
    return StrategyRegistry.create(name, **params)


def list_available_strategies() -> List[str]:
    """List all available strategies."""
    return StrategyRegistry.list_strategies()


class StrategyEnsemble:
    """
    Combine multiple strategies.

    Methods:
    - voting: Majority vote
    - weighted: Weighted average
    """

    def __init__(self, strategies: List[BaseStrategy], method: str = "voting"):
        self.strategies = strategies
        self.method = method

    def generate_signals(self, data: Union[pd.DataFrame, pd.Series]) -> Signal:
        """Generate ensemble signals from multiple strategies."""
        signals = []

        for strategy in self.strategies:
            try:
                signal = strategy.generate_signals(data)
                signals.append(signal)
            except Exception as e:
                logger.warning(f"Strategy {strategy.name} failed: {e}")

        if not signals:
            return Signal(SignalType.HOLD, 0.0)

        if self.method == "voting":
            return self._voting(signals)
        elif self.method == "weighted":
            return self._weighted(signals)

        return signals[0]

    def _voting(self, signals: List[Signal]) -> Signal:
        """Majority voting with 5-class signals."""
        votes = {
            SignalType.STRONG_BUY: 0,
            SignalType.BUY: 0,
            SignalType.HOLD: 0,
            SignalType.SELL: 0,
            SignalType.STRONG_SELL: 0,
        }
        total_conf = {
            SignalType.STRONG_BUY: 0.0,
            SignalType.BUY: 0.0,
            SignalType.HOLD: 0.0,
            SignalType.SELL: 0.0,
            SignalType.STRONG_SELL: 0.0,
        }

        for s in signals:
            votes[s.signal] += 1
            total_conf[s.signal] += s.confidence

        decision = max(votes, key=votes.get)
        confidence = (
            total_conf[decision] / votes[decision] if votes[decision] > 0 else 50
        )

        return Signal(decision, confidence)

    def _weighted(
        self, signals: List[Signal], weights: Optional[List[float]] = None
    ) -> Signal:
        """Weighted average of 5-class signals."""
        if weights is None:
            weights = [1.0 / len(signals)] * len(signals)

        total_score = 0.0
        total_confidence = 0.0

        signal_map = {
            SignalType.STRONG_BUY: 2,
            SignalType.BUY: 1,
            SignalType.HOLD: 0,
            SignalType.SELL: -1,
            SignalType.STRONG_SELL: -2,
        }

        for s, w in zip(signals, weights):
            score = signal_map.get(s.signal, 0)
            total_score += score * w * s.confidence
            total_confidence += w * s.confidence

        # Thresholds: >= 85 strong_buy, >= 60 buy, >= 40 hold, >= 25 sell, < 25 strong_sell
        # Map to -100 to 100 scale:
        # - score >= 85 -> strong_buy
        # - score >= 60 -> buy
        # - score >= 40 -> hold
        # - score >= 25 -> sell
        # - score < 25 -> strong_sell
        # total_score ranges from -200 to +200, so map to -100 to 100
        normalized_score = (total_score / 200 + 1) * 50  # Now 0-100

        if normalized_score >= 85:
            signal = SignalType.STRONG_BUY
        elif normalized_score >= 60:
            signal = SignalType.BUY
        elif normalized_score >= 40:
            signal = SignalType.HOLD
        elif normalized_score >= 25:
            signal = SignalType.SELL
        else:
            signal = SignalType.STRONG_SELL

        return Signal(signal, min(abs(total_confidence), 100))


def add_strategy_cli_args(parser: argparse.ArgumentParser) -> None:
    """Add strategy-related CLI arguments."""
    parser.add_argument(
        "--strategy",
        type=str,
        default="ma_crossover",
        choices=list_available_strategies(),
        help="Trading strategy to use",
    )
    parser.add_argument(
        "--strategy-params",
        type=str,
        default="",
        help="Strategy parameters as comma-separated key=value pairs (e.g., short_window=20,long_window=50)",
    )


def parse_strategy_params(params_str: str) -> Dict[str, Any]:
    """Parse strategy parameters from CLI string."""
    if not params_str:
        return {}

    params = {}
    for pair in params_str.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            try:
                params[key.strip()] = (
                    float(value.strip()) if "." in value else int(value.strip())
                )
            except ValueError:
                params[key.strip()] = value.strip()
    return params


__all__ = [
    "SignalType",
    "Signal",
    "StrategyConfig",
    "BaseStrategy",
    "MACrossoverStrategy",
    "RSIMeanReversionStrategy",
    "BreakoutStrategy",
    "MomentumStrategy",
    "BollingerBandStrategy",
    "StrategyRegistry",
    "StrategyEnsemble",
    "create_strategy",
    "list_available_strategies",
    "add_strategy_cli_args",
    "parse_strategy_params",
]
