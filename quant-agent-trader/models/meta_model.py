"""
Meta Model Training Module - Complete ML pipeline for training and managing meta models.

Features:
- Walk-forward training (train on past, test on future)
- Model registry for version management
- Feature importance analysis
- Multiple model backends (LightGBM, XGBoost, sklearn)

Usage:
    from models.meta_model import MetaModelTrainer, ModelRegistry, WalkForwardTrainer

    # Train a model
    trainer = MetaModelTrainer()
    trainer.train(dataset, target="target_binary_5d")

    # Walk-forward training
    wft = WalkForwardTrainer()
    results = wft.run_walk_forward(data, n_splits=5)

    # Get latest model
    registry = ModelRegistry()
    model = registry.load_latest()
"""

from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pickle
import json
import os
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """Metadata for a trained model."""

    version: str
    model_type: str
    training_data_range: str
    features_used: List[str]
    target: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    created_at: str
    training_samples: int
    hyperparams: Dict[str, Any] = field(default_factory=dict)


class ModelRegistry:
    """
    Model registry for version management.

    Stores models in:
        models/trained/
            meta_model_v1.pkl
            meta_model_v2.pkl
            ...

    Registry file:
        models/registry.json
    """

    def __init__(self, base_path: str = "models"):
        self.base_path = base_path
        self.trained_path = os.path.join(base_path, "trained")
        self.registry_file = os.path.join(base_path, "registry.json")

        os.makedirs(self.trained_path, exist_ok=True)

        if not os.path.exists(self.registry_file):
            self._save_registry({})

    def _load_registry(self) -> Dict:
        """Load registry from file."""
        try:
            with open(self.registry_file, "r") as f:
                return json.load(f)
        except:
            return {}

    def _save_registry(self, registry: Dict) -> None:
        """Save registry to file."""
        with open(self.registry_file, "w") as f:
            json.dump(registry, f, indent=2)

    def register_model(
        self, model: Any, metadata: ModelMetadata, features: List[str]
    ) -> str:
        """
        Register a new model version.

        Args:
            model: Trained model object
            metadata: Model metadata
            features: List of feature names used

        Returns:
            Version string (e.g., "v3")
        """
        registry = self._load_registry()

        version = metadata.version

        model_path = os.path.join(self.trained_path, f"meta_model_{version}.pkl")

        with open(model_path, "wb") as f:
            pickle.dump(
                {"model": model, "metadata": asdict(metadata), "features": features}, f
            )

        registry[version] = {
            "model_path": model_path,
            "created_at": metadata.created_at,
            "accuracy": metadata.accuracy,
            "sharpe_ratio": metadata.sharpe_ratio,
            "training_samples": metadata.training_samples,
        }

        self._save_registry(registry)

        logger.info(f"Registered model {version} at {model_path}")

        return version

    def load_model(self, version: str) -> Tuple[Any, ModelMetadata, List[str]]:
        """
        Load a specific model version.

        Args:
            version: Model version (e.g., "v1")

        Returns:
            Tuple of (model, metadata, features)
        """
        model_path = os.path.join(self.trained_path, f"meta_model_{version}.pkl")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model {version} not found at {model_path}")

        try:
            with open(model_path, "rb") as f:
                data = pickle.load(f)
        except pickle.UnpicklingError as e:
            logger.error(f"Failed to unpickle model {version}: {e}")
            raise ValueError(f"Corrupted model file: {model_path}") from e
        except Exception as e:
            logger.error(f"Error loading model {version}: {e}")
            raise

        metadata = ModelMetadata(**data["metadata"])

        logger.info(f"Loaded model {version}")

        return data["model"], metadata, data["features"]

    def load_latest(self) -> Tuple[Any, ModelMetadata, List[str]]:
        """
        Load the latest model.

        Returns:
            Tuple of (model, metadata, features)
        """
        registry = self._load_registry()

        if not registry:
            raise ValueError("No models registered")

        versions = sorted(registry.keys(), key=lambda v: int(v[1:]))
        latest_version = versions[-1]

        return self.load_model(latest_version)

    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models."""
        registry = self._load_registry()

        models = []
        for version, info in registry.items():
            models.append({"version": version, **info})

        return sorted(models, key=lambda m: m["version"], reverse=True)

    def get_best_model(self, metric: str = "sharpe_ratio") -> Tuple[str, Dict]:
        """
        Get the best model by a specific metric.

        Args:
            metric: Metric to optimize (accuracy, sharpe_ratio, win_rate)

        Returns:
            Tuple of (version, info)
        """
        registry = self._load_registry()

        if not registry:
            raise ValueError("No models registered")

        best_version = max(registry.keys(), key=lambda v: registry[v].get(metric, 0))

        return best_version, registry[best_version]


class MetaModelTrainer:
    """
    Trains meta models for signal aggregation.

    Supports:
    - LightGBM, XGBoost, sklearn
    - Feature selection
    - Hyperparameter tuning
    - Comprehensive metrics
    """

    def __init__(self, model_type: str = "lightgbm", random_state: int = 42):
        self.model_type = model_type
        self.random_state = random_state
        self.model = None
        self.feature_names: List[str] = []
        self.metadata: Optional[ModelMetadata] = None
        self.scaler = None

    def train(
        self,
        dataset: pd.DataFrame,
        target: str = "target_binary_5d",
        feature_cols: Optional[List[str]] = None,
        test_size: float = 0.2,
        hyperparams: Optional[Dict] = None,
    ) -> Dict[str, float]:
        """
        Train a meta model.

        Args:
            dataset: Training data
            target: Target column name
            feature_cols: Feature columns to use
            test_size: Test set fraction
            hyperparams: Model hyperparameters

        Returns:
            Training metrics
        """
        exclude_cols = [
            "timestamp",
            "symbol",
            "date",
            "future_return_5d",
            "future_return_10d",
            "future_return_20d",
            "target_binary_5d",
            "target_binary_10d",
            "target_binary_20d",
        ]

        if feature_cols is None:
            feature_cols = [
                c
                for c in dataset.columns
                if c not in exclude_cols and dataset[c].dtype in [np.float64, np.int64]
            ]

        self.feature_names = feature_cols

        df = dataset.dropna(subset=[target] + feature_cols)

        X = df[feature_cols].fillna(0)
        y = df[target]

        from sklearn.model_selection import train_test_split

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.random_state, stratify=y
        )

        if self.model_type == "lightgbm":
            self._train_lightgbm(X_train, X_test, y_train, y_test, hyperparams or {})
        elif self.model_type == "xgboost":
            self._train_xgboost(X_train, X_test, y_train, y_test, hyperparams or {})
        else:
            self._train_sklearn(X_train, X_test, y_train, y_test, hyperparams or {})

        metrics = self._evaluate(X_test, y_test)

        start_date = df["timestamp"].min() if "timestamp" in df.columns else "unknown"
        end_date = df["timestamp"].max() if "timestamp" in df.columns else "unknown"

        self.metadata = ModelMetadata(
            version=f"v{int(datetime.now().timestamp())}",
            model_type=self.model_type,
            training_data_range=f"{start_date} to {end_date}",
            features_used=feature_cols,
            target=target,
            accuracy=metrics["accuracy"],
            precision=metrics["precision"],
            recall=metrics["recall"],
            f1=metrics["f1"],
            sharpe_ratio=metrics.get("sharpe_ratio", 0),
            max_drawdown=metrics.get("max_drawdown", 0),
            win_rate=metrics.get("win_rate", 0),
            created_at=datetime.now().isoformat(),
            training_samples=len(X_train),
            hyperparams=hyperparams or {},
        )

        return metrics

    def _train_lightgbm(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
        hyperparams: Dict,
    ) -> None:
        """Train LightGBM model."""
        try:
            import lightgbm as lgb

            params = {
                "n_estimators": hyperparams.get("n_estimators", 100),
                "max_depth": hyperparams.get("max_depth", 5),
                "learning_rate": hyperparams.get("learning_rate", 0.1),
                "num_leaves": hyperparams.get("num_leaves", 31),
                "random_state": self.random_state,
                "verbose": -1,
            }

            self.model = lgb.LGBMClassifier(**params)
            self.model.fit(X_train, y_train)

            logger.info("LightGBM model trained")

        except ImportError:
            logger.warning("LightGBM not available, using sklearn")
            self.model_type = "sklearn"
            self._train_sklearn(X_train, X_test, y_train, y_test, hyperparams)

    def _train_xgboost(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
        hyperparams: Dict,
    ) -> None:
        """Train XGBoost model."""
        try:
            import xgboost as xgb

            params = {
                "n_estimators": hyperparams.get("n_estimators", 100),
                "max_depth": hyperparams.get("max_depth", 5),
                "learning_rate": hyperparams.get("learning_rate", 0.1),
                "random_state": self.random_state,
                "use_label_encoder": False,
                "eval_metric": "logloss",
            }

            self.model = xgb.XGBClassifier(**params)
            self.model.fit(X_train, y_train)

            logger.info("XGBoost model trained")

        except ImportError:
            logger.warning("XGBoost not available, using sklearn")
            self.model_type = "sklearn"
            self._train_sklearn(X_train, X_test, y_train, y_test, hyperparams)

    def _train_sklearn(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
        hyperparams: Dict,
    ) -> None:
        """Train sklearn model."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        if hyperparams.get("use_logistic"):
            self.scaler = StandardScaler()
            X_train = pd.DataFrame(
                self.scaler.fit_transform(X_train), columns=X_train.columns
            )
            X_test = pd.DataFrame(self.scaler.transform(X_test), columns=X_test.columns)
            self.model = LogisticRegression(
                random_state=self.random_state, max_iter=1000
            )
        else:
            self.model = RandomForestClassifier(
                n_estimators=hyperparams.get("n_estimators", 100),
                max_depth=hyperparams.get("max_depth", 10),
                random_state=self.random_state,
            )

        self.model.fit(X_train, y_train)

        logger.info(f"Sklearn {type(self.model).__name__} trained")

    def _evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
        """Evaluate model on test set."""
        from sklearn.metrics import (
            accuracy_score,
            precision_score,
            recall_score,
            f1_score,
            confusion_matrix,
        )

        y_pred = self.model.predict(X_test)

        if hasattr(self.model, "predict_proba"):
            y_proba = self.model.predict_proba(X_test)[:, 1]
        else:
            y_proba = y_pred.astype(float)

        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0),
        }

        returns = np.where(y_proba > 0.6, 1, -1) * np.where(y_test == 1, 1, -1)

        metrics["win_rate"] = (returns > 0).mean()

        returns_series = pd.Series(returns)
        if returns_series.std() > 0:
            metrics["sharpe_ratio"] = (
                returns_series.mean() / returns_series.std() * np.sqrt(252)
            )
        else:
            metrics["sharpe_ratio"] = 0

        cumulative = (1 + returns_series).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        metrics["max_drawdown"] = abs(drawdown.min())

        return metrics

    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance from trained model."""
        if self.model is None:
            return pd.DataFrame()

        if hasattr(self.model, "feature_importances_"):
            importance = pd.DataFrame(
                {
                    "feature": self.feature_names,
                    "importance": self.model.feature_importances_,
                }
            ).sort_values("importance", ascending=False)
        elif hasattr(self.model, "coef_"):
            importance = pd.DataFrame(
                {
                    "feature": self.feature_names,
                    "importance": np.abs(self.model.coef_[0]),
                }
            ).sort_values("importance", ascending=False)
        else:
            return pd.DataFrame()

        return importance

    def save(self, path: str) -> None:
        """Save model to disk."""
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "model": self.model,
                    "feature_names": self.feature_names,
                    "metadata": asdict(self.metadata) if self.metadata else None,
                    "scaler": self.scaler,
                    "model_type": self.model_type,
                },
                f,
            )

        logger.info(f"Model saved to {path}")

    def load(self, path: str) -> None:
        """Load model from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.model = data["model"]
        self.feature_names = data["feature_names"]
        self.scaler = data.get("scaler")
        self.model_type = data.get("model_type", "sklearn")

        if data.get("metadata"):
            self.metadata = ModelMetadata(**data["metadata"])

        logger.info(f"Model loaded from {path}")


class WalkForwardTrainer:
    """
    Walk-forward training for time series models.

    Mimics real trading conditions by training on past data
    and testing on future data.

    Example timeline:
        train: 2018-2021, test: 2022
        train: 2019-2022, test: 2023
        train: 2020-2023, test: 2024
    """

    def __init__(self, train_years: int = 3, test_years: int = 1, step_years: int = 1):
        self.train_years = train_years
        self.test_years = test_years
        self.step_years = step_years

    def run_walk_forward(
        self,
        dataset: pd.DataFrame,
        target: str = "target_binary_5d",
        model_type: str = "lightgbm",
    ) -> Dict[str, Any]:
        """
        Run walk-forward training.

        Args:
            dataset: Full dataset with features and labels
            target: Target column
            model_type: Model type to train

        Returns:
            Dictionary with results for each fold
        """
        if "timestamp" not in dataset.columns:
            raise ValueError("Dataset must have 'timestamp' column")

        dataset = dataset.sort_values("timestamp").reset_index(drop=True)

        min_date = dataset["timestamp"].min()
        max_date = dataset["timestamp"].max()

        results = []

        current_train_end = min_date + pd.DateOffset(years=self.train_years)
        test_end = current_train_end + pd.DateOffset(years=self.test_years)

        fold = 0

        while test_end <= max_date:
            train_data = dataset[
                (dataset["timestamp"] >= min_date)
                & (dataset["timestamp"] < current_train_end)
            ]

            test_data = dataset[
                (dataset["timestamp"] >= current_train_end)
                & (dataset["timestamp"] < test_end)
            ]

            if len(train_data) < 100 or len(test_data) < 50:
                logger.warning(f"Skipping fold {fold}: insufficient data")
                current_train_end = current_train_end + pd.DateOffset(
                    years=self.step_years
                )
                test_end = test_end + pd.DateOffset(years=self.step_years)
                continue

            logger.info(
                f"Fold {fold}: train {len(train_data)} samples, "
                f"test {len(test_data)} samples"
            )

            trainer = MetaModelTrainer(model_type=model_type)
            metrics = trainer.train(train_data, target=target)

            test_features = [
                c
                for c in test_data.columns
                if c
                not in [
                    "timestamp",
                    "symbol",
                    target,
                    "future_return_5d",
                    "future_return_10d",
                    "future_return_20d",
                    "target_binary_5d",
                    "target_binary_10d",
                    "target_binary_20d",
                ]
            ]

            X_test = test_data[test_features].fillna(0)
            y_test = test_data[target]

            y_pred = trainer.model.predict(X_test)

            from sklearn.metrics import accuracy_score

            fold_result = {
                "fold": fold,
                "train_period": f"{min_date.year}-{current_train_end.year}",
                "test_period": f"{current_train_end.year}-{test_end.year}",
                "train_samples": len(train_data),
                "test_samples": len(test_data),
                "accuracy": accuracy_score(y_test, y_pred),
                **metrics,
            }

            results.append(fold_result)

            min_date = min_date + pd.DateOffset(years=self.step_years)
            current_train_end = current_train_end + pd.DateOffset(years=self.step_years)
            test_end = test_end + pd.DateOffset(years=self.step_years)
            fold += 1

        return {"folds": results, "summary": self._summarize_results(results)}

    def _summarize_results(self, results: List[Dict]) -> Dict:
        """Summarize walk-forward results."""
        if not results:
            return {}

        metrics = ["accuracy", "precision", "recall", "f1", "sharpe_ratio", "win_rate"]

        summary = {}

        for metric in metrics:
            values = [r[metric] for r in results if metric in r]
            if values:
                summary[f"avg_{metric}"] = np.mean(values)
                summary[f"std_{metric}"] = np.std(values)

        return summary


class LiveInference:
    """
    Live inference pipeline for real-time predictions.

    Pipeline:
        agents run -> feature vector -> meta model -> decision
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.feature_names: List[str] = []
        self.scaler = None

        if model_path:
            self.load(model_path)

    def load(self, path: str) -> None:
        """Load model from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.model = data["model"]
        self.feature_names = data["feature_names"]
        self.scaler = data.get("scaler")

        logger.info(f"Loaded inference model from {path}")

    def predict(
        self,
        features: Dict[str, float],
        buy_threshold: float = 0.6,
        sell_threshold: float = 0.4,
    ) -> Dict[str, Any]:
        """
        Make a prediction.

        Args:
            features: Feature dictionary
            buy_threshold: Probability threshold for buy
            sell_threshold: Probability threshold for sell

        Returns:
            Prediction result with decision and probability
        """
        if self.model is None:
            raise ValueError("No model loaded")

        feature_vector = self._prepare_features(features)

        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(feature_vector)[0][1]
        else:
            proba = self.model.predict(feature_vector)[0]

        if proba >= buy_threshold:
            decision = "buy"
        elif proba <= sell_threshold:
            decision = "sell"
        else:
            decision = "hold"

        confidence = abs(proba - 0.5) * 2 * 100

        return {
            "probability": float(proba),
            "decision": decision,
            "confidence": float(confidence),
        }

    def _prepare_features(self, features: Dict[str, float]) -> pd.DataFrame:
        """Prepare feature vector for prediction."""
        vector = {}

        for fname in self.feature_names:
            vector[fname] = features.get(fname, 0.0)

        df = pd.DataFrame([vector])

        if self.scaler:
            df = pd.DataFrame(self.scaler.transform(df), columns=df.columns)

        return df


def create_default_model(dataset: pd.DataFrame, output_dir: str = "models") -> str:
    """
    Create a default meta model from dataset.

    Args:
        dataset: Training data
        output_dir: Output directory

    Returns:
        Path to saved model
    """
    os.makedirs(output_dir, exist_ok=True)

    trainer = MetaModelTrainer(model_type="lightgbm")
    trainer.train(dataset, target="target_binary_5d")

    version = f"v1"
    model_path = os.path.join(output_dir, "trained", f"meta_model_{version}.pkl")
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    trainer.save(model_path)

    registry = ModelRegistry(base_path=output_dir)
    registry.register_model(trainer.model, trainer.metadata, trainer.feature_names)

    return model_path
