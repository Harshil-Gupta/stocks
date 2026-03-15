"""
Portfolio Optimization Module.

Comprehensive portfolio optimization with:
- Mean-Variance Optimization (Markowitz)
- Risk Parity Portfolio
- Volatility Targeting
- Black-Litterman Model
- Minimum Variance Portfolio
- Maximum Sharpe Portfolio

Usage:
    from portfolio.optimization import (
        MeanVarianceOptimizer,
        RiskParityOptimizer,
        VolatilityTargetOptimizer,
        PortfolioOptimizer
    )

    # Optimize weights
    optimizer = MeanVarianceOptimizer()
    weights = optimizer.optimize(expected_returns, cov_matrix)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

try:
    from scipy.optimize import minimize

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    logger.warning("scipy not available, using simplified optimization")


class OptimizationMethod(Enum):
    """Portfolio optimization methods."""

    MEAN_VARIANCE = "mean_variance"
    MIN_VARIANCE = "min_variance"
    MAX_SHARPE = "max_sharpe"
    RISK_PARITY = "risk_parity"
    VOLATILITY_TARGET = "volatility_target"
    EQUAL_WEIGHT = "equal_weight"
    BLACK_LITTERMAN = "black_litterman"


@dataclass
class OptimizationConfig:
    """Configuration for portfolio optimization."""

    method: OptimizationMethod = OptimizationMethod.MAX_SHARPE
    risk_aversion: float = 1.0
    target_volatility: float = 0.15
    min_weight: float = 0.0
    max_weight: float = 0.3
    max_leverage: float = 1.0
    allow_short: bool = False
    regularization: float = 1e-6


@dataclass
class PortfolioWeights:
    """Portfolio weights result."""

    weights: pd.Series
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    method: str


class BaseOptimizer:
    """Base class for portfolio optimizers."""

    def __init__(self, config: Optional[OptimizationConfig] = None):
        self.config = config or OptimizationConfig()

    def optimize(
        self,
        expected_returns: Union[pd.Series, np.ndarray],
        covariance: Union[pd.DataFrame, np.ndarray],
    ) -> PortfolioWeights:
        raise NotImplementedError

    def _prepare_inputs(
        self,
        expected_returns: Union[pd.Series, np.ndarray],
        covariance: Union[pd.DataFrame, np.ndarray],
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Prepare inputs for optimization."""
        if isinstance(expected_returns, pd.Series):
            assets = expected_returns.index.tolist()
            exp_ret = expected_returns.values
        else:
            n = len(expected_returns)
            assets = [f"asset_{i}" for i in range(n)]
            exp_ret = expected_returns

        if isinstance(covariance, pd.DataFrame):
            cov = covariance.values
        else:
            cov = covariance

        return exp_ret, cov, assets

    def _apply_constraints(
        self,
        weights: np.ndarray,
    ) -> np.ndarray:
        """Apply weight constraints."""
        if not self.config.allow_short:
            weights = np.maximum(weights, 0)

        weights = np.clip(weights, self.config.min_weight, self.config.max_weight)

        total = weights.sum()
        if total > 0:
            weights = weights / total * min(total, self.config.max_leverage)

        return weights

    def _calculate_metrics(
        self,
        weights: np.ndarray,
        expected_returns: np.ndarray,
        covariance: np.ndarray,
    ) -> Tuple[float, float, float]:
        """Calculate portfolio metrics."""
        port_return = np.dot(weights, expected_returns)
        port_vol = np.sqrt(np.dot(weights, np.dot(covariance, weights)))

        sharpe = (port_return - 0.06) / port_vol if port_vol > 0 else 0

        return port_return, port_vol, sharpe

    def _get_bounds(self, n: int) -> List[Tuple[float, float]]:
        """Get bounds for optimization."""
        if self.config.allow_short:
            return [(-self.config.max_weight, self.config.max_weight) for _ in range(n)]
        return [(self.config.min_weight, self.config.max_weight) for _ in range(n)]


def _optimize_scipy(
    objective: Any,
    n: int,
    bounds: List[Tuple[float, float]],
    constraints: List[Dict],
    initial: np.ndarray,
) -> np.ndarray:
    """Optimize using scipy if available."""
    if HAS_SCIPY:
        result = minimize(
            objective,
            initial,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000},
        )
        return result.x
    else:
        return _optimize_grid_search(objective, n, bounds)


def _optimize_grid_search(
    objective: Any,
    n: int,
    bounds: List[Tuple[float, float]],
    n_points: int = 20,
) -> np.ndarray:
    """Fallback grid search optimization when scipy not available."""
    best_weights = np.ones(n) / n
    best_score = float("inf")

    for _ in range(100):
        weights = np.random.random(n)
        weights = weights / weights.sum()
        weights = np.clip(weights, 0, 0.4)

        score = objective(weights)
        if score < best_score:
            best_score = score
            best_weights = weights

    return best_weights


class MeanVarianceOptimizer(BaseOptimizer):
    """
    Mean-Variance Optimization (Markowitz).

    Maximizes expected return for a given level of risk,
    or minimizes risk for a given level of return.
    """

    def __init__(self, config: Optional[OptimizationConfig] = None):
        super().__init__(config)

    def optimize(
        self,
        expected_returns: Union[pd.Series, np.ndarray],
        covariance: Union[pd.DataFrame, np.ndarray],
    ) -> PortfolioWeights:
        """
        Optimize portfolio using mean-variance framework.

        Args:
            expected_returns: Expected returns per asset
            covariance: Covariance matrix

        Returns:
            PortfolioWeights with optimal weights
        """
        exp_ret, cov, assets = self._prepare_inputs(expected_returns, covariance)
        n = len(exp_ret)

        if n == 0:
            return self._empty_result(assets)

        def objective(w):
            ret = np.dot(w, exp_ret)
            vol = np.sqrt(np.dot(w, np.dot(cov, w)))
            return -(ret - self.config.risk_aversion * vol**2)

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]

        bounds = self._get_bounds(n)

        initial = np.ones(n) / n

        weights = _optimize_scipy(
            objective,
            n,
            bounds,
            constraints,
            initial,
        )

        weights = self._apply_constraints(weights)

        ret, vol, sharpe = self._calculate_metrics(weights, exp_ret, cov)

        return PortfolioWeights(
            weights=pd.Series(weights, index=assets),
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            method="mean_variance",
        )

    def _get_bounds(self, n: int) -> List[Tuple[float, float]]:
        """Get bounds for optimization."""
        if self.config.allow_short:
            return [(-self.config.max_weight, self.config.max_weight) for _ in range(n)]
        return [(self.config.min_weight, self.config.max_weight) for _ in range(n)]

    def _empty_result(self, assets: List[str]) -> PortfolioWeights:
        """Return empty result."""
        weights = pd.Series(1.0 / len(assets), index=assets) if assets else pd.Series()
        return PortfolioWeights(
            weights=weights,
            expected_return=0,
            expected_volatility=0,
            sharpe_ratio=0,
            method="mean_variance",
        )


class MaxSharpeOptimizer(BaseOptimizer):
    """
    Maximum Sharpe Ratio Portfolio.

    Finds the portfolio that maximizes the Sharpe ratio.
    """

    def __init__(self, config: Optional[OptimizationConfig] = None):
        super().__init__(config)
        self.config.risk_aversion = 0

    def optimize(
        self,
        expected_returns: Union[pd.Series, np.ndarray],
        covariance: Union[pd.DataFrame, np.ndarray],
        risk_free_rate: float = 0.06,
    ) -> PortfolioWeights:
        """Optimize for maximum Sharpe ratio."""
        exp_ret, cov, assets = self._prepare_inputs(expected_returns, covariance)
        n = len(exp_ret)

        if n == 0:
            return self._empty_result(assets)

        def objective(w):
            ret = np.dot(w, exp_ret)
            vol = np.sqrt(np.dot(w, np.dot(cov, w)))
            if vol == 0:
                return 0
            return -(ret - risk_free_rate) / vol

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]

        bounds = self._get_bounds(n)

        initial = np.ones(n) / n

        weights = _optimize_scipy(
            objective,
            n,
            bounds,
            constraints,
            initial,
        )

        weights = self._apply_constraints(weights)

        ret, vol, sharpe = self._calculate_metrics(weights, exp_ret, cov)

        return PortfolioWeights(
            weights=pd.Series(weights, index=assets),
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            method="max_sharpe",
        )

    def _get_bounds(self, n: int) -> List[Tuple[float, float]]:
        if self.config.allow_short:
            return [(-self.config.max_weight, self.config.max_weight) for _ in range(n)]
        return [(self.config.min_weight, self.config.max_weight) for _ in range(n)]

    def _empty_result(self, assets: List[str]) -> PortfolioWeights:
        weights = pd.Series(1.0 / len(assets), index=assets) if assets else pd.Series()
        return PortfolioWeights(
            weights=weights,
            expected_return=0,
            expected_volatility=0,
            sharpe_ratio=0,
            method="max_sharpe",
        )


class MinVarianceOptimizer(BaseOptimizer):
    """
    Minimum Variance Portfolio.

    Finds the portfolio with minimum volatility.
    """

    def optimize(
        self,
        expected_returns: Union[pd.Series, np.ndarray],
        covariance: Union[pd.DataFrame, np.ndarray],
    ) -> PortfolioWeights:
        """Optimize for minimum variance."""
        exp_ret, cov, assets = self._prepare_inputs(expected_returns, covariance)
        n = len(exp_ret)

        if n == 0:
            return self._empty_result(assets)

        def objective(w):
            return np.dot(w, np.dot(cov, w))

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]

        bounds = self._get_bounds(n)

        initial = np.ones(n) / n

        weights = _optimize_scipy(
            objective,
            n,
            bounds,
            constraints,
            initial,
        )

        weights = self._apply_constraints(weights)

        ret, vol, sharpe = self._calculate_metrics(weights, exp_ret, cov)

        return PortfolioWeights(
            weights=pd.Series(weights, index=assets),
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            method="min_variance",
        )

    def _empty_result(self, assets: List[str]) -> PortfolioWeights:
        weights = pd.Series(1.0 / len(assets), index=assets) if assets else pd.Series()
        return PortfolioWeights(
            weights=weights,
            expected_return=0,
            expected_volatility=0,
            sharpe_ratio=0,
            method="min_variance",
        )


class RiskParityOptimizer(BaseOptimizer):
    """
    Risk Parity Portfolio.

    Each asset contributes equally to portfolio risk.
    """

    def optimize(
        self,
        expected_returns: Union[pd.Series, np.ndarray],
        covariance: Union[pd.DataFrame, np.ndarray],
    ) -> PortfolioWeights:
        """Optimize for risk parity."""
        exp_ret, cov, assets = self._prepare_inputs(expected_returns, covariance)
        n = len(exp_ret)

        if n == 0:
            return self._empty_result(assets)

        def risk_contribution(w):
            portfolio_vol = np.sqrt(np.dot(w, np.dot(cov, w)))
            if portfolio_vol == 0:
                return np.zeros(n)

            marginal_contrib = np.dot(cov, w)
            risk_contrib = w * marginal_contrib / portfolio_vol
            return risk_contrib

        def objective(w):
            rc = risk_contribution(w)
            target_rc = np.sum(rc) / n
            return np.sum((rc - target_rc) ** 2)

        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "ineq", "fun": lambda w: w},
        ]

        bounds = [(0.001, self.config.max_weight) for _ in range(n)]

        initial = np.ones(n) / n

        weights = _optimize_scipy(
            objective,
            n,
            bounds,
            constraints,
            initial,
        )

        weights = self._apply_constraints(weights)

        ret, vol, sharpe = self._calculate_metrics(weights, exp_ret, cov)

        return PortfolioWeights(
            weights=pd.Series(weights, index=assets),
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            method="risk_parity",
        )

    def _empty_result(self, assets: List[str]) -> PortfolioWeights:
        weights = pd.Series(1.0 / len(assets), index=assets) if assets else pd.Series()
        return PortfolioWeights(
            weights=weights,
            expected_return=0,
            expected_volatility=0,
            sharpe_ratio=0,
            method="risk_parity",
        )


class VolatilityTargetOptimizer(BaseOptimizer):
    """
    Volatility Targeting Portfolio.

    Scales positions to achieve target volatility.
    """

    def __init__(self, config: Optional[OptimizationConfig] = None):
        super().__init__(config)
        self.config.target_volatility = config.target_volatility if config else 0.15

    def optimize(
        self,
        expected_returns: Union[pd.Series, np.ndarray],
        covariance: Union[pd.DataFrame, np.ndarray],
    ) -> PortfolioWeights:
        """Optimize for target volatility."""
        exp_ret, cov, assets = self._prepare_inputs(expected_returns, covariance)
        n = len(exp_ret)

        if n == 0:
            return self._empty_result(assets)

        mvo = MaxSharpeOptimizer(self.config)
        mvo_weights = mvo.optimize(exp_ret, cov)

        base_weights = mvo_weights.weights.values

        base_vol = np.sqrt(np.dot(base_weights, np.dot(cov, base_weights)))

        if base_vol > 0:
            scaling_factor = self.config.target_volatility / base_vol
            scaling_factor = min(scaling_factor, 2.0)
        else:
            scaling_factor = 1.0

        weights = base_weights * scaling_factor

        weights = np.clip(weights, self.config.min_weight, self.config.max_weight)

        if weights.sum() > 0:
            weights = weights / weights.sum()

        ret, vol, sharpe = self._calculate_metrics(weights, exp_ret, cov)

        return PortfolioWeights(
            weights=pd.Series(weights, index=assets),
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            method="volatility_target",
        )

    def _empty_result(self, assets: List[str]) -> PortfolioWeights:
        weights = pd.Series(1.0 / len(assets), index=assets) if assets else pd.Series()
        return PortfolioWeights(
            weights=weights,
            expected_return=0,
            expected_volatility=0,
            sharpe_ratio=0,
            method="volatility_target",
        )


class BlackLittermanOptimizer(BaseOptimizer):
    """
    Black-Litterman Model.

    Combines market equilibrium returns with investor views.
    """

    def __init__(
        self,
        config: Optional[OptimizationConfig] = None,
        market_caps: Optional[pd.Series] = None,
        tau: float = 0.05,
    ):
        super().__init__(config)
        self.market_caps = market_caps
        self.tau = tau

    def optimize(
        self,
        expected_returns: Union[pd.Series, np.ndarray],
        covariance: Union[pd.DataFrame, np.ndarray],
        views: Optional[Dict[str, float]] = None,
        view_confidences: Optional[Dict[str, float]] = None,
    ) -> PortfolioWeights:
        """
        Optimize using Black-Litterman model.

        Args:
            expected_returns: Prior expected returns
            covariance: Covariance matrix
            views: Dict of asset -> expected return view
            view_confidences: Dict of asset -> confidence (0-1)
        """
        exp_ret, cov, assets = self._prepare_inputs(expected_returns, covariance)
        n = len(exp_ret)

        if n == 0:
            return self._empty_result(assets)

        if self.market_caps is not None:
            mc = self.market_caps.values
        else:
            mc = np.ones(n)

        market_weights = mc / mc.sum()

        risk_free = 0.06
        implied_returns = risk_free + np.dot(cov, market_weights) * np.log(
            mc / mc.mean()
        )

        if views:
            view_returns = np.array([views.get(a, 0) for a in assets])
            confidences = np.array([view_confidences.get(a, 0.5) for a in assets])

            omega = np.diag(np.dot(cov, confidences) * self.tau)

            blended = np.linalg.inv(np.linalg.inv(cov) + np.linalg.inv(omega)) @ (
                np.linalg.inv(cov) @ implied_returns
                + np.linalg.inv(omega) @ view_returns
            )
            exp_ret = blended

        mvo = MaxSharpeOptimizer(self.config)
        return mvo.optimize(exp_ret, cov)

    def _empty_result(self, assets: List[str]) -> PortfolioWeights:
        weights = pd.Series(1.0 / len(assets), index=assets) if assets else pd.Series()
        return PortfolioWeights(
            weights=weights,
            expected_return=0,
            expected_volatility=0,
            sharpe_ratio=0,
            method="black_litterman",
        )


class PortfolioOptimizer:
    """
    Unified portfolio optimizer with multiple methods.
    """

    OPTIMIZERS = {
        OptimizationMethod.MEAN_VARIANCE: MeanVarianceOptimizer,
        OptimizationMethod.MAX_SHARPE: MaxSharpeOptimizer,
        OptimizationMethod.MIN_VARIANCE: MinVarianceOptimizer,
        OptimizationMethod.RISK_PARITY: RiskParityOptimizer,
        OptimizationMethod.VOLATILITY_TARGET: VolatilityTargetOptimizer,
        OptimizationMethod.BLACK_LITTERMAN: BlackLittermanOptimizer,
    }

    def __init__(
        self,
        method: OptimizationMethod = OptimizationMethod.MAX_SHARPE,
        config: Optional[OptimizationConfig] = None,
    ):
        self.method = method
        self.config = config or OptimizationConfig(method=method)

        if method == OptimizationMethod.EQUAL_WEIGHT:
            self.optimizer = None
        else:
            optimizer_class = self.OPTIMIZERS.get(method, MaxSharpeOptimizer)
            self.optimizer = optimizer_class(self.config)

    def optimize(
        self,
        expected_returns: Union[pd.Series, np.ndarray],
        covariance: Union[pd.DataFrame, np.ndarray],
        **kwargs,
    ) -> PortfolioWeights:
        """Optimize portfolio weights."""
        if self.method == OptimizationMethod.EQUAL_WEIGHT:
            return self._equal_weight(expected_returns, covariance)

        if self.optimizer is None:
            self.optimizer = MaxSharpeOptimizer(self.config)

        return self.optimizer.optimize(expected_returns, covariance, **kwargs)

    def _equal_weight(
        self,
        expected_returns: Union[pd.Series, np.ndarray],
        covariance: Union[pd.DataFrame, np.ndarray],
    ) -> PortfolioWeights:
        """Generate equal weight portfolio."""
        if isinstance(expected_returns, pd.Series):
            assets = expected_returns.index.tolist()
            n = len(expected_returns)
        else:
            n = len(expected_returns)
            assets = [f"asset_{i}" for i in range(n)]

        weights = pd.Series(1.0 / n, index=assets)

        if isinstance(covariance, pd.DataFrame):
            cov = covariance.values
        else:
            cov = covariance

        if isinstance(expected_returns, pd.Series):
            exp_ret = expected_returns.values
        else:
            exp_ret = expected_returns

        ret = np.dot(weights.values, exp_ret)
        vol = np.sqrt(np.dot(weights.values, np.dot(cov, weights.values)))
        sharpe = (ret - 0.06) / vol if vol > 0 else 0

        return PortfolioWeights(
            weights=weights,
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            method="equal_weight",
        )


def compute_covariance_matrix(
    returns: pd.DataFrame,
    method: str = "sample",
    lookback: int = 252,
    shrink: float = 0.2,
) -> pd.DataFrame:
    """
    Compute covariance matrix with multiple methods.

    Args:
        returns: DataFrame of asset returns
        method: "sample", "shrink", "ewma", or "factor"
        lookback: Window for EWMA
        shrink: Shrinkage parameter

    Returns:
        Covariance matrix
    """
    if method == "sample":
        return returns.cov()

    elif method == "shrink":
        sample_cov = returns.cov()
        mu = returns.mean()
        n, p = returns.shape

        prior = (
            np.outer(mu, mu) * (1 - shrink)
            + np.eye(p) * shrink * sample_cov.values.mean()
        )
        prior = pd.DataFrame(prior, index=sample_cov.index, columns=sample_cov.columns)

        return prior

    elif method == "ewma":
        cov = returns.ewm(halflife=lookback).cov()
        return cov.loc[returns.index[-1]]

    return returns.cov()


def calculate_expected_returns(
    prices: pd.DataFrame,
    method: str = "mean",
    lookback: int = 252,
) -> pd.Series:
    """
    Calculate expected returns.

    Args:
        prices: DataFrame of prices
        method: "mean", "ema", "capm", or "risk_adj"
        lookback: Window for calculation

    Returns:
        Expected returns per asset
    """
    returns = prices.pct_change().dropna()

    if method == "mean":
        return returns.mean() * 252

    elif method == "ema":
        return returns.ewm(halflife=lookback).mean().iloc[-1] * 252

    elif method == "risk_adj":
        vol = returns.std() * np.sqrt(252)
        mean_ret = returns.mean() * 252
        return mean_ret / vol * 0.15

    return returns.mean() * 252


__all__ = [
    "OptimizationMethod",
    "OptimizationConfig",
    "PortfolioWeights",
    "BaseOptimizer",
    "MeanVarianceOptimizer",
    "MaxSharpeOptimizer",
    "MinVarianceOptimizer",
    "RiskParityOptimizer",
    "VolatilityTargetOptimizer",
    "BlackLittermanOptimizer",
    "PortfolioOptimizer",
    "compute_covariance_matrix",
    "calculate_expected_returns",
]
