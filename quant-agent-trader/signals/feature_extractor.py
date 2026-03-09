"""
Feature Extractor - Transforms agent outputs into features for ML meta model.

This module converts agent signals into numerical feature vectors that can be
used to train a meta-learning model.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
import logging

from signals.signal_schema import AgentSignal, AgentCategory

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """
    Transforms agent outputs into feature vectors for ML models.
    
    Maps categorical agent signals to numerical features:
    - BUY -> +1
    - SELL -> -1
    - HOLD -> 0
    
    Generates features like:
    - rsi_score, macd_score, momentum_score
    - mean_reversion_score, stat_arb_score
    - sentiment_score, macro_score
    """
    
    CATEGORY_TO_FEATURE_PREFIX = {
        "technical": "tech",
        "fundamental": "fund",
        "sentiment": "sentiment",
        "macro": "macro",
        "market_structure": "mkt_struct",
        "risk": "risk",
        "quant": "quant",
        "meta": "meta"
    }
    
    def __init__(self):
        self.feature_names: List[str] = []
    
    def signals_to_features(
        self, 
        signals: List[AgentSignal],
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Convert agent signals to feature dictionary.
        
        Args:
            signals: List of AgentSignal objects
            include_metadata: Include metadata like date, symbol
            
        Returns:
            Dictionary of feature_name -> value
        """
        features = {}
        
        for signal in signals:
            feature_prefix = self.CATEGORY_TO_FEATURE_PREFIX.get(
                signal.agent_category, 
                signal.agent_category
            )
            
            numerical = self._signal_to_numerical(signal.signal)
            
            features[f"{feature_prefix}_score"] = numerical
            features[f"{feature_prefix}_confidence"] = signal.confidence / 100.0
            features[f"{feature_prefix}_numerical"] = signal.numerical_score
            
            weighted = numerical * (signal.confidence / 100.0)
            features[f"{feature_prefix}_weighted"] = weighted
        
        features.update(self._aggregate_by_category(signals))
        features.update(self._compute_ensemble_stats(signals))
        
        return features
    
    def _signal_to_numerical(self, signal: str) -> float:
        """Convert signal string to numerical value."""
        signal_lower = signal.lower()
        if signal_lower == "buy":
            return 1.0
        elif signal_lower == "sell":
            return -1.0
        else:
            return 0.0
    
    def _aggregate_by_category(self, signals: List[AgentSignal]) -> Dict[str, float]:
        """Compute aggregate stats per category."""
        category_scores = {}
        category_confidences = {}
        
        for signal in signals:
            cat = signal.agent_category
            if cat not in category_scores:
                category_scores[cat] = []
                category_confidences[cat] = []
            
            category_scores[cat].append(signal.numerical_score)
            category_confidences[cat].append(signal.confidence)
        
        aggregates = {}
        for cat, scores in category_scores.items():
            prefix = self.CATEGORY_TO_FEATURE_PREFIX.get(cat, cat)
            aggregates[f"{prefix}_category_avg"] = np.mean(scores)
            aggregates[f"{prefix}_category_std"] = np.std(scores) if len(scores) > 1 else 0.0
            aggregates[f"{prefix}_category_count"] = len(scores)
        
        return aggregates
    
    def _compute_ensemble_stats(self, signals: List[AgentSignal]) -> Dict[str, float]:
        """Compute ensemble-level statistics."""
        if not signals:
            return {}
        
        numerical_scores = [s.numerical_score for s in signals]
        confidences = [s.confidence for s in signals]
        
        return {
            "ensemble_mean": np.mean(numerical_scores),
            "ensemble_std": np.std(numerical_scores),
            "ensemble_min": np.min(numerical_scores),
            "ensemble_max": np.max(numerical_scores),
            "ensemble_range": np.max(numerical_scores) - np.min(numerical_scores),
            "avg_confidence": np.mean(confidences),
            "max_confidence": np.max(confidences),
            "min_confidence": np.min(confidences),
            "signal_buy_count": sum(1 for s in signals if s.signal.lower() == "buy"),
            "signal_sell_count": sum(1 for s in signals if s.signal.lower() == "sell"),
            "signal_hold_count": sum(1 for s in signals if s.signal.lower() == "hold"),
            "total_agents": len(signals)
        }
    
    def get_feature_names(self, signals: List[AgentSignal]) -> List[str]:
        """Get list of feature names that would be generated."""
        features = self.signals_to_features(signals, include_metadata=False)
        return sorted(features.keys())


class TrainingDataBuilder:
    """
    Builds training datasets from backtest runs.
    
    Captures:
    - Agent outputs as features
    - Future returns as targets
    
    Stores in parquet format for ML training.
    """
    
    def __init__(self, output_dir: str = "data/training"):
        self.output_dir = output_dir
        self.feature_extractor = FeatureExtractor()
        self.training_rows: List[Dict] = []
    
    def add_sample(
        self,
        date: datetime,
        symbol: str,
        signals: List[AgentSignal],
        future_return: float,
        regime: str = "unknown",
        price_at_signal: float = 0.0,
        price_at_target: float = 0.0
    ) -> None:
        """
        Add a training sample.
        
        Args:
            date: Date when signal was generated
            symbol: Stock symbol
            signals: Agent signals at this point
            future_return: Future return (target variable)
            regime: Market regime at signal time
            price_at_signal: Price when signal was generated
            price_at_target: Price at target horizon
        """
        features = self.feature_extractor.signals_to_features(signals)
        
        features["date"] = date
        features["symbol"] = symbol
        features["future_return"] = future_return
        features["regime"] = regime
        features["price_at_signal"] = price_at_signal
        features["price_at_target"] = price_at_target
        
        features["target_binary"] = 1 if future_return > 0 else 0
        
        features["target_5d"] = 1 if future_return > 0 else 0
        features["target_10d"] = 1 if future_return > 0.02 else 0
        features["target_20d"] = 1 if future_return > 0.05 else 0
        
        self.training_rows.append(features)
    
    def compute_future_return(
        self,
        data: pd.DataFrame,
        current_date: datetime,
        horizon: int = 5
    ) -> Optional[float]:
        """
        Compute future return over horizon.
        
        Args:
            data: Price data
            current_date: Current date
            horizon: Days ahead to compute return
            
        Returns:
            Future return as percentage, or None if not available
        """
        if current_date not in data.index:
            return None
        
        current_idx = data.index.get_loc(current_date)
        
        if current_idx + horizon >= len(data):
            return None
        
        current_price = data.iloc[current_idx]['close']
        future_price = data.iloc[current_idx + horizon]['close']
        
        return (future_price - current_price) / current_price
    
    def save_dataset(self, filename: str = "agent_dataset.parquet") -> str:
        """
        Save training dataset to parquet.
        
        Args:
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        if not self.training_rows:
            logger.warning("No training samples to save")
            return ""
        
        df = pd.DataFrame(self.training_rows)
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        filepath = os.path.join(self.output_dir, filename)
        df.to_parquet(filepath, index=False)
        
        logger.info(f"Saved {len(df)} samples to {filepath}")
        
        return filepath
    
    def get_dataset(self) -> pd.DataFrame:
        """Get training dataset as DataFrame."""
        return pd.DataFrame(self.training_rows)
    
    def clear(self) -> None:
        """Clear all stored samples."""
        self.training_rows = []


import os
