"""
Feature Pipeline - Production-ready feature engineering with proper isolation.

This module provides:
- FeatureRegistry integration for pluggable features
- Feature isolation (no lookahead)
- Proper train/test splits for ML
- Feature caching and versioning
- Cross-validation support

Key principles:
1. Features never use future data
2. Labels computed after features
3. Train/test split with temporal gap
4. Feature caching with versioning
"""

from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
import hashlib
import logging
from pathlib import Path

from features.config import FeatureConfig, FeatureMode
from features.registry import FeatureRegistry, FeatureGenerator

logger = logging.getLogger(__name__)


class FeaturePipeline:
    """
    Production feature pipeline with proper data isolation.

    Uses FeatureRegistry for pluggable feature generators.
    """

    def __init__(self, config: Optional[FeatureConfig] = None):
        self.config = config or FeatureConfig()
        self.feature_cache: Dict[str, pd.DataFrame] = {}
        self.feature_hash: Optional[str] = None
        self._generators: Dict[str, FeatureGenerator] = {}
        self._initialize_generators()

    def _initialize_generators(self) -> None:
        """Initialize feature generators from registry."""
        from features.generators import (
            ReturnsGenerator,
            SMAGenerator,
            EMAGenerator,
            RSIGenerator,
            MACDGenerator,
            BollingerBandsGenerator,
            ATRGenerator,
            VolatilityGenerator,
            MomentumGenerator,
            ROCGenerator,
            VolumeIndicatorsGenerator,
            StochasticGenerator,
            CCIGenerator,
            ADXGenerator,
            WilliamsRGenerator,
            MFIGenerator,
            VWAPGenerator,
            PricePositionGenerator,
            MACrossoverGenerator,
        )

        lookback_windows = self.config.lookback_windows

        generator_configs = {
            "returns": ReturnsGenerator,
            "sma": lambda: SMAGenerator(windows=lookback_windows),
            "ema": lambda: EMAGenerator(spans=lookback_windows),
            "rsi": RSIGenerator,
            "macd": MACDGenerator,
            "bollinger_bands": BollingerBandsGenerator,
            "atr": ATRGenerator,
            "volatility": VolatilityGenerator,
            "momentum": MomentumGenerator,
            "roc": ROCGenerator,
            "volume_indicators": VolumeIndicatorsGenerator,
            "stochastic": StochasticGenerator,
            "cci": CCIGenerator,
            "adx": ADXGenerator,
            "williams_r": WilliamsRGenerator,
            "mfi": MFIGenerator,
            "vwap": VWAPGenerator,
            "price_position": PricePositionGenerator,
            "ma_crossover": MACrossoverGenerator,
        }

        for feature_name in self.config.features:
            if feature_name in generator_configs:
                config_fn = generator_configs[feature_name]
                if callable(config_fn) and not isinstance(config_fn, type):
                    self._generators[feature_name] = config_fn()
                else:
                    self._generators[feature_name] = config_fn()

    def compute_features(
        self, data: pd.DataFrame, mode: Optional[FeatureMode] = None
    ) -> pd.DataFrame:
        """
        Compute features with proper temporal isolation.

        Args:
            data: Raw OHLCV data with DatetimeIndex
            mode: Feature computation mode (training/inference/backtest)

        Returns:
            DataFrame with features (and labels if training mode)
        """
        mode = mode or self.config.mode

        df = data.copy()

        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        df = df.sort_index()

        df = self._compute_base_features(df)

        for feature_name, generator in self._generators.items():
            try:
                feature_df = generator.compute(df)
                for col in feature_df.columns:
                    df[col] = feature_df[col]
            except Exception as e:
                logger.warning(f"Failed to compute feature {feature_name}: {e}")

        if mode == FeatureMode.TRAINING:
            df = self._compute_labels(df)

        min_lookback = self._get_min_lookback()
        df = df.iloc[min_lookback:]

        return df

    def _compute_base_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute base price features."""
        if "returns" not in df.columns:
            df["returns"] = df["close"].pct_change()
        if "log_returns" not in df.columns:
            df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
        return df

    def _compute_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute future return labels.

        IMPORTANT: Labels are computed AFTER features to avoid leakage.
        The model learns to predict returns from past features only.
        """
        horizons = self.config.label_config.horizons
        threshold = self.config.label_config.threshold

        for horizon in horizons:
            df[f"future_return_{horizon}d"] = (
                df["close"].shift(-horizon) / df["close"] - 1
            )

            if self.config.label_config.binary:
                df[f"target_binary_{horizon}d"] = (
                    df[f"future_return_{horizon}d"] > threshold
                ).astype(int)

        return df

    def _get_min_lookback(self) -> int:
        """Get minimum lookback required based on configured features."""
        max_lookback = self.config.min_history

        for generator in self._generators.values():
            max_lookback = max(max_lookback, generator.lookback_required)

        return max_lookback

    def create_train_test_split(
        self,
        data: pd.DataFrame,
        train_end: Any,
        test_start: Any,
        test_end: Any,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Create temporal train/test split with gap.

        Args:
            data: Feature DataFrame
            train_end: Last date of training data
            test_start: First date of test data (includes gap)
            test_end: Last date of test data

        Returns:
            Train and test DataFrames
        """
        train_data = data.loc[:train_end].copy()

        max_horizon = max(self.config.label_config.horizons)
        train_data = train_data.iloc[:-max_horizon]

        test_data = data.loc[test_start:test_end].copy()

        label_cols = [
            c for c in test_data.columns if "future_return" in c or "target_binary" in c
        ]
        test_data = test_data.drop(columns=label_cols, errors="ignore")

        logger.info(
            f"Train split: {len(train_data)} rows, Test split: {len(test_data)} rows"
        )

        return train_data, test_data

    def create_temporal_splits(
        self,
        data: pd.DataFrame,
        n_splits: int = 5,
        gap_days: int = 20,
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Create temporal cross-validation splits.

        Args:
            data: Feature DataFrame
            n_splits: Number of CV splits
            gap_days: Gap between train and test

        Returns:
            List of (train, test) tuples
        """
        splits = []
        n = len(data)
        test_size = n // (n_splits + 1)

        for i in range(n_splits):
            train_end_idx = n - (i + 1) * test_size - gap_days
            test_start_idx = train_end_idx + gap_days
            test_end_idx = test_start_idx + test_size

            if train_end_idx < self.config.min_history:
                break

            train_data = data.iloc[:train_end_idx].copy()
            test_data = data.iloc[test_start_idx:test_end_idx].copy()

            label_cols = [
                c
                for c in test_data.columns
                if "future_return" in c or "target_binary" in c
            ]
            test_data = test_data.drop(columns=label_cols, errors="ignore")

            splits.append((train_data, test_data))

        return splits

    def get_feature_columns(self, data: pd.DataFrame) -> List[str]:
        """Get list of feature columns (excluding labels and price)."""
        exclude = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "date",
            "future_return",
            "target_binary",
            "returns",
            "log_returns",
        ]

        feature_cols = [c for c in data.columns if not any(e in c for e in exclude)]

        return feature_cols

    def get_X_y(
        self, data: pd.DataFrame, label_col: str = "target_binary_5d"
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Get feature matrix X and target vector y.

        Args:
            data: Feature DataFrame with labels
            label_col: Target column name

        Returns:
            Tuple of (X, y)
        """
        feature_cols = self.get_feature_columns(data)

        X = data[feature_cols].copy()
        y = data[label_col].copy()

        X = X.replace([np.inf, -np.inf], np.nan)

        return X, y

    def cache_features(self, key: str, data: pd.DataFrame) -> None:
        """Cache computed features."""
        if self.config.cache_enabled:
            self.feature_cache[key] = data.copy()
            self.feature_hash = self._compute_hash(data)

    def get_cached_features(self, key: str) -> Optional[pd.DataFrame]:
        """Retrieve cached features."""
        return self.feature_cache.get(key)

    def _compute_hash(self, data: pd.DataFrame) -> str:
        """Compute hash of feature data for versioning."""
        cols = sorted(data.columns)
        hash_input = f"{cols}_{len(data)}_{self.config.feature_version}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:8]

    def get_feature_importance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_top: int = 20,
    ) -> pd.DataFrame:
        """
        Get feature importance using correlation with target.

        Args:
            X: Feature matrix
            y: Target vector
            n_top: Number of top features to return

        Returns:
            DataFrame with feature importances
        """
        correlations = []

        for col in X.columns:
            valid_mask = X[col].notna() & y.notna()
            if valid_mask.sum() > 10:
                corr = X.loc[valid_mask, col].corr(y.loc[valid_mask])
                correlations.append({"feature": col, "correlation": corr})

        importance_df = pd.DataFrame(correlations)
        importance_df = importance_df.sort_values(
            "correlation", key=abs, ascending=False
        ).head(n_top)

        return importance_df


def create_ml_feature_pipeline(
    data: Dict[str, pd.DataFrame],
    config: Optional[FeatureConfig] = None,
) -> Tuple[pd.DataFrame, FeaturePipeline]:
    """
    Create ML-ready feature pipeline for multiple symbols.

    Args:
        data: Dictionary of symbol -> OHLCV DataFrames
        config: Feature configuration

    Returns:
        Tuple of (combined_df, pipeline)
    """
    pipeline = FeaturePipeline(config)

    all_features = []

    for symbol, df in data.items():
        features = pipeline.compute_features(df, mode=FeatureMode.TRAINING)
        features["symbol"] = symbol

        label_cols = [
            c for c in features.columns if "future_return" in c or "target_binary" in c
        ]
        features = features.dropna(subset=label_cols)

        all_features.append(features)

    combined = pd.concat(all_features, ignore_index=True)

    return combined, pipeline


__all__ = [
    "FeaturePipeline",
    "create_ml_feature_pipeline",
]
