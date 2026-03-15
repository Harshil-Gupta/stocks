"""
Strategy Plugin System - Extensible strategy framework.

This module provides:
- Base strategy interface
- Strategy registration and discovery
- Parameter validation
- Strategy combination (ensemble)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

VALID_SIGNALS = {"strong_buy", "buy", "hold", "sell", "strong_sell"}

SIGNAL_SCORE_MAP = {
    "strong_buy": 2,
    "buy": 1,
    "hold": 0,
    "sell": -1,
    "strong_sell": -2,
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

    def __init__(self, config: StrategyConfig):
        self.config = config
        self.name = config.name
        self.params = config.parameters
        self.risk_limits = config.risk_limits
        self._is_initialized = False

    @abstractmethod
    def generate_signals(self, data: Any, **kwargs) -> Dict[str, Any]:
        """
        Generate trading signals from market data.

        Args:
            data: Market data (DataFrame or dict)

        Returns:
            Dictionary with keys: signal (strong_buy/buy/hold/sell/strong_sell), confidence, metadata
        """
        pass

    @abstractmethod
    def validate_parameters(self) -> bool:
        """Validate strategy parameters."""
        pass

    def initialize(self) -> None:
        """Initialize strategy (e.g., load models, compute parameters)."""
        if not self.validate_parameters():
            raise ValueError(f"Invalid parameters for strategy {self.name}")
        self._is_initialized = True
        logger.info(f"Initialized strategy: {self.name}")

    def get_required_features(self) -> List[str]:
        """List features required by this strategy."""
        return []

    def get_risk_metrics(self) -> Dict[str, float]:
        """Get current risk metrics."""
        return {}


class MomentumStrategy(BaseStrategy):
    """Momentum-based trading strategy."""

    def validate_parameters(self) -> bool:
        required = ["lookback_period", "threshold"]
        return all(p in self.params for p in required)

    def generate_signals(self, data: Any, **kwargs) -> Dict[str, Any]:
        if not self._is_initialized:
            self.initialize()

        lookback = self.params["lookback_period"]
        threshold = self.params["threshold"]

        if hasattr(data, "iloc"):
            returns = data["close"].pct_change(lookback).iloc[-1]
        else:
            returns = 0

        if returns > threshold * 2:
            return {"signal": "strong_buy", "confidence": min(abs(returns) * 10, 100)}
        elif returns > threshold:
            return {"signal": "buy", "confidence": min(abs(returns) * 8, 90)}
        elif returns < -threshold * 2:
            return {"signal": "strong_sell", "confidence": min(abs(returns) * 10, 100)}
        elif returns < -threshold:
            return {"signal": "sell", "confidence": min(abs(returns) * 8, 90)}

        return {"signal": "hold", "confidence": 50}


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion trading strategy."""

    def validate_parameters(self) -> bool:
        required = ["bb_period", "bb_std"]
        return all(p in self.params for p in required)

    def generate_signals(self, data: Any, **kwargs) -> Dict[str, Any]:
        if not self._is_initialized:
            self.initialize()

        period = self.params["bb_period"]
        bb_std = self.params["bb_std"]

        if hasattr(data, "iloc"):
            close = data["close"]
            sma = close.rolling(period).mean().iloc[-1]
            std = close.rolling(period).std().iloc[-1]
            current = close.iloc[-1]

            distance = abs(current - sma) / std
            confidence = min(60 + distance * 20, 95)

            if current < sma - (bb_std * std):
                signal = "strong_buy" if distance > 2 * bb_std else "buy"
                return {"signal": signal, "confidence": confidence}
            elif current > sma + (bb_std * std):
                signal = "strong_sell" if distance > 2 * bb_std else "sell"
                return {"signal": signal, "confidence": confidence}

        return {"signal": "hold", "confidence": 50}


class BreakoutStrategy(BaseStrategy):
    """Breakout trading strategy."""

    def validate_parameters(self) -> bool:
        required = ["lookback_period"]
        return all(p in self.params for p in required)

    def generate_signals(self, data: Any, **kwargs) -> Dict[str, Any]:
        if not self._is_initialized:
            self.initialize()

        period = self.params["lookback_period"]

        if hasattr(data, "iloc"):
            high = data["high"].rolling(period).max().iloc[-1]
            low = data["low"].rolling(period).min().iloc[-1]
            current = data["close"].iloc[-1]

            distance_up = (current - high) / high if current > high else 0
            distance_down = (low - current) / current if current < low else 0

            if distance_up > 0.03:
                return {"signal": "strong_buy", "confidence": 90}
            elif current > high:
                return {"signal": "buy", "confidence": 80}
            elif distance_down > 0.03:
                return {"signal": "strong_sell", "confidence": 90}
            elif current < low:
                return {"signal": "sell", "confidence": 80}

        return {"signal": "hold", "confidence": 50}


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
    def create(cls, name: str, config: Optional[StrategyConfig] = None) -> BaseStrategy:
        """Create a strategy instance."""
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}")

        if config is None:
            config = StrategyConfig(name=name)

        instance = cls._strategies[name](config)
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
StrategyRegistry.register("momentum", MomentumStrategy)
StrategyRegistry.register("mean_reversion", MeanReversionStrategy)
StrategyRegistry.register("breakout", BreakoutStrategy)


class StrategyEnsemble:
    """
    Combine multiple strategies.

    Methods:
    - voting: Majority vote
    - weighted: Weighted average
    - stacking: Meta-learner
    """

    def __init__(self, strategies: List[BaseStrategy], method: str = "voting"):
        self.strategies = strategies
        self.method = method

    def generate_signals(
        self, data: Any, weights: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Generate ensemble signals from multiple strategies."""
        signals = []

        for strategy in self.strategies:
            try:
                signal = strategy.generate_signals(data)
                signals.append(signal)
            except Exception as e:
                logger.warning(f"Strategy {strategy.name} failed: {e}")

        if not signals:
            return {"signal": "hold", "confidence": 0}

        if self.method == "voting":
            return self._voting(signals)
        elif self.method == "weighted":
            return self._weighted(signals, weights)

        return signals[0]

    def _voting(self, signals: List[Dict]) -> Dict[str, Any]:
        """Majority voting with 5-class signals."""
        votes = {"strong_buy": 0, "buy": 0, "hold": 0, "sell": 0, "strong_sell": 0}
        total_confidence = {
            "strong_buy": 0.0,
            "buy": 0.0,
            "hold": 0.0,
            "sell": 0.0,
            "strong_sell": 0.0,
        }

        for s in signals:
            signal = s.get("signal", "hold")
            conf = s.get("confidence", 50)
            if signal in votes:
                votes[signal] += 1
                total_confidence[signal] += conf

        decision = max(votes, key=votes.get)
        confidence = (
            total_confidence[decision] / votes[decision] if votes[decision] > 0 else 50
        )

        return {"signal": decision, "confidence": confidence}

    def _weighted(
        self, signals: List[Dict], weights: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Weighted average of 5-class signals."""
        if weights is None:
            weights = [1.0 / len(signals)] * len(signals)

        total_score = 0.0
        total_confidence = 0.0

        for s, w in zip(signals, weights):
            signal = s.get("signal", "hold")
            score = SIGNAL_SCORE_MAP.get(signal, 0)
            total_score += score * w * s.get("confidence", 50)
            total_confidence += w * s.get("confidence", 50)

        if total_score > 30:
            signal = "strong_buy"
        elif total_score > 10:
            signal = "buy"
        elif total_score < -30:
            signal = "strong_sell"
        elif total_score < -10:
            signal = "sell"
        else:
            signal = "hold"

        return {"signal": signal, "confidence": min(abs(total_confidence), 100)}


__all__ = [
    "StrategyConfig",
    "BaseStrategy",
    "MomentumStrategy",
    "MeanReversionStrategy",
    "BreakoutStrategy",
    "StrategyRegistry",
    "StrategyEnsemble",
]
