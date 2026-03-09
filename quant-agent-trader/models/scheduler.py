"""
Continuous Retraining Scheduler - Automates model retraining.

Schedule:
    daily   → collect new features
    weekly  → retrain model
    monthly → full retraining + evaluation

Usage:
    scheduler = RetrainingScheduler()
    scheduler.run_daily_update()
    scheduler.run_weekly_retrain()
    scheduler.run_monthly_full_retrain()
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import pandas as pd
import logging
import json

from data.feature_store import FeatureStore
from models.meta_model import MetaModelTrainer, WalkForwardTrainer, ModelRegistry, LiveInference
from signals.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)


class RetrainingScheduler:
    """
    Scheduler for automated model retraining.
    
    Pipeline:
        cron job
            ↓
        update feature store
            ↓
        train new model
            ↓
        validate performance
            ↓
        deploy if better
    """
    
    def __init__(
        self,
        feature_store: Optional[FeatureStore] = None,
        model_dir: str = "models",
        min_samples_for_retrain: int = 500
    ):
        self.feature_store = feature_store or FeatureStore()
        self.model_dir = model_dir
        self.min_samples_for_retrain = min_samples_for_retrain
        self.registry = ModelRegistry(base_path=model_dir)
    
    def run_daily_update(
        self,
        new_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Daily: Collect new features.
        
        Args:
            new_data: New feature data to add
            
        Returns:
            Status dictionary
        """
        logger.info("[SCHEDULER] Running daily update")
        
        if new_data is not None:
            self.feature_store.write_batch(new_data.to_dict("records"))
        
        stats = self.feature_store.get_stats()
        
        logger.info(f"[SCHEDULER] Daily update complete. Total samples: {stats.get('rows', 0)}")
        
        return {
            "status": "success",
            "total_samples": stats.get("rows", 0),
            "timestamp": datetime.now().isoformat()
        }
    
    def run_weekly_retrain(
        self,
        target: str = "target_binary_5d",
        model_type: str = "lightgbm"
    ) -> Dict[str, Any]:
        """
        Weekly: Retrain model with latest data.
        
        Args:
            target: Target column
            model_type: Model type
            
        Returns:
            Training results
        """
        logger.info("[SCHEDULER] Running weekly retrain")
        
        dataset = self.feature_store.read_features()
        
        if len(dataset) < self.min_samples_for_retrain:
            logger.warning(f"[SCHEDULER] Insufficient data: {len(dataset)} < {self.min_samples_for_retrain}")
            return {"status": "skipped", "reason": "insufficient_data"}
        
        trainer = MetaModelTrainer(model_type=model_type)
        metrics = trainer.train(dataset, target=target)
        
        models = self.registry.list_models()
        
        if models:
            best_version, best_info = self.registry.get_best_model("sharpe_ratio")
            best_sharpe = best_info.get("sharpe_ratio", 0)
        else:
            best_sharpe = 0
        
        new_sharpe = metrics.get("sharpe_ratio", 0)
        
        if new_sharpe >= best_sharpe * 0.9:
            version = self.registry.register_model(
                trainer.model,
                trainer.metadata,
                trainer.feature_names
            )
            
            logger.info(f"[SCHEDULER] Registered new model version {version}")
            
            return {
                "status": "deployed",
                "version": version,
                "metrics": metrics,
                "improvement": new_sharpe - best_sharpe
            }
        else:
            logger.warning(f"[SCHEDULER] New model worse than best ({new_sharpe} < {best_sharpe}), not deploying")
            
            return {
                "status": "rejected",
                "metrics": metrics,
                "best_sharpe": best_sharpe,
                "reason": "performance_degradation"
            }
    
    def run_monthly_full_retrain(
        self,
        target: str = "target_binary_5d"
    ) -> Dict[str, Any]:
        """
        Monthly: Full retraining with walk-forward validation.
        
        Args:
            target: Target column
            
        Returns:
            Full evaluation results
        """
        logger.info("[SCHEDULER] Running monthly full retrain with walk-forward")
        
        dataset = self.feature_store.read_features()
        
        if len(dataset) < 1000:
            logger.warning(f"[SCHEDULER] Insufficient data for walk-forward: {len(dataset)}")
            return {"status": "skipped", "reason": "insufficient_data"}
        
        wft = WalkForwardTrainer(train_years=3, test_years=1)
        results = wft.run_walk_forward(dataset, target=target)
        
        summary = results.get("summary", {})
        
        avg_accuracy = summary.get("avg_accuracy", 0)
        
        trainer = MetaModelTrainer(model_type="lightgbm")
        trainer.train(dataset, target=target)
        
        importance = trainer.get_feature_importance()
        
        version = self.registry.register_model(
            trainer.model,
            trainer.metadata,
            trainer.feature_names
        )
        
        logger.info(f"[SCHEDULER] Monthly retrain complete. New version: {version}")
        
        return {
            "status": "success",
            "version": version,
            "walk_forward_summary": summary,
            "avg_accuracy": avg_accuracy,
            "feature_importance": importance.head(10).to_dict("records") if not importance.empty else [],
            "metadata": trainer.metadata.__dict__ if trainer.metadata else {}
        }


class ScheduledRunner:
    """
    Wrapper for running scheduled tasks.
    
    Usage:
        runner = ScheduledRunner()
        
        # Run daily
        runner.run_task("daily")
        
        # Run weekly  
        runner.run_task("weekly")
        
        # Run monthly
        runner.run_task("monthly")
    """
    
    def __init__(self):
        self.scheduler = RetrainingScheduler()
        self.last_daily = None
        self.last_weekly = None
        self.last_monthly = None
    
    def run_task(self, task_type: str) -> Dict[str, Any]:
        """
        Run a scheduled task.
        
        Args:
            task_type: "daily", "weekly", or "monthly"
            
        Returns:
            Task results
        """
        if task_type == "daily":
            return self.scheduler.run_daily_update()
        elif task_type == "weekly":
            return self.scheduler.run_weekly_retrain()
        elif task_type == "monthly":
            return self.scheduler.run_monthly_full_retrain()
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    def should_run(self, task_type: str) -> bool:
        """Check if task should run based on schedule."""
        now = datetime.now()
        
        if task_type == "daily":
            if self.last_daily is None:
                return True
            return (now - self.last_daily).days >= 1
        
        if task_type == "weekly":
            if self.last_weekly is None:
                return True
            return (now - self.last_weekly).days >= 7
        
        if task_type == "monthly":
            if self.last_monthly is None:
                return True
            return (now - self.last_monthly).days >= 30
        
        return False
    
    def update_last_run(self, task_type: str) -> None:
        """Update last run timestamp."""
        now = datetime.now()
        
        if task_type == "daily":
            self.last_daily = now
        elif task_type == "weekly":
            self.last_weekly = now
        elif task_type == "monthly":
            self.last_monthly = now


def run_as_cron():
    """
    Entry point for cron-based execution.
    
    Add to crontab:
        0 6 * * * python -m models.scheduler run daily
        0 7 * * 0 python -m models.scheduler run weekly
        0 8 1 * * python -m models.scheduler run monthly
    """
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python -m models.scheduler run <daily|weekly|monthly>")
        sys.exit(1)
    
    command = sys.argv[2]
    
    runner = ScheduledRunner()
    result = runner.run_task(command)
    
    print(json.dumps(result, indent=2))
    
    if result.get("status") in ["success", "deployed"]:
        sys.exit(0)
    else:
        sys.exit(1)
