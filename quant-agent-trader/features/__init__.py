"""
Features Module - Technical indicators and feature calculation.

Provides:
- FeatureRegistry for pluggable feature discovery
- Modular feature generators
- FeatureConfig for pipeline configuration
- FeaturePipeline for ML-ready feature computation
"""

from features.config import (
    FeatureConfig,
    FeatureMode,
    LabelConfig,
    SplitConfig,
)
from features.registry import (
    FeatureRegistry,
    FeatureMetadata,
    FeatureGenerator,
)
from features.pipeline import (
    FeaturePipeline,
    create_ml_feature_pipeline,
)
from features.indicators import TechnicalFeatures
from features.factor_models import (
    FactorExposure,
    FactorModel,
    RiskAttribution,
    FactorScreener,
)

__all__ = [
    "FeatureConfig",
    "FeatureMode",
    "LabelConfig",
    "SplitConfig",
    "FeatureRegistry",
    "FeatureMetadata",
    "FeatureGenerator",
    "FeaturePipeline",
    "create_ml_feature_pipeline",
    "TechnicalFeatures",
    "FactorExposure",
    "FactorModel",
    "RiskAttribution",
    "FactorScreener",
]
