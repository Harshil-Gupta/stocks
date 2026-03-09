"""
Experiment Tracker - Log and manage experiments.

Usage:
    tracker = ExperimentTracker()
    
    with tracker.start_experiment("exp_001") as exp:
        exp.log_config({"agents": [...], "capital": 100000})
        exp.log_metrics({"sharpe": 1.5, "drawdown": 0.1})
        
        # Run backtest
        results = run_backtest(...)
        
        exp.log_results(results)
        
    # List experiments
    tracker.list_experiments()
    
    # Compare
    tracker.compare(["exp_001", "exp_002"])
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class Experiment:
    """Single experiment container."""
    
    def __init__(self, exp_id: str, base_path: str):
        self.exp_id = exp_id
        self.base_path = Path(base_path) / exp_id
        self.config_path = self.base_path / "config.json"
        self.metrics_path = self.base_path / "metrics.json"
        self.results_path = self.base_path / "results.json"
        self.logs_path = self.base_path / "logs.txt"
        
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self._config: Dict = {}
        self._metrics: Dict = {}
        self._results: Dict = {}
        self._logs: List[str] = []
        self._start_time = datetime.now()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._save()
    
    def log_config(self, config: Dict) -> None:
        """Log experiment configuration."""
        self._config = config
        self._save()
    
    def log_metrics(self, metrics: Dict) -> None:
        """Log experiment metrics."""
        self._metrics.update(metrics)
        self._save()
    
    def log_results(self, results: Dict) -> None:
        """Log final results."""
        self._results = results
        self._save()
    
    def log(self, message: str) -> None:
        """Log a message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._logs.append(f"[{timestamp}] {message}")
        self._save()
    
    def _save(self) -> None:
        """Save all data to disk."""
        if self._config:
            with open(self.config_path, "w") as f:
                json.dump({
                    **self._config,
                    "start_time": self._start_time.isoformat(),
                    "exp_id": self.exp_id
                }, f, indent=2)
        
        if self._metrics:
            with open(self.metrics_path, "w") as f:
                json.dump(self._metrics, f, indent=2)
        
        if self._results:
            with open(self.results_path, "w") as f:
                json.dump(self._results, f, indent=2, default=str)
        
        if self._logs:
            with open(self.logs_path, "w") as f:
                f.write("\n".join(self._logs))
    
    def get_summary(self) -> Dict:
        """Get experiment summary."""
        return {
            "exp_id": self.exp_id,
            "start_time": self._start_time.isoformat(),
            "config": self._config,
            "metrics": self._metrics,
            "results": self._results
        }


class ExperimentTracker:
    """
    Track and manage experiments.
    
    Structure:
        experiments/
            exp_001/
                config.json
                metrics.json
                results.json
                logs.txt
            exp_002/
                ...
    """
    
    def __init__(self, base_path: str = "experiments"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def start_experiment(self, exp_id: Optional[str] = None) -> Experiment:
        """
        Start a new experiment.
        
        Args:
            exp_id: Optional experiment ID (auto-generated if not provided)
            
        Returns:
            Experiment context manager
        """
        if exp_id is None:
            exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return Experiment(exp_id, str(self.base_path))
    
    def list_experiments(self) -> List[Dict]:
        """List all experiments."""
        experiments = []
        
        for exp_dir in sorted(self.base_path.iterdir()):
            if not exp_dir.is_dir():
                continue
            
            config_path = exp_dir / "config.json"
            metrics_path = exp_dir / "metrics.json"
            
            exp_info = {"exp_id": exp_dir.name}
            
            if config_path.exists():
                with open(config_path) as f:
                    exp_info["config"] = json.load(f)
            
            if metrics_path.exists():
                with open(metrics_path) as f:
                    exp_info["metrics"] = json.load(f)
            
            experiments.append(exp_info)
        
        return sorted(experiments, key=lambda x: x.get("exp_id", ""), reverse=True)
    
    def load_experiment(self, exp_id: str) -> Experiment:
        """Load an existing experiment."""
        exp = Experiment(exp_id, str(self.base_path))
        
        if exp.config_path.exists():
            with open(exp.config_path) as f:
                exp._config = json.load(f)
        
        if exp.metrics_path.exists():
            with open(exp.metrics_path) as f:
                exp._metrics = json.load(f)
        
        if exp.results_path.exists():
            with open(exp.results_path) as f:
                exp._results = json.load(f)
        
        if exp.logs_path.exists():
            with open(exp.logs_path) as f:
                exp._logs = f.read().split("\n")
        
        return exp
    
    def compare(self, exp_ids: List[str]) -> pd.DataFrame:
        """Compare multiple experiments."""
        rows = []
        
        for exp_id in exp_ids:
            try:
                exp = self.load_experiment(exp_id)
                row = {
                    "exp_id": exp_id,
                    **exp._config,
                    **exp._metrics
                }
                rows.append(row)
            except Exception as e:
                logger.warning(f"Could not load experiment {exp_id}: {e}")
        
        return pd.DataFrame(rows)
    
    def get_best(self, metric: str = "sharpe_ratio") -> Optional[Dict]:
        """Get best experiment by metric."""
        experiments = self.list_experiments()
        
        if not experiments:
            return None
        
        best = None
        best_value = float("-inf")
        
        for exp in experiments:
            value = exp.get("metrics", {}).get(metric, 0)
            if value > best_value:
                best_value = value
                best = exp
        
        return best
    
    def delete_experiment(self, exp_id: str) -> bool:
        """Delete an experiment."""
        exp_path = self.base_path / exp_id
        
        if not exp_path.exists():
            return False
        
        shutil.rmtree(exp_path)
        return True
    
    def export_summary(self, output_path: str = "experiments_summary.csv") -> None:
        """Export all experiments to CSV."""
        experiments = self.list_experiments()
        
        if not experiments:
            logger.warning("No experiments to export")
            return
        
        rows = []
        for exp in experiments:
            row = {
                "exp_id": exp.get("exp_id"),
                **exp.get("config", {}),
                **exp.get("metrics", {})
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        
        logger.info(f"Exported {len(df)} experiments to {output_path}")


class MLflowTracker:
    """
    Optional MLflow integration for experiment tracking.
    
    Usage:
        tracker = MLflowTracker()
        tracker.log_param("model", "lightgbm")
        tracker.log_metric("sharpe", 1.5)
    """
    
    def __init__(self, experiment_name: str = "quant_trader"):
        self.experiment_name = experiment_name
        self._client = None
        self._run = None
        
        try:
            import mlflow
            mlflow.set_experiment(experiment_name)
            self._client = mlflow
        except ImportError:
            logger.warning("MLflow not installed, using basic tracker")
    
    def log_param(self, key: str, value: Any) -> None:
        """Log a parameter."""
        if self._client:
            self._client.log_param(key, value)
    
    def log_metric(self, key: str, value: float) -> None:
        """Log a metric."""
        if self._client:
            self._client.log_metric(key, value)
    
    def log_params(self, params: Dict) -> None:
        """Log multiple parameters."""
        for key, value in params.items():
            self.log_param(key, value)
    
    def log_metrics(self, metrics: Dict) -> None:
        """Log multiple metrics."""
        for key, value in metrics.items():
            self.log_metric(key, value)
    
    def start_run(self) -> None:
        """Start MLflow run."""
        if self._client:
            self._client.start_run()
    
    def end_run(self) -> None:
        """End MLflow run."""
        if self._client:
            self._client.end_run()


class WeightsAndBiasesTracker:
    """
    Optional Weights & Biases integration.
    """
    
    def __init__(self, project_name: str = "quant_trader"):
        self.project_name = project_name
        self._run = None
        
        try:
            import wandb
            wandb.init(project=project_name)
            self._run = wandb
        except ImportError:
            logger.warning("Weights & Biases not installed")
    
    def log(self, metrics: Dict) -> None:
        """Log metrics."""
        if self._run:
            self._run.log(metrics)
    
    def finish(self) -> None:
        """Finish run."""
        if self._run:
            self._run.finish()
