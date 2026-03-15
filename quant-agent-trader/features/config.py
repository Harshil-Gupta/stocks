"""
Feature Configuration - Configuration classes for feature pipeline.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import yaml
from pathlib import Path


class FeatureMode(Enum):
    """Feature computation mode."""

    TRAINING = "training"
    INFERENCE = "inference"
    BACKTEST = "backtest"


@dataclass
class LabelConfig:
    """Configuration for label generation."""

    horizons: List[int] = field(default_factory=lambda: [5, 10, 20])
    binary: bool = True
    threshold: float = 0.0


@dataclass
class SplitConfig:
    """Configuration for train/test split."""

    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    gap_days: int = 20


@dataclass
class FeatureConfig:
    """
    Configuration for feature generation pipeline.

    Attributes:
        features: List of feature names to compute
        lookback_windows: Windows for lookback features
        label_config: Label generation configuration
        split_config: Train/test split configuration
        mode: Feature computation mode
        min_history: Minimum history required
        feature_version: Version string for caching
        cache_enabled: Enable feature caching
    """

    features: List[str] = field(
        default_factory=lambda: [
            "returns",
            "sma",
            "ema",
            "rsi",
            "macd",
            "bollinger_bands",
            "atr",
            "volatility",
            "momentum",
            "roc",
            "volume_indicators",
            "stochastic",
            "cci",
            "adx",
            "williams_r",
            "mfi",
            "vwap",
            "price_position",
            "ma_crossover",
        ]
    )
    lookback_windows: List[int] = field(
        default_factory=lambda: [5, 10, 20, 50, 100, 200]
    )
    label_config: LabelConfig = field(default_factory=LabelConfig)
    split_config: SplitConfig = field(default_factory=SplitConfig)
    mode: FeatureMode = FeatureMode.TRAINING
    min_history: int = 200
    feature_version: str = "1.0"
    cache_enabled: bool = True

    def __post_init__(self):
        if isinstance(self.label_config, dict):
            self.label_config = LabelConfig(**self.label_config)
        if isinstance(self.split_config, dict):
            self.split_config = SplitConfig(**self.split_config)
        if isinstance(self.mode, str):
            self.mode = FeatureMode(self.mode)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "features": self.features,
            "lookback_windows": self.lookback_windows,
            "label_config": {
                "horizons": self.label_config.horizons,
                "binary": self.label_config.binary,
                "threshold": self.label_config.threshold,
            },
            "split_config": {
                "train_ratio": self.split_config.train_ratio,
                "val_ratio": self.split_config.val_ratio,
                "test_ratio": self.split_config.test_ratio,
                "gap_days": self.split_config.gap_days,
            },
            "mode": self.mode.value,
            "min_history": self.min_history,
            "feature_version": self.feature_version,
            "cache_enabled": self.cache_enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureConfig":
        """Create from dictionary."""
        label_config = LabelConfig(**data.get("label_config", {}))
        split_config = SplitConfig(**data.get("split_config", {}))

        return cls(
            features=data.get("features", []),
            lookback_windows=data.get("lookback_windows", [5, 10, 20, 50, 100, 200]),
            label_config=label_config,
            split_config=split_config,
            mode=data.get("mode", "training"),
            min_history=data.get("min_history", 200),
            feature_version=data.get("feature_version", "1.0"),
            cache_enabled=data.get("cache_enabled", True),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> "FeatureConfig":
        """Load from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    def to_yaml(self, path: Path) -> None:
        """Save to YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)

    @classmethod
    def default_momentum(cls) -> "FeatureConfig":
        """Default config for momentum strategies."""
        return cls(
            features=[
                "returns",
                "sma",
                "ema",
                "rsi",
                "macd",
                "momentum",
                "roc",
                "stochastic",
                "cci",
            ],
            min_history=50,
        )

    @classmethod
    def default_mean_reversion(cls) -> "FeatureConfig":
        """Default config for mean reversion strategies."""
        return cls(
            features=[
                "returns",
                "bollinger_bands",
                "rsi",
                "volatility",
                "price_position",
                "mfi",
            ],
            min_history=50,
        )

    @classmethod
    def default_breakout(cls) -> "FeatureConfig":
        """Default config for breakout strategies."""
        return cls(
            features=[
                "returns",
                "sma",
                "atr",
                "volatility",
                "volume_indicators",
                "adx",
            ],
            min_history=50,
        )


__all__ = [
    "FeatureMode",
    "LabelConfig",
    "SplitConfig",
    "FeatureConfig",
]
