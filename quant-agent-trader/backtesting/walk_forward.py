"""
Walk-Forward Backtesting Module.

Professional workflow that prevents overfitting by training on past data
and testing on future data.

Timeline:
    train 2016-2020, test 2021
    train 2017-2021, test 2022
    train 2018-2022, test 2023
    train 2019-2023, test 2024

Usage:
    from backtesting.walk_forward import WalkForwardBacktest
    
    wft = WalkForwardBacktest(
        train_years=3,
        test_year=1,
        step_year=1
    )
    results = wft.run(data, agents)
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass, field

from backtesting.engine import BacktestEngine, BacktestConfigExtended

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward backtesting."""
    train_years: int = 3
    test_year: int = 1
    step_year: int = 1
    min_train_samples: int = 500
    min_test_samples: int = 100


@dataclass
class FoldResult:
    """Result from a single walk-forward fold."""
    fold: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    train_samples: int
    test_samples: int
    metrics: Dict[str, float]
    trades_count: int


class WalkForwardBacktest:
    """
    Walk-forward backtesting to prevent overfitting.
    
    Each fold:
        1. Train on historical data (e.g., 2018-2021)
        2. Test on future data (e.g., 2022)
        3. Slide window forward
    """
    
    def __init__(
        self,
        config: Optional[WalkForwardConfig] = None,
        backtest_config: Optional[BacktestConfigExtended] = None
    ):
        self.config = config or WalkForwardConfig()
        self.backtest_config = backtest_config or BacktestConfigExtended()
        self.results: List[FoldResult] = []
    
    def run(
        self,
        data: Dict[str, pd.DataFrame],
        agents: List[Any],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Run walk-forward backtest.
        
        Args:
            data: Dict of symbol -> price DataFrame
            agents: List of trading agents
            start_date: Optional override for start
            end_date: Optional override for end
            
        Returns:
            Walk-forward results
        """
        if start_date is None:
            start_date = min(df.index.min() for df in data.values() if not df.empty)
        if end_date is None:
            end_date = max(df.index.max() for df in data.values() if not df.empty)
        
        logger.info(
            f"Walk-forward backtest: {start_date.date()} to {end_date.date()}"
        )
        logger.info(
            f"Config: train={self.config.train_years}y, "
            f"test={self.config.test_year}y, step={self.config.step_year}y"
        )
        
        self.results = []
        
        train_end = start_date + timedelta(days=365 * self.config.train_years)
        test_end = train_end + timedelta(days=365 * self.config.test_year)
        
        fold = 0
        
        while test_end <= end_date:
            train_start = start_date
            test_start = train_end
            
            logger.info(
                f"Fold {fold}: train {train_start.date()} to {train_end.date()}, "
                f"test {test_start.date()} to {test_end.date()}"
            )
            
            train_data = {
                symbol: df[(df.index >= train_start) & (df.index < train_end)]
                for symbol, df in data.items()
            }
            
            test_data = {
                symbol: df[(df.index >= test_start) & (df.index < test_end)]
                for symbol, df in data.items()
            }
            
            train_samples = sum(len(df) for df in train_data.values())
            test_samples = sum(len(df) for df in test_data.values())
            
            if train_samples < self.config.min_train_samples:
                logger.warning(f"Skipping fold {fold}: insufficient training data")
                train_end = train_end + timedelta(days=365 * self.config.step_year)
                test_end = test_end + timedelta(days=365 * self.config.step_year)
                continue
            
            if test_samples < self.config.min_test_samples:
                logger.warning(f"Skipping fold {fold}: insufficient test data")
                train_end = train_end + timedelta(days=365 * self.config.step_year)
                test_end = test_end + timedelta(days=365 * self.config.step_year)
                continue
            
            fold_result = self._run_fold(
                fold=fold,
                train_data=train_data,
                test_data=test_data,
                agents=agents,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end
            )
            
            self.results.append(fold_result)
            
            train_end = train_end + timedelta(days=365 * self.config.step_year)
            test_end = test_end + timedelta(days=365 * self.config.step_year)
            fold += 1
        
        return self._summarize_results()
    
    def _run_fold(
        self,
        fold: int,
        train_data: Dict[str, pd.DataFrame],
        test_data: Dict[str, pd.DataFrame],
        agents: List[Any],
        train_start: datetime,
        train_end: datetime,
        test_start: datetime,
        test_end: datetime
    ) -> FoldResult:
        """Run a single fold."""
        logger.info(f"Running fold {fold}...")
        
        engine = BacktestEngine(config=self.backtest_config)
        
        result = engine.run_backtest(
            data=test_data,
            agents=agents,
            start_date=test_start,
            end_date=test_end,
            regime="sideways"
        )
        
        metrics = {
            "cumulative_return": result.metrics.cumulative_return,
            "annualized_return": result.metrics.annualized_return,
            "sharpe_ratio": result.metrics.sharpe_ratio,
            "sortino_ratio": result.metrics.sortino_ratio,
            "max_drawdown": result.metrics.max_drawdown,
            "win_rate": result.metrics.win_rate,
            "profit_factor": result.metrics.profit_factor,
            "total_trades": result.metrics.total_trades
        }
        
        train_samples = sum(len(df) for df in train_data.values())
        test_samples = sum(len(df) for df in test_data.values())
        
        logger.info(
            f"Fold {fold} complete: Return={metrics['cumulative_return']:.2%}, "
            f"Sharpe={metrics['sharpe_ratio']:.2f}, Trades={metrics['total_trades']}"
        )
        
        return FoldResult(
            fold=fold,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            train_samples=train_samples,
            test_samples=test_samples,
            metrics=metrics,
            trades_count=result.metrics.total_trades
        )
    
    def _summarize_results(self) -> Dict[str, Any]:
        """Summarize all fold results."""
        if not self.results:
            return {"folds": [], "summary": {}}
        
        metrics_keys = [
            "cumulative_return", "annualized_return", "sharpe_ratio",
            "sortino_ratio", "max_drawdown", "win_rate", "profit_factor"
        ]
        
        summary = {}
        
        for key in metrics_keys:
            values = [r.metrics.get(key, 0) for r in self.results]
            if values:
                summary[f"avg_{key}"] = np.mean(values)
                summary[f"std_{key}"] = np.std(values)
                summary[f"min_{key}"] = np.min(values)
                summary[f"max_{key}"] = np.max(values)
        
        summary["total_folds"] = len(self.results)
        summary["total_trades"] = sum(r.trades_count for r in self.results)
        
        return {
            "folds": [
                {
                    "fold": r.fold,
                    "train_period": f"{r.train_start.date()} to {r.train_end.date()}",
                    "test_period": f"{r.test_start.date()} to {r.test_end.date()}",
                    "train_samples": r.train_samples,
                    "test_samples": r.test_samples,
                    "metrics": r.metrics,
                    "trades_count": r.trades_count
                }
                for r in self.results
            ],
            "summary": summary
        }
    
    def get_results_df(self) -> pd.DataFrame:
        """Get results as DataFrame."""
        if not self.results:
            return pd.DataFrame()
        
        data = []
        for r in self.results:
            row = {
                "fold": r.fold,
                "train_start": r.train_start,
                "train_end": r.train_end,
                "test_start": r.test_start,
                "test_end": r.test_end,
                "train_samples": r.train_samples,
                "test_samples": r.test_samples,
                "trades": r.trades_count,
                **r.metrics
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def print_summary(self) -> None:
        """Print summary to console."""
        if not self.results:
            print("No results to display")
            return
        
        print("\n" + "="*70)
        print("WALK-FORWARD BACKTEST RESULTS")
        print("="*70)
        
        print(f"\nConfiguration:")
        print(f"  Train years:  {self.config.train_years}")
        print(f"  Test year:    {self.config.test_year}")
        print(f"  Step year:    {self.config.step_year}")
        print(f"  Total folds:  {len(self.results)}")
        
        print(f"\n{'Fold':<5} {'Train Period':<25} {'Test Period':<25} {'Return':<10} {'Sharpe':<8} {'Trades':<8}")
        print("-"*70)
        
        for r in self.results:
            print(
                f"{r.fold:<5} "
                f"{r.train_start.date()} to {r.train_end.date():<12} "
                f"{r.test_start.date()} to {r.test_end.date():<12} "
                f"{r.metrics['cumulative_return']:<10.2%} "
                f"{r.metrics['sharpe_ratio']:<8.2f} "
                f"{r.trades_count:<8}"
            )
        
        summary = self._summarize_results()["summary"]
        
        print("\n" + "-"*70)
        print("SUMMARY STATISTICS")
        print("-"*70)
        
        print(f"\n{'Metric':<25} {'Mean':<12} {'Std':<12} {'Min':<12} {'Max':<12}")
        print("-"*70)
        
        metrics = [
            ("Cumulative Return", "avg_cumulative_return", "min_cumulative_return", "max_cumulative_return"),
            ("Annualized Return", "avg_annualized_return", "min_annualized_return", "max_annualized_return"),
            ("Sharpe Ratio", "avg_sharpe_ratio", "min_sharpe_ratio", "max_sharpe_ratio"),
            ("Sortino Ratio", "avg_sortino_ratio", "min_sortino_ratio", "max_sortino_ratio"),
            ("Max Drawdown", "avg_max_drawdown", "min_max_drawdown", "max_max_drawdown"),
            ("Win Rate", "avg_win_rate", "min_win_rate", "max_win_rate"),
        ]
        
        for name, avg_key, min_key, max_key in metrics:
            avg = summary.get(avg_key, 0)
            std = summary.get(avg_key.replace("avg", "std"), 0)
            mn = summary.get(min_key, 0)
            mx = summary.get(max_key, 0)
            
            print(f"{name:<25} {avg:<12.4f} {std:<12.4f} {mn:<12.4f} {mx:<12.4f}")
        
        print("\n" + "="*70)


class RegimeAwareWalkForward:
    """
    Walk-forward backtesting with regime awareness.
    
    Trains separate models for each regime.
    """
    
    def __init__(
        self,
        config: Optional[WalkForwardConfig] = None,
        regimes: List[str] = None
    ):
        self.config = config or WalkForwardConfig()
        self.regimes = regimes or ["bull", "bear", "sideways", "high_volatility"]
        self.results_by_regime: Dict[str, List[FoldResult]] = {
            r: [] for r in self.regimes
        }
    
    def run(
        self,
        data: Dict[str, pd.DataFrame],
        agents: List[Any],
        regime_data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Run regime-aware walk-forward."""
        
        wft = WalkForwardBacktest(config=self.config)
        results = wft.run(data, agents)
        
        return {
            "overall": results,
            "by_regime": {
                regime: {"folds": [], "summary": {}}
                for regime in self.regimes
            }
        }
