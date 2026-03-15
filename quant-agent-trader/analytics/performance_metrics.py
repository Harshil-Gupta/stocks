"""
Advanced Performance Metrics Module.

Provides comprehensive portfolio and strategy performance analysis:
- Alpha, Beta, Information Ratio
- Sortino Ratio, Calmar Ratio
- Rolling Sharpe, Rolling Drawdown
- Custom Risk Metrics
- Benchmark Comparison
- Performance Attribution

Usage:
    from analytics.performance_metrics import PerformanceAnalyzer

    analyzer = PerformanceAnalyzer()
    metrics = analyzer.compute_metrics(returns, benchmark_returns)

    # Rolling metrics
    rolling_sharpe = analyzer.rolling_sharpe(returns, window=60)
    rolling_dd = analyzer.rolling_drawdown(equity_curve)
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _skewness(data: np.ndarray) -> float:
    """Calculate skewness without scipy."""
    n = len(data)
    if n < 3:
        return 0.0
    mean = np.mean(data)
    std = np.std(data)
    if std == 0:
        return 0.0
    return np.mean(((data - mean) / std) ** 3)


def _kurtosis(data: np.ndarray) -> float:
    """Calculate kurtosis without scipy."""
    n = len(data)
    if n < 4:
        return 0.0
    mean = np.mean(data)
    std = np.std(data)
    if std == 0:
        return 0.0
    return np.mean(((data - mean) / std) ** 4) - 3


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""

    total_return: float
    cagr: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    alpha: float
    beta: float
    information_ratio: float
    treynor_ratio: float
    gain_to_pain_ratio: float
    skewness: float
    kurtosis: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    expectancy: float
    recovery_time: Optional[int] = None


@dataclass
class RollingMetrics:
    """Rolling window metrics."""

    rolling_sharpe: pd.Series = field(default_factory=pd.Series)
    rolling_sortino: pd.Series = field(default_factory=pd.Series)
    rolling_drawdown: pd.Series = field(default_factory=pd.Series)
    rolling_volatility: pd.Series = field(default_factory=pd.Series)
    rolling_return: pd.Series = field(default_factory=pd.Series)


class PerformanceAnalyzer:
    """
    Advanced performance metrics analyzer.

    Computes comprehensive risk and return metrics for:
    - Portfolio returns
    - Strategy returns
    - Benchmark comparison
    """

    def __init__(
        self,
        risk_free_rate: float = 0.06,
        trading_days: int = 252,
    ):
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
        self.daily_rf = risk_free_rate / trading_days

    def compute_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        equity_curve: Optional[pd.Series] = None,
    ) -> PerformanceMetrics:
        """
        Compute all performance metrics.

        Args:
            returns: Strategy returns series
            benchmark_returns: Benchmark returns for alpha/beta
            equity_curve: Optional equity curve

        Returns:
            PerformanceMetrics object
        """
        if equity_curve is None:
            equity_curve = (1 + returns).cumprod()

        total_return = self.total_return(equity_curve)
        cagr = self.cagr(equity_curve)
        volatility = self.volatility(returns)
        sharpe = self.sharpe_ratio(returns)
        sortino = self.sortino_ratio(returns)
        calmar = self.calmar_ratio(returns)
        max_dd, max_dd_dur = self.max_drawdown(equity_curve)

        alpha = 0.0
        beta = 0.0
        ir = 0.0
        treynor = 0.0

        if benchmark_returns is not None and len(benchmark_returns) > 0:
            alpha = self.alpha(returns, benchmark_returns)
            beta = self.beta(returns, benchmark_returns)
            ir = self.information_ratio(returns, benchmark_returns)
            if beta != 0:
                treynor = (returns.mean() - self.daily_rf) / beta * self.trading_days

        g2p = self.gain_to_pain_ratio(returns)
        skew = _skewness(returns.dropna().values)
        kurt = _kurtosis(returns.dropna().values)

        win_rate, pf, avg_win, avg_loss, expect = self.trade_statistics(returns)

        return PerformanceMetrics(
            total_return=total_return,
            cagr=cagr,
            volatility=volatility,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_dur,
            alpha=alpha,
            beta=beta,
            information_ratio=ir,
            treynor_ratio=treynor,
            gain_to_pain_ratio=g2p,
            skewness=skew,
            kurtosis=kurt,
            win_rate=win_rate,
            profit_factor=pf,
            avg_win=avg_win,
            avg_loss=avg_loss,
            expectancy=expect,
        )

    def total_return(self, equity_curve: pd.Series) -> float:
        """Calculate total return."""
        if len(equity_curve) == 0:
            return 0.0
        return (
            (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1)
            if equity_curve.iloc[0] != 0
            else 0.0
        )

    def cagr(self, equity_curve: pd.Series) -> float:
        """Calculate Compound Annual Growth Rate."""
        if len(equity_curve) < 2:
            return 0.0

        start_value = equity_curve.iloc[0]
        end_value = equity_curve.iloc[-1]

        if start_value <= 0:
            return 0.0

        n_years = len(equity_curve) / self.trading_days
        if n_years <= 0:
            return 0.0

        return (end_value / start_value) ** (1 / n_years) - 1

    def volatility(self, returns: pd.Series) -> float:
        """Calculate annualized volatility."""
        if len(returns) == 0:
            return 0.0
        return returns.std() * np.sqrt(self.trading_days)

    def sharpe_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: Optional[float] = None,
    ) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) == 0:
            return 0.0

        rf = risk_free_rate if risk_free_rate is not None else self.risk_free_rate
        daily_rf = rf / self.trading_days

        excess_returns = returns - daily_rf

        if excess_returns.std() == 0:
            return 0.0

        return (excess_returns.mean() / excess_returns.std()) * np.sqrt(
            self.trading_days
        )

    def sortino_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: Optional[float] = None,
    ) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        if len(returns) == 0:
            return 0.0

        rf = risk_free_rate if risk_free_rate is not None else self.risk_free_rate
        daily_rf = rf / self.trading_days

        excess_returns = returns - daily_rf

        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0

        downside_std = downside_returns.std() * np.sqrt(self.trading_days)

        return (excess_returns.mean() * self.trading_days) / downside_std

    def calmar_ratio(self, equity_curve: pd.Series) -> float:
        """Calculate Calmar ratio (CAGR / Max Drawdown)."""
        cagr = self.cagr(equity_curve)
        max_dd, _ = self.max_drawdown(equity_curve)

        if max_dd == 0:
            return 0.0

        return cagr / abs(max_dd)

    def max_drawdown(self, equity_curve: pd.Series) -> Tuple[float, int]:
        """
        Calculate maximum drawdown and duration.

        Returns:
            Tuple of (max_drawdown, duration_in_days)
        """
        if len(equity_curve) == 0:
            return 0.0, 0

        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max

        max_dd = drawdown.min()

        if pd.isna(max_dd) or max_dd == 0:
            return 0.0, 0

        dd_start = drawdown.idxmin()

        try:
            dd_start_idx = equity_curve.index.get_loc(dd_start)
        except KeyError:
            dd_start_idx = 0

        recovery_idx = len(equity_curve)
        for i in range(dd_start_idx + 1, len(equity_curve)):
            if equity_curve.iloc[i] >= running_max.iloc[dd_start_idx]:
                recovery_idx = i
                break

        duration = recovery_idx - dd_start_idx

        return abs(max_dd), duration

    def alpha(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> float:
        """Calculate Jensen's Alpha."""
        if len(returns) == 0 or len(benchmark_returns) == 0:
            return 0.0

        aligned_returns = returns.align(benchmark_returns, join="inner")
        strategy_ret = aligned_returns[0]
        bench_ret = aligned_returns[1]

        if len(strategy_ret) == 0:
            return 0.0

        strategy_excess = strategy_ret.mean() - self.daily_rf
        bench_excess = bench_ret.mean() - self.daily_rf

        covariance = np.cov(strategy_ret, bench_ret)[0][1]
        bench_variance = np.var(bench_ret)

        if bench_variance == 0:
            return 0.0

        beta = covariance / bench_variance

        alpha = strategy_excess - beta * bench_excess

        return alpha * self.trading_days

    def beta(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> float:
        """Calculate portfolio Beta."""
        if len(returns) == 0 or len(benchmark_returns) == 0:
            return 0.0

        aligned_returns = returns.align(benchmark_returns, join="inner")
        strategy_ret = aligned_returns[0]
        bench_ret = aligned_returns[1]

        if len(strategy_ret) == 0:
            return 0.0

        covariance = np.cov(strategy_ret, bench_ret)[0][1]
        bench_variance = np.var(bench_ret)

        if bench_variance == 0:
            return 0.0

        return covariance / bench_variance

    def information_ratio(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> float:
        """Calculate Information Ratio."""
        if len(returns) == 0 or len(benchmark_returns) == 0:
            return 0.0

        aligned_returns = returns.align(benchmark_returns, join="inner")
        strategy_ret = aligned_returns[0]
        bench_ret = aligned_returns[1]

        if len(strategy_ret) == 0:
            return 0.0

        active_returns = strategy_ret - bench_ret

        if active_returns.std() == 0:
            return 0.0

        return (active_returns.mean() / active_returns.std()) * np.sqrt(
            self.trading_days
        )

    def gain_to_pain_ratio(self, returns: pd.Series) -> float:
        """Calculate Gain to Pain Ratio."""
        if len(returns) == 0:
            return 0.0

        total_return = returns.sum()
        pain = returns[returns < 0].sum()

        if pain == 0:
            return 0.0

        return total_return / abs(pain)

    def trade_statistics(
        self, returns: pd.Series
    ) -> Tuple[float, float, float, float, float]:
        """Calculate trade-level statistics."""
        if len(returns) == 0:
            return 0.0, 0.0, 0.0, 0.0, 0.0

        wins = returns[returns > 0]
        losses = returns[returns < 0]

        win_rate = len(wins) / len(returns) if len(returns) > 0 else 0.0

        gross_profit = wins.sum() if len(wins) > 0 else 0.0
        gross_loss = abs(losses.sum()) if len(losses) > 0 else 0.0

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        avg_win = wins.mean() if len(wins) > 0 else 0.0
        avg_loss = losses.mean() if len(losses) > 0 else 0.0

        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        return win_rate, profit_factor, avg_win, avg_loss, expectancy

    def rolling_sharpe(
        self,
        returns: pd.Series,
        window: int = 60,
    ) -> pd.Series:
        """Calculate rolling Sharpe ratio."""
        if len(returns) < window:
            return pd.Series(dtype=float)

        rolling_mean = returns.rolling(window).mean()
        rolling_std = returns.rolling(window).std()

        sharpe = (
            (rolling_mean - self.daily_rf) / rolling_std * np.sqrt(self.trading_days)
        )

        return sharpe

    def rolling_sortino(
        self,
        returns: pd.Series,
        window: int = 60,
    ) -> pd.Series:
        """Calculate rolling Sortino ratio."""
        if len(returns) < window:
            return pd.Series(dtype=float)

        rolling_mean = returns.rolling(window).mean()

        downside = returns.copy()
        downside[downside > 0] = 0
        downside_std = downside.rolling(window).std()

        sortino = (
            (rolling_mean - self.daily_rf) / downside_std * np.sqrt(self.trading_days)
        )

        return sortino

    def rolling_drawdown(self, equity_curve: pd.Series) -> pd.Series:
        """Calculate rolling drawdown."""
        if len(equity_curve) == 0:
            return pd.Series(dtype=float)

        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max

        return drawdown

    def rolling_volatility(
        self,
        returns: pd.Series,
        window: int = 60,
    ) -> pd.Series:
        """Calculate rolling volatility."""
        return returns.rolling(window).std() * np.sqrt(self.trading_days)

    def rolling_max_drawdown(
        self,
        equity_curve: pd.Series,
        window: int = 252,
    ) -> pd.Series:
        """Calculate rolling maximum drawdown."""
        if len(equity_curve) < window:
            return pd.Series(dtype=float)

        rolling_max = equity_curve.rolling(window, min_periods=1).max()
        drawdown = (equity_curve - rolling_max) / rolling_max

        return drawdown.rolling(window).min()

    def compute_all_rolling(
        self,
        returns: pd.Series,
        equity_curve: Optional[pd.Series] = None,
        window: int = 60,
    ) -> RollingMetrics:
        """Compute all rolling metrics."""
        if equity_curve is None:
            equity_curve = (1 + returns).cumprod()

        return RollingMetrics(
            rolling_sharpe=self.rolling_sharpe(returns, window),
            rolling_sortino=self.rolling_sortino(returns, window),
            rolling_drawdown=self.rolling_drawdown(equity_curve),
            rolling_volatility=self.rolling_volatility(returns, window),
            rolling_return=returns.rolling(window).mean() * self.trading_days,
        )

    def performance_summary(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive performance summary."""
        equity_curve = (1 + returns).cumprod()

        metrics = self.compute_metrics(returns, benchmark_returns, equity_curve)

        rolling = self.compute_all_rolling(returns, equity_curve)

        return {
            "metrics": metrics.__dict__,
            "rolling": {
                "sharpe": rolling.rolling_sharpe.to_dict(),
                "drawdown": rolling.rolling_drawdown.to_dict(),
                "volatility": rolling.rolling_volatility.to_dict(),
            },
            "summary": {
                "total_days": len(returns),
                "trading_days": len(returns[returns != 0]),
                "positive_days": len(returns[returns > 0]),
                "negative_days": len(returns[returns < 0]),
            },
        }

    def compare_strategies(
        self,
        strategy_returns: Dict[str, pd.Series],
        benchmark_returns: Optional[pd.Series] = None,
    ) -> pd.DataFrame:
        """
        Compare multiple strategies.

        Args:
            strategy_returns: Dict of strategy_name -> returns series
            benchmark_returns: Optional benchmark

        Returns:
            DataFrame with comparison metrics
        """
        results = []

        for name, returns in strategy_returns.items():
            metrics = self.compute_metrics(returns, benchmark_returns)

            results.append(
                {
                    "Strategy": name,
                    "Total Return": f"{metrics.total_return * 100:.2f}%",
                    "CAGR": f"{metrics.cagr * 100:.2f}%",
                    "Volatility": f"{metrics.volatility * 100:.2f}%",
                    "Sharpe": f"{metrics.sharpe_ratio:.2f}",
                    "Sortino": f"{metrics.sortino_ratio:.2f}",
                    "Max DD": f"{metrics.max_drawdown * 100:.2f}%",
                    "Calmar": f"{metrics.calmar_ratio:.2f}",
                    "Win Rate": f"{metrics.win_rate * 100:.1f}%",
                    "Alpha": f"{metrics.alpha * 100:.2f}%" if metrics.alpha else "N/A",
                    "Beta": f"{metrics.beta:.2f}" if metrics.beta else "N/A",
                }
            )

        return pd.DataFrame(results).set_index("Strategy")


def calculate_performance_metrics(
    returns: pd.Series,
    benchmark: Optional[pd.Series] = None,
    risk_free_rate: float = 0.06,
) -> Dict[str, float]:
    """
    Convenience function to calculate performance metrics.

    Args:
        returns: Strategy returns
        benchmark: Benchmark returns
        risk_free_rate: Annual risk-free rate

    Returns:
        Dictionary of metrics
    """
    analyzer = PerformanceAnalyzer(risk_free_rate=risk_free_rate)
    metrics = analyzer.compute_metrics(returns, benchmark)
    return {
        "total_return": metrics.total_return,
        "cagr": metrics.cagr,
        "volatility": metrics.volatility,
        "sharpe_ratio": metrics.sharpe_ratio,
        "sortino_ratio": metrics.sortino_ratio,
        "calmar_ratio": metrics.calmar_ratio,
        "max_drawdown": metrics.max_drawdown,
        "alpha": metrics.alpha,
        "beta": metrics.beta,
        "information_ratio": metrics.information_ratio,
        "win_rate": metrics.win_rate,
        "profit_factor": metrics.profit_factor,
    }


__all__ = [
    "PerformanceMetrics",
    "RollingMetrics",
    "PerformanceAnalyzer",
    "calculate_performance_metrics",
]
