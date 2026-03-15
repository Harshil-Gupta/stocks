"""
Portfolio Optimizer - Position sizing and risk management.

Methods:
- Kelly Criterion
- Risk Parity
- Volatility Scaling
- Mean-Variance Optimization

Usage:
    from portfolio.optimizer import PortfolioOptimizer

    optimizer = PortfolioOptimizer(method="kelly")
    positions = optimizer.optimize(
        signals=signals,
        portfolio_value=100000,
        volatility=0.15
    )
"""

from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
import logging

from signals.signal_schema import AggregatedSignal, AgentSignal

logger = logging.getLogger(__name__)


class PositionSizer:
    """Base class for position sizing strategies."""

    def compute_size(
        self, signal: AggregatedSignal, portfolio_value: float, **kwargs
    ) -> float:
        """Compute position size (0-1)."""
        raise NotImplementedError


class FixedPositionSizer(PositionSizer):
    """Fixed position size regardless of signal."""

    def __init__(self, size: float = 0.1):
        self.size = size

    def compute_size(
        self, signal: AggregatedSignal, portfolio_value: float, **kwargs
    ) -> float:
        return self.size


class KellyPositionSizer(PositionSizer):
    """
    Kelly Criterion position sizing.

    position_size = (bp * p - b) / b
    where:
        bp = win rate
        p = average win / average loss
        b = odds
    """

    def __init__(self, fraction: float = 1.0, max_size: float = 0.25):
        self.fraction = fraction
        self.max_size = max_size

    def compute_size(
        self,
        signal: AggregatedSignal,
        portfolio_value: float,
        win_rate: float = 0.55,
        avg_win: float = 0.02,
        avg_loss: float = 0.01,
        **kwargs,
    ) -> float:
        """Compute Kelly position size."""
        if win_rate <= 0 or avg_win <= 0 or avg_loss <= 0:
            return 0.1

        b = avg_win / avg_loss

        kelly = (win_rate * b - (1 - win_rate)) / b

        kelly = kelly * self.fraction

        kelly = max(0, min(kelly, self.max_size))

        return kelly


class VolatilityPositionSizer(PositionSizer):
    """
    Volatility-based position sizing.

    position_size = target_volatility / actual_volatility
    """

    def __init__(
        self,
        target_volatility: float = 0.15,
        max_size: float = 0.25,
        min_size: float = 0.02,
    ):
        self.target_volatility = target_volatility
        self.max_size = max_size
        self.min_size = min_size

    def compute_size(
        self,
        signal: AggregatedSignal,
        portfolio_value: float,
        volatility: float = 0.15,
        **kwargs,
    ) -> float:
        """Compute volatility-adjusted position size."""
        if volatility <= 0:
            return self.min_size

        size = self.target_volatility / volatility

        size = size * (signal.confidence / 100)

        size = max(self.min_size, min(size, self.max_size))

        return size


class RiskParitySizer(PositionSizer):
    """
    Risk parity position sizing.

    Equal risk contribution from each position.
    """

    def __init__(self, max_positions: int = 10):
        self.max_positions = max_positions

    def compute_size(
        self,
        signal: AggregatedSignal,
        portfolio_value: float,
        position_volatility: float = 0.15,
        **kwargs,
    ) -> float:
        """Compute risk parity size."""
        if not signal.is_buy:
            return 0

        target_risk = 1.0 / self.max_positions

        size = target_risk / position_volatility if position_volatility > 0 else 0

        return min(size, 0.2)


class ConfidencePositionSizer(PositionSizer):
    """
    Confidence-based position sizing.

    Size = confidence * base_size
    """

    def __init__(self, base_size: float = 0.1, max_size: float = 0.25):
        self.base_size = base_size
        self.max_size = max_size

    def compute_size(
        self, signal: AggregatedSignal, portfolio_value: float, **kwargs
    ) -> float:
        """Compute confidence-based size."""
        if signal.decision == "hold":
            return 0

        confidence = signal.confidence / 100

        base_size = self.base_size

        if signal.decision == "strong_buy":
            base_size = self.base_size * 1.5
        elif signal.decision == "strong_sell":
            base_size = -self.base_size * 1.5

        size = base_size * confidence

        if signal.is_sell:
            size = -abs(size)

        return max(-self.max_size, min(size, self.max_size))


class PortfolioOptimizer:
    """
    Portfolio optimizer with multiple methods.

    Usage:
        optimizer = PortfolioOptimizer(method="kelly")
        positions = optimizer.optimize(signals, portfolio_value)
    """

    METHODS = {
        "fixed": FixedPositionSizer,
        "kelly": KellyPositionSizer,
        "volatility": VolatilityPositionSizer,
        "risk_parity": RiskParitySizer,
        "confidence": ConfidencePositionSizer,
    }

    def __init__(self, method: str = "confidence", **kwargs):
        self.method = method
        self.sizer = self.METHODS.get(method, ConfidencePositionSizer)(**kwargs)

        logger.info(f"Portfolio optimizer initialized with method: {method}")

    def optimize(
        self, signals: List[AggregatedSignal], portfolio_value: float, **kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """
        Optimize portfolio positions.

        Args:
            signals: List of aggregated signals
            portfolio_value: Total portfolio value
            **kwargs: Additional parameters for sizer

        Returns:
            Dict of symbol -> position details
        """
        positions = {}

        for signal in signals:
            if signal.decision == "hold":
                continue

            size = self.sizer.compute_size(
                signal=signal, portfolio_value=portfolio_value, **kwargs
            )

            if size == 0:
                continue

            position_value = portfolio_value * abs(size)

            positions[signal.stock_symbol] = {
                "symbol": signal.stock_symbol,
                "decision": signal.decision,
                "position_size": size,
                "position_value": position_value,
                "confidence": signal.confidence,
                "final_score": signal.final_score,
                "regime": signal.regime,
            }

        return positions

    def optimize_with_risk(
        self,
        signals: List[AggregatedSignal],
        portfolio_value: float,
        max_position_size: float = 0.25,
        max_portfolio_risk: float = 0.20,
        **kwargs,
    ) -> Dict[str, Dict[str, Any]]:
        """Optimize with risk constraints."""
        positions = self.optimize(signals, portfolio_value, **kwargs)

        total_long = sum(
            p["position_size"] for p in positions.values() if p["decision"] == "buy"
        )

        if total_long > max_portfolio_risk:
            scale = max_portfolio_risk / total_long
            for pos in positions.values():
                if pos["decision"] == "buy":
                    pos["position_size"] *= scale
                    pos["position_value"] = portfolio_value * pos["position_size"]

        for symbol, pos in positions.items():
            if abs(pos["position_size"]) > max_position_size:
                pos["position_size"] = np.sign(pos["position_size"]) * max_position_size
                pos["position_value"] = portfolio_value * abs(pos["position_size"])

        return positions


class MeanVarianceOptimizer:
    """
    Mean-variance optimization (Markowitz).

    Maximizes Sharpe ratio given expected returns and covariance.
    """

    def __init__(
        self,
        risk_aversion: float = 1.0,
        min_weight: float = 0.0,
        max_weight: float = 0.3,
    ):
        self.risk_aversion = risk_aversion
        self.min_weight = min_weight
        self.max_weight = max_weight

    def optimize(
        self,
        expected_returns: pd.Series,
        covariance: pd.DataFrame,
        current_weights: Optional[pd.Series] = None,
    ) -> pd.Series:
        """
        Optimize portfolio weights.

        Args:
            expected_returns: Expected returns per asset
            covariance: Covariance matrix
            current_weights: Current portfolio weights

        Returns:
            Optimal weights
        """
        n_assets = len(expected_returns)

        if current_weights is None:
            current_weights = pd.Series(1.0 / n_assets, index=expected_returns.index)

        weights = self._solve_quadratic(expected_returns, covariance, current_weights)

        return weights

    def _solve_quadratic(
        self,
        expected_returns: pd.Series,
        covariance: pd.DataFrame,
        initial_weights: pd.Series,
    ) -> pd.Series:
        """Solve quadratic optimization problem."""
        from scipy.optimize import minimize

        def objective(w):
            port_return = np.dot(w, expected_returns)
            port_vol = np.sqrt(np.dot(w, np.dot(covariance, w)))

            if port_vol == 0:
                return 0

            sharpe = port_return / port_vol

            return -(sharpe - self.risk_aversion * port_vol)

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]

        bounds = [
            (self.min_weight, self.max_weight) for _ in range(len(expected_returns))
        ]

        result = minimize(
            objective,
            initial_weights.values,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        return pd.Series(result.x, index=expected_returns.index)


class RegimeAwareOptimizer:
    """
    Optimizer that adjusts based on market regime.

    Different sizing in bull vs bear markets.
    """

    REGIME_CONFIGS = {
        "bull": {"method": "momentum", "base_size": 0.15, "max_size": 0.30},
        "bear": {"method": "volatility", "base_size": 0.05, "max_size": 0.10},
        "sideways": {"method": "mean_reversion", "base_size": 0.08, "max_size": 0.15},
        "high_volatility": {
            "method": "volatility",
            "base_size": 0.05,
            "max_size": 0.10,
        },
    }

    def __init__(self):
        self.optimizers: Dict[str, PortfolioOptimizer] = {}

        for regime, config in self.REGIME_CONFIGS.items():
            self.optimizers[regime] = PortfolioOptimizer(
                method=config["method"],
                base_size=config["base_size"],
                max_size=config["max_size"],
            )

    def optimize(
        self,
        signals: List[AggregatedSignal],
        portfolio_value: float,
        regime: str = "sideways",
    ) -> Dict[str, Dict[str, Any]]:
        """Optimize with regime awareness."""
        optimizer = self.optimizers.get(regime, self.optimizers["sideways"])

        return optimizer.optimize(signals, portfolio_value)


def calculate_portfolio_metrics(
    positions: Dict[str, Dict[str, Any]], returns: pd.DataFrame
) -> Dict[str, float]:
    """Calculate portfolio-level metrics."""
    if not positions or returns.empty:
        return {}

    symbols = list(positions.keys())
    weights = np.array([positions[s]["position_size"] for s in symbols])

    if returns.empty or not any(s in returns.columns for s in symbols):
        return {}

    relevant_returns = returns[symbols]

    portfolio_returns = (relevant_returns * weights).sum(axis=1)

    metrics = {
        "total_return": portfolio_returns.sum(),
        "volatility": portfolio_returns.std() * np.sqrt(252),
        "sharpe_ratio": (
            portfolio_returns.mean() / portfolio_returns.std() * np.sqrt(252)
            if portfolio_returns.std() > 0
            else 0
        ),
        "max_drawdown": calculate_max_drawdown(portfolio_returns),
        "win_rate": (portfolio_returns > 0).mean(),
    }

    return metrics


def calculate_max_drawdown(returns: pd.Series) -> float:
    """Calculate maximum drawdown."""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max

    return abs(drawdown.min())
