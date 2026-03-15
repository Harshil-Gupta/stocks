"""
Factor Models - Multi-factor investing framework.

Provides:
- Factor computation (Momentum, Value, Quality, Size, Volatility)
- Factor exposure analysis
- Risk attribution
- Factor-based screening
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class FactorExposure:
    """Factor exposure for a single asset."""

    symbol: str
    momentum: float
    value: float
    quality: float
    size: float
    volatility: float
    beta: float


class FactorModel:
    """
    Multi-factor model for stock selection.

    Factors:
    - Momentum: Past returns
    - Value: P/E, P/B ratios
    - Quality: ROE, ROA, Debt/Equity
    - Size: Market cap
    - Volatility: Historical volatility
    """

    def __init__(
        self, momentum_periods: List[int] = [20, 60, 120], lookback_days: int = 252
    ):
        self.momentum_periods = momentum_periods
        self.lookback_days = lookback_days

    def compute_factors(
        self,
        price_data: Dict[str, pd.DataFrame],
        fundamental_data: Optional[Dict[str, Dict]] = None,
    ) -> pd.DataFrame:
        """
        Compute factor exposures for all symbols.

        Args:
            price_data: Dict of symbol -> OHLCV DataFrames
            fundamental_data: Optional dict of symbol -> fundamentals

        Returns:
            DataFrame with factor exposures per symbol
        """
        factor_data = []

        for symbol, df in price_data.items():
            if len(df) < 60:
                continue

            factors = {"symbol": symbol}

            # Momentum factors
            for period in self.momentum_periods:
                ret = df["close"].pct_change(period).iloc[-1]
                factors[f"momentum_{period}d"] = ret

            # Volatility factor (lower is better)
            returns = df["close"].pct_change().iloc[-self.lookback_days :]
            factors["volatility"] = returns.std() * np.sqrt(252)

            # Size factor (log market cap if available)
            if fundamental_data and symbol in fundamental_data:
                fund = fundamental_data[symbol]
                factors["market_cap"] = fund.get("market_cap", 0)
                factors["pe_ratio"] = fund.get("pe_ratio", 0)
                factors["pb_ratio"] = fund.get("pb_ratio", 0)
                factors["roe"] = fund.get("roe", 0)
                factors["debt_equity"] = fund.get("debt_equity", 0)
            else:
                # Use price-based proxies
                factors["market_cap"] = df["close"].iloc[-1] * 1e9
                factors["pe_ratio"] = 20  # Default
                factors["pb_ratio"] = 3  # Default
                factors["roe"] = 15  # Default
                factors["debt_equity"] = 0.5  # Default

            factor_data.append(factors)

        return pd.DataFrame(factor_data)

    def compute_z_scores(self, factors: pd.DataFrame) -> pd.DataFrame:
        """Compute normalized factor z-scores."""
        z_scores = factors.copy()

        for col in factors.columns:
            if col == "symbol":
                continue

            mean = factors[col].mean()
            std = factors[col].std()

            if std > 0:
                z_scores[col] = (factors[col] - mean) / std
            else:
                z_scores[col] = 0

        return z_scores

    def compute_factor_returns(
        self, factors: pd.DataFrame, returns: pd.DataFrame, lookback: int = 60
    ) -> Dict[str, float]:
        """
        Compute historical factor returns via regression.

        Returns:
            Dict of factor name -> annualized return
        """
        factor_returns = {}

        for col in factors.columns:
            if col == "symbol":
                continue

            # Compute rolling correlation with returns
            factor_series = factors[col].shift(1)  # Lag to avoid lookahead
            ret_series = returns["total_return"]

            # Align series
            aligned = pd.concat([factor_series, ret_series], axis=1).dropna()

            if len(aligned) > 10:
                corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
                factor_returns[col] = corr
            else:
                factor_returns[col] = 0

        return factor_returns

    def rank_stocks(
        self, factors: pd.DataFrame, weights: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        Rank stocks by composite factor score.

        Args:
            factors: Factor DataFrame
            weights: Optional factor weights

        Returns:
            Ranked DataFrame
        """
        if weights is None:
            weights = {
                "momentum_60d": 0.25,
                "pe_ratio": 0.20,
                "roe": 0.25,
                "volatility": -0.15,
                "market_cap": 0.15,
            }

        # Compute z-scores
        z_scores = self.compute_z_scores(factors)

        # Compute composite score
        scores = pd.DataFrame()
        scores["symbol"] = factors["symbol"]
        scores["score"] = 0

        for factor, weight in weights.items():
            if factor in z_scores.columns:
                # Invert sign for negative factors
                sign = (
                    -1
                    if factor in ["volatility", "pe_ratio", "pb_ratio", "debt_equity"]
                    else 1
                )
                scores["score"] += z_scores[factor] * weight * sign

        # Rank
        scores = scores.sort_values("score", ascending=False)
        scores["rank"] = range(1, len(scores) + 1)

        return scores


class RiskAttribution:
    """
    Decompose portfolio risk into factor contributions.
    """

    def __init__(self, factor_model: FactorModel):
        self.factor_model = factor_model

    def attribute_risk(
        self,
        portfolio_weights: Dict[str, float],
        factor_exposures: pd.DataFrame,
        covariance_matrix: Optional[pd.DataFrame] = None,
    ) -> Dict[str, float]:
        """
        Attribute portfolio risk to factors.

        Args:
            portfolio_weights: Symbol -> weight mapping
            factor_exposures: Factor exposures per symbol
            covariance_matrix: Optional factor covariance

        Returns:
            Factor name -> risk contribution
        """
        risk_contrib = {}

        # Get factor loadings for portfolio
        symbols = list(portfolio_weights.keys())
        weights = np.array([portfolio_weights[s] for s in symbols])

        for col in factor_exposures.columns:
            if col == "symbol":
                continue

            # Factor exposure = weighted average of factor values
            factor_vals = factor_exposures.set_index("symbol")[col]

            # Align with portfolio weights
            valid_symbols = [s for s in symbols if s in factor_vals.index]
            if valid_symbols:
                aligned_weights = np.array(
                    [portfolio_weights[s] for s in valid_symbols]
                )
                aligned_factor = np.array([factor_vals[s] for s in valid_symbols])

                exposure = np.dot(aligned_weights, aligned_factor)
                risk_contrib[col] = abs(exposure)

        # Normalize
        total = sum(risk_contrib.values())
        if total > 0:
            risk_contrib = {k: v / total for k, v in risk_contrib.items()}

        return risk_contrib


class FactorScreener:
    """
    Screen stocks based on factor criteria.
    """

    def __init__(self, factor_model: FactorModel):
        self.factor_model = factor_model

    def screen(
        self, factors: pd.DataFrame, criteria: Dict[str, Tuple[str, float]]
    ) -> List[str]:
        """
        Screen stocks meeting factor criteria.

        Args:
            factors: Factor DataFrame
            criteria: Dict of factor -> (operator, threshold)
                    Operators: '>', '<', '>=', '<=', '=='

        Returns:
            List of symbols meeting criteria
        """
        z_scores = self.factor_model.compute_z_scores(factors)

        mask = pd.Series([True] * len(z_scores), index=z_scores.index)

        for factor, (op, threshold) in criteria.items():
            if factor not in z_scores.columns:
                continue

            col = z_scores[factor]

            if op == ">":
                mask &= col > threshold
            elif op == "<":
                mask &= col < threshold
            elif op == ">=":
                mask &= col >= threshold
            elif op == "<=":
                mask &= col <= threshold
            elif op == "==":
                mask &= col == threshold

        return z_scores.loc[mask, "symbol"].tolist()


__all__ = [
    "FactorExposure",
    "FactorModel",
    "RiskAttribution",
    "FactorScreener",
]
