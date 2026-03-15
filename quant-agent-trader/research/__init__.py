"""
Research Platform - Experiment tracking, strategy comparison, and hyperparameter tuning.

Features:
- Experiment tracking with versioning
- Strategy parameter grids
- Backtest comparison
- Results persistence (SQLite/JSON)
- Hyperparameter optimization

Usage:
    from research.experiment import Experiment, ExperimentTracker
    from research.tuning import HyperparameterOptimizer

    # Run experiment
    tracker = ExperimentTracker("research/results")
    exp = tracker.create_experiment("ma_crossover_test")
    exp.run(strategy_params={"short_window": 20, "long_window": 50})
"""

import json
import os
import sqlite3
import uuid
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
import pandas as pd
import numpy as np
from itertools import product
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    """Configuration for an experiment."""

    name: str
    strategy: str
    parameters: Dict[str, Any]
    start_date: str
    end_date: str
    symbols: List[str]
    initial_capital: float = 100000


@dataclass
class ExperimentResult:
    """Results from an experiment."""

    experiment_id: str
    timestamp: str
    status: str
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    duration_seconds: float
    error: Optional[str] = None


class ExperimentTracker:
    """
    Track experiments with versioning and persistence.
    """

    def __init__(self, results_dir: str = "research/results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.results_dir / "experiments.db"
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                strategy TEXT NOT NULL,
                parameters TEXT,
                start_date TEXT,
                end_date TEXT,
                status TEXT,
                metrics TEXT,
                duration_seconds REAL,
                error TEXT,
                created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiment_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT,
                run_number INTEGER,
                parameters TEXT,
                metrics TEXT,
                timestamp TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        """)

        conn.commit()
        conn.close()

    def create_experiment(self, name: str) -> "Experiment":
        """Create a new experiment."""
        return Experiment(name, self)

    def save_result(self, result: ExperimentResult):
        """Save experiment result."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO experiments 
            (id, name, strategy, parameters, status, metrics, duration_seconds, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                result.experiment_id,
                result.experiment_id.split("_")[0],
                result.experiment_id.split("_")[0],
                json.dumps(result.parameters),
                result.status,
                json.dumps(result.metrics),
                result.duration_seconds,
                result.error,
                result.timestamp,
            ),
        )

        conn.commit()
        conn.close()

        self._save_json_result(result)

    def _save_json_result(self, result: ExperimentResult):
        """Save detailed result as JSON."""
        result_file = self.results_dir / f"{result.experiment_id}.json"

        with open(result_file, "w") as f:
            json.dump(asdict(result), f, indent=2)

    def list_experiments(self) -> pd.DataFrame:
        """List all experiments."""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql("SELECT * FROM experiments ORDER BY created_at DESC", conn)
        conn.close()
        return df

    def get_experiment(self, experiment_id: str) -> Optional[ExperimentResult]:
        """Get specific experiment result."""
        result_file = self.results_dir / f"{experiment_id}.json"

        if result_file.exists():
            with open(result_file) as f:
                data = json.load(f)
                return ExperimentResult(**data)

        return None

    def compare_experiments(self, experiment_ids: List[str]) -> pd.DataFrame:
        """Compare multiple experiments."""
        results = []

        for exp_id in experiment_ids:
            result = self.get_experiment(exp_id)
            if result:
                row = {
                    "experiment_id": exp_id,
                    "status": result.status,
                    "duration": result.duration_seconds,
                }
                row.update(result.metrics)
                results.append(row)

        return pd.DataFrame(results)

    def get_best_experiment(
        self, metric: str = "sharpe_ratio", maximize: bool = True
    ) -> Optional[ExperimentResult]:
        """Get best experiment by metric."""
        df = self.list_experiments()

        if df.empty:
            return None

        df["metrics_dict"] = df["metrics"].apply(json.loads)
        df["metric_value"] = df["metrics_dict"].apply(lambda x: x.get(metric, 0))

        if maximize:
            best_idx = df["metric_value"].idxmax()
        else:
            best_idx = df["metric_value"].idxmin()

        return self.get_experiment(df.loc[best_idx, "id"])


class Experiment:
    """
    Single experiment runner.
    """

    def __init__(self, name: str, tracker: ExperimentTracker):
        self.name = name
        self.tracker = tracker
        self.experiment_id = (
            f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        )
        self.parameters: Dict[str, Any] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def run(
        self, strategy_func: Callable, parameters: Dict[str, Any], **kwargs
    ) -> ExperimentResult:
        """Run the experiment."""
        self.parameters = parameters
        self.start_time = datetime.now()

        try:
            result = strategy_func(parameters=parameters, **kwargs)

            if isinstance(result, dict):
                metrics = result
            elif hasattr(result, "metrics"):
                metrics = result.metrics
            else:
                metrics = {"result": str(result)}

            status = "success"
            error = None

        except Exception as e:
            metrics = {}
            status = "failed"
            error = str(e)
            logger.error(f"Experiment {self.experiment_id} failed: {e}")

        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        result_obj = ExperimentResult(
            experiment_id=self.experiment_id,
            timestamp=self.start_time.isoformat(),
            status=status,
            parameters=self.parameters,
            metrics=metrics,
            duration_seconds=duration,
            error=error,
        )

        self.tracker.save_result(result_obj)

        return result_obj


class StrategyComparator:
    """
    Compare multiple strategies side by side.
    """

    def __init__(self, results_dir: str = "research/results"):
        self.results_dir = Path(results_dir)
        self.tracker = ExperimentTracker(results_dir)

    def run_comparison(
        self,
        strategies: Dict[str, Callable],
        parameters: Dict[str, Any],
        symbols: List[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        Run multiple strategies and compare results.

        Args:
            strategies: Dict of strategy_name -> strategy_function
            parameters: Parameters to test
            symbols: Symbols to backtest
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with comparison results
        """
        results = []

        for strategy_name, strategy_func in strategies.items():
            logger.info(f"Running strategy: {strategy_name}")

            exp = self.tracker.create_experiment(strategy_name)

            try:
                result = exp.run(
                    strategy_func,
                    parameters,
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                )

                results.append(
                    {
                        "strategy": strategy_name,
                        "status": result.status,
                        **result.metrics,
                    }
                )

            except Exception as e:
                logger.error(f"Strategy {strategy_name} failed: {e}")
                results.append(
                    {
                        "strategy": strategy_name,
                        "status": "failed",
                        "error": str(e),
                    }
                )

        return pd.DataFrame(results)

    def compare_parameter_sets(
        self, strategy_func: Callable, parameter_grid: Dict[str, List[Any]], **kwargs
    ) -> pd.DataFrame:
        """
        Compare different parameter sets for a strategy.

        Args:
            strategy_func: Strategy function to run
            parameter_grid: Dict of parameter_name -> list of values
            **kwargs: Additional arguments for strategy_func

        Returns:
            DataFrame with all parameter combinations
        """
        param_names = list(parameter_grid.keys())
        param_values = list(parameter_grid.values())

        combinations = list(product(*param_values))

        results = []

        for combo in combinations:
            params = dict(zip(param_names, combo))
            logger.info(f"Testing parameters: {params}")

            exp = self.tracker.create_experiment(f"param_test_{uuid.uuid4().hex[:4]}")

            try:
                result = exp.run(strategy_func, params, **kwargs)

                row = {"parameters": params, "status": result.status}
                row.update(result.metrics)
                results.append(row)

            except Exception as e:
                results.append(
                    {
                        "parameters": params,
                        "status": "failed",
                        "error": str(e),
                    }
                )

        return pd.DataFrame(results)

    def load_previous_results(self) -> pd.DataFrame:
        """Load all previous experiment results."""
        return self.tracker.list_experiments()


class HyperparameterOptimizer:
    """
    Hyperparameter optimization using grid search or random search.
    """

    def __init__(
        self,
        strategy_func: Callable,
        parameter_grid: Dict[str, List[Any]],
        optimization_metric: str = "sharpe_ratio",
        maximize: bool = True,
        method: str = "grid",
        n_iterations: int = 50,
    ):
        self.strategy_func = strategy_func
        self.parameter_grid = parameter_grid
        self.optimization_metric = optimization_metric
        self.maximize = maximize
        self.method = method
        self.n_iterations = n_iterations
        self.results: List[Dict] = []

    def optimize(
        self, tracker: Optional[ExperimentTracker] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Run hyperparameter optimization.

        Args:
            tracker: Optional experiment tracker
            **kwargs: Additional arguments for strategy_func

        Returns:
            Best parameters found
        """
        if self.method == "grid":
            return self._grid_search(tracker, **kwargs)
        elif self.method == "random":
            return self._random_search(tracker, **kwargs)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    def _grid_search(
        self, tracker: Optional[ExperimentTracker], **kwargs
    ) -> Dict[str, Any]:
        """Grid search over parameter grid."""
        param_names = list(self.parameter_grid.keys())
        param_values = list(self.parameter_grid.values())

        combinations = list(product(*param_values))

        best_score = -float("inf") if self.maximize else float("inf")
        best_params = None
        best_result = None

        for i, combo in enumerate(combinations):
            params = dict(zip(param_names, combo))
            logger.info(f"[{i + 1}/{len(combinations)}] Testing: {params}")

            exp_name = f"grid_search_{i}"
            exp = (
                Experiment(exp_name, tracker)
                if tracker
                else Experiment(exp_name, ExperimentTracker())
            )

            try:
                result = exp.run(self.strategy_func, params, **kwargs)

                score = result.metrics.get(self.optimization_metric, 0)

                self.results.append(
                    {
                        "parameters": params,
                        "score": score,
                        "metrics": result.metrics,
                    }
                )

                is_better = (self.maximize and score > best_score) or (
                    not self.maximize and score < best_score
                )

                if is_better:
                    best_score = score
                    best_params = params
                    best_result = result

            except Exception as e:
                logger.error(f"Failed for {params}: {e}")

        logger.info(f"Best params: {best_params}, Score: {best_score}")

        return {
            "best_parameters": best_params,
            "best_score": best_score,
            "all_results": self.results,
        }

    def _random_search(
        self, tracker: Optional[ExperimentTracker], **kwargs
    ) -> Dict[str, Any]:
        """Random search over parameter grid."""
        import random

        best_score = -float("inf") if self.maximize else float("inf")
        best_params = None
        best_result = None

        for i in range(self.n_iterations):
            params = {
                name: random.choice(values)
                for name, values in self.parameter_grid.items()
            }

            logger.info(f"[{i + 1}/{self.n_iterations}] Testing: {params}")

            exp = Experiment(f"random_search_{i}", tracker or ExperimentTracker())

            try:
                result = exp.run(self.strategy_func, params, **kwargs)

                score = result.metrics.get(self.optimization_metric, 0)

                self.results.append(
                    {
                        "parameters": params,
                        "score": score,
                        "metrics": result.metrics,
                    }
                )

                is_better = (self.maximize and score > best_score) or (
                    not self.maximize and score < best_score
                )

                if is_better:
                    best_score = score
                    best_params = params
                    best_result = result

            except Exception as e:
                logger.error(f"Failed for {params}: {e}")

        logger.info(f"Best params: {best_params}, Score: {best_score}")

        return {
            "best_parameters": best_params,
            "best_score": best_score,
            "all_results": self.results,
        }


class ResultsStorage:
    """
    Persistent storage for experiment results.
    """

    def __init__(self, storage_dir: str = "research/storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_dataframe(self, df: pd.DataFrame, name: str):
        """Save DataFrame to storage."""
        path = self.storage_dir / f"{name}.parquet"
        df.to_parquet(path, index=False)
        logger.info(f"Saved {name} to {path}")

    def load_dataframe(self, name: str) -> pd.DataFrame:
        """Load DataFrame from storage."""
        path = self.storage_dir / f"{name}.parquet"

        if path.exists():
            return pd.read_parquet(path)

        return pd.DataFrame()

    def save_dict(self, data: Dict, name: str):
        """Save dictionary to JSON."""
        path = self.storage_dir / f"{name}.json"

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {name} to {path}")

    def load_dict(self, name: str) -> Dict:
        """Load dictionary from JSON."""
        path = self.storage_dir / f"{name}.json"

        if path.exists():
            with open(path) as f:
                return json.load(f)

        return {}

    def list_experiments(self) -> List[str]:
        """List all stored experiments."""
        return [f.stem for f in self.storage_dir.glob("*.json")]


__all__ = [
    "Experiment",
    "ExperimentTracker",
    "ExperimentConfig",
    "ExperimentResult",
    "StrategyComparator",
    "HyperparameterOptimizer",
    "ResultsStorage",
]
