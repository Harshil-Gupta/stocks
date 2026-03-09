"""
Meta Model Aggregator - ML-based signal aggregation.

This module replaces the rule-based SignalAggregator with an ML meta-model
that learns from agent outputs to make better trading decisions.

Pipeline:
    agents → agent_scores → ML model → final signal
    
Supports:
    - LightGBM, XGBoost, Logistic Regression
    - Regime-aware models (bull, bear, sideways, high_volatility)
    - Model persistence and loading
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np
import pickle
import logging
import os

from signals.signal_schema import AgentSignal, AggregatedSignal
from signals.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for meta model."""
    model_type: str = "lightgbm"
    buy_threshold: float = 0.6
    sell_threshold: float = 0.4
    n_estimators: int = 100
    max_depth: int = 5
    learning_rate: float = 0.1
    random_state: int = 42


class MetaModelAggregator:
    """
    ML-based signal aggregator using meta-learning.
    
    Replaces rule-based aggregation with a trained ML model that
    learns optimal combinations of agent signals.
    """
    
    REGIMES = ["bull", "bear", "sideways", "high_volatility"]
    
    def __init__(
        self,
        config: Optional[ModelConfig] = None,
        model_path: Optional[str] = None
    ):
        """
        Initialize MetaModelAggregator.
        
        Args:
            config: Model configuration
            model_path: Path to saved model file
        """
        self.config = config or ModelConfig()
        self.feature_extractor = FeatureExtractor()
        
        self.models: Dict[str, Any] = {}
        self.is_trained = False
        self.feature_names: List[str] = []
        
        if model_path and os.path.exists(model_path):
            self.load_models(model_path)
    
    def train(
        self,
        dataset: pd.DataFrame,
        target_column: str = "target_binary",
        test_size: float = 0.2,
        train_regime_models: bool = True
    ) -> Dict[str, float]:
        """
        Train meta model on dataset.
        
        Args:
            dataset: Training data with agent features and targets
            target_column: Name of target column
            test_size: Fraction for test split
            train_regime_models: Whether to train separate models per regime
            
        Returns:
            Dictionary of model performance metrics
        """
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, classification_report
        
        feature_cols = [c for c in dataset.columns if c not in [
            "date", "symbol", "future_return", "target_binary", 
            "target_5d", "target_10d", "target_20d", "regime",
            "price_at_signal", "price_at_target"
        ]]
        
        self.feature_names = feature_cols
        
        X = dataset[feature_cols].fillna(0)
        y = dataset[target_column]
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.config.random_state
        )
        
        if self.config.model_type == "lightgbm":
            self._train_lightgbm(X_train, X_test, y_train, y_test)
        elif self.config.model_type == "xgboost":
            self._train_xgboost(X_train, X_test, y_train, y_test)
        else:
            self._train_sklearn(X_train, X_test, y_train, y_test)
        
        y_pred = self.models["default"].predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"Meta model training complete. Test accuracy: {accuracy:.4f}")
        
        if train_regime_models and "regime" in dataset.columns:
            self._train_regime_models(dataset, target_column)
        
        self.is_trained = True
        
        return {"accuracy": accuracy, "test_size": len(y_test)}
    
    def _train_lightgbm(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series
    ) -> None:
        """Train LightGBM model."""
        try:
            import lightgbm as lgb
            
            model = lgb.LGBMClassifier(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                learning_rate=self.config.learning_rate,
                random_state=self.config.random_state,
                verbose=-1
            )
            
            model.fit(X_train, y_train)
            self.models["default"] = model
            
            logger.info("LightGBM model trained successfully")
            
        except ImportError:
            logger.warning("LightGBM not installed, falling back to sklearn")
            self._train_sklearn(X_train, X_test, y_train, y_test)
    
    def _train_xgboost(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series
    ) -> None:
        """Train XGBoost model."""
        try:
            import xgboost as xgb
            
            model = xgb.XGBClassifier(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                learning_rate=self.config.learning_rate,
                random_state=self.config.random_state,
                use_label_encoder=False,
                eval_metric='logloss'
            )
            
            model.fit(X_train, y_train)
            self.models["default"] = model
            
            logger.info("XGBoost model trained successfully")
            
        except ImportError:
            logger.warning("XGBoost not installed, falling back to sklearn")
            self._train_sklearn(X_train, X_test, y_train, y_test)
    
    def _train_sklearn(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series
    ) -> None:
        """Train sklearn model (Logistic Regression or Random Forest)."""
        from sklearn.linear_model import LogisticRegression
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        if self.config.model_type == "logistic":
            model = LogisticRegression(
                random_state=self.config.random_state,
                max_iter=1000
            )
        else:
            model = RandomForestClassifier(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                random_state=self.config.random_state
            )
        
        model.fit(X_train_scaled, y_train)
        
        self.models["default"] = model
        self.models["scaler"] = self.scaler
        
        logger.info(f"Sklearn {self.config.model_type} model trained successfully")
    
    def _train_regime_models(
        self,
        dataset: pd.DataFrame,
        target_column: str
    ) -> None:
        """Train separate models per regime."""
        from sklearn.model_selection import train_test_split
        
        for regime in self.REGIMES:
            regime_data = dataset[dataset["regime"] == regime]
            
            if len(regime_data) < 50:
                logger.warning(f"Not enough data to train regime model for {regime}")
                continue
            
            X = regime_data[self.feature_names].fillna(0)
            y = regime_data[target_column]
            
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=self.config.random_state
            )
            
            if self.config.model_type == "lightgbm":
                self._train_lightgbm_regime(X_train, X_test, y_train, y_test, regime)
            else:
                self._train_sklearn_regime(X_train, X_test, y_train, y_test, regime)
    
    def _train_lightgbm_regime(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
        regime: str
    ) -> None:
        """Train LightGBM for specific regime."""
        try:
            import lightgbm as lgb
            
            model = lgb.LGBMClassifier(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                learning_rate=self.config.learning_rate,
                random_state=self.config.random_state,
                verbose=-1
            )
            
            model.fit(X_train, y_train)
            self.models[regime] = model
            
            logger.info(f"Regime model for {regime} trained successfully")
            
        except ImportError:
            self._train_sklearn_regime(X_train, X_test, y_train, y_test, regime)
    
    def _train_sklearn_regime(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
        regime: str
    ) -> None:
        """Train sklearn model for specific regime."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        model = RandomForestClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            random_state=self.config.random_state
        )
        
        model.fit(X_train_scaled, y_train)
        
        self.models[regime] = model
        self.models[f"{regime}_scaler"] = scaler
    
    def aggregate_signals(
        self,
        signals: List[AgentSignal],
        regime: str = "sideways",
        stock_symbol: str = "UNKNOWN"
    ) -> AggregatedSignal:
        """
        Aggregate signals using ML model.
        
        Args:
            signals: List of agent signals
            regime: Current market regime
            stock_symbol: Stock symbol
            
        Returns:
            AggregatedSignal with ML-based decision
        """
        if not self.is_trained:
            logger.warning("Model not trained, using fallback to rule-based")
            return self._fallback_aggregation(signals, regime, stock_symbol)
        
        if not signals:
            return self._create_empty_signal(stock_symbol, regime)
        
        features = self.feature_extractor.signals_to_features(signals)
        
        feature_vector = self._prepare_feature_vector(features)
        
        model = self.models.get(regime, self.models.get("default"))
        
        if model is None:
            model = self.models.get("default")
        
        if model is None:
            return self._fallback_aggregation(signals, regime, stock_symbol)
        
        probability = self._predict_proba(model, feature_vector)
        
        decision = self._probability_to_decision(probability)
        
        confidence = self._calculate_ml_confidence(probability)
        
        supporting = [s.agent_name for s in signals if s.signal.lower() == decision]
        conflicting = [s.agent_name for s in signals if s.signal.lower() != decision]
        
        return AggregatedSignal(
            stock_symbol=stock_symbol,
            final_score=probability,
            decision=decision,
            confidence=confidence,
            supporting_agents=supporting,
            conflicting_agents=conflicting,
            agent_signals=signals,
            regime=regime,
            timestamp=datetime.now()
        )
    
    def _prepare_feature_vector(self, features: Dict[str, Any]) -> pd.DataFrame:
        """Prepare feature vector for prediction."""
        vector = {}
        
        for fname in self.feature_names:
            vector[fname] = features.get(fname, 0.0)
        
        return pd.DataFrame([vector])
    
    def _predict_proba(self, model: Any, features: pd.DataFrame) -> float:
        """Get probability prediction."""
        if hasattr(model, "predict_proba"):
            if "scaler" in self.models:
                features_scaled = self.models["scaler"].transform(features)
                proba = model.predict_proba(features_scaled)[0][1]
            else:
                proba = model.predict_proba(features)[0][1]
        else:
            proba = model.predict(features)[0]
        
        return float(proba)
    
    def _probability_to_decision(self, probability: float) -> str:
        """Convert probability to trading decision."""
        if probability >= self.config.buy_threshold:
            return "buy"
        elif probability <= self.config.sell_threshold:
            return "sell"
        else:
            return "hold"
    
    def _calculate_ml_confidence(self, probability: float) -> float:
        """Calculate confidence based on prediction probability."""
        distance_from_neutral = abs(probability - 0.5)
        confidence = distance_from_neutral * 2 * 100
        return min(100.0, max(0.0, confidence))
    
    def _fallback_aggregation(
        self,
        signals: List[AgentSignal],
        regime: str,
        stock_symbol: str
    ) -> AggregatedSignal:
        """Fallback to simple averaging when model not available."""
        if not signals:
            return self._create_empty_signal(stock_symbol, regime)
        
        numerical_scores = [s.numerical_score for s in signals]
        avg_score = np.mean(numerical_scores)
        
        final_score = (avg_score + 1) / 2
        
        if final_score >= 0.6:
            decision = "buy"
        elif final_score <= 0.4:
            decision = "sell"
        else:
            decision = "hold"
        
        confidence = np.mean([s.confidence for s in signals])
        
        return AggregatedSignal(
            stock_symbol=stock_symbol,
            final_score=final_score,
            decision=decision,
            confidence=confidence,
            supporting_agents=[s.agent_name for s in signals],
            conflicting_agents=[],
            agent_signals=signals,
            regime=regime,
            timestamp=datetime.now()
        )
    
    def _create_empty_signal(
        self,
        stock_symbol: str,
        regime: str
    ) -> AggregatedSignal:
        """Create empty aggregated signal."""
        return AggregatedSignal(
            stock_symbol=stock_symbol,
            final_score=0.5,
            decision="hold",
            confidence=0.0,
            supporting_agents=[],
            conflicting_agents=[],
            agent_signals=[],
            regime=regime,
            timestamp=datetime.now()
        )
    
    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """Get feature importance from trained model."""
        if "default" not in self.models:
            return None
        
        model = self.models["default"]
        
        if hasattr(model, "feature_importances_"):
            importance = pd.DataFrame({
                "feature": self.feature_names,
                "importance": model.feature_importances_
            }).sort_values("importance", ascending=False)
            
            return importance
        
        return None
    
    def save_models(self, path: str) -> None:
        """Save trained models to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "wb") as f:
            pickle.dump({
                "models": self.models,
                "config": self.config,
                "feature_names": self.feature_names,
                "is_trained": self.is_trained
            }, f)
        
        logger.info(f"Models saved to {path}")
    
    def load_models(self, path: str) -> None:
        """Load trained models from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        
        self.models = data["models"]
        self.config = data["config"]
        self.feature_names = data["feature_names"]
        self.is_trained = data["is_trained"]
        
        logger.info(f"Models loaded from {path}")


class HybridAggregator:
    """
    Hybrid aggregator combining rule-based and ML-based aggregation.
    
    Uses ML when model is trained, falls back to rules otherwise.
    Blends both approaches when both are available.
    """
    
    def __init__(
        self,
        ml_aggregator: Optional[MetaModelAggregator] = None,
        rule_aggregator: Optional[Any] = None,
        ml_weight: float = 0.7
    ):
        """
        Initialize hybrid aggregator.
        
        Args:
            ml_aggregator: ML-based aggregator
            rule_aggregator: Rule-based aggregator
            ml_weight: Weight for ML predictions (1 - weight for rules)
        """
        self.ml_aggregator = ml_aggregator
        self.rule_aggregator = rule_aggregator
        self.ml_weight = ml_weight
    
    def aggregate_signals(
        self,
        signals: List[AgentSignal],
        regime: str = "sideways",
        stock_symbol: str = "UNKNOWN"
    ) -> AggregatedSignal:
        """Aggregate signals using hybrid approach."""
        ml_signal = None
        rule_signal = None
        
        if self.ml_aggregator and self.ml_aggregator.is_trained:
            ml_signal = self.ml_aggregator.aggregate_signals(
                signals, regime, stock_symbol
            )
        
        if self.rule_aggregator:
            rule_signal = self.rule_aggregator.aggregate_signals(
                signals, regime, stock_symbol
            )
        
        if ml_signal is None and rule_signal is None:
            return AggregatedSignal(
                stock_symbol=stock_symbol,
                final_score=0.5,
                decision="hold",
                confidence=0.0,
                supporting_agents=[],
                conflicting_agents=[],
                agent_signals=signals,
                regime=regime,
                timestamp=datetime.now()
            )
        
        if ml_signal is None:
            return rule_signal
        
        if rule_signal is None:
            return ml_signal
        
        final_score = (
            ml_signal.final_score * self.ml_weight +
            rule_signal.final_score * (1 - self.ml_weight)
        )
        
        if final_score >= 0.6:
            decision = "buy"
        elif final_score <= 0.4:
            decision = "sell"
        else:
            decision = "hold"
        
        confidence = (
            ml_signal.confidence * self.ml_weight +
            rule_signal.confidence * (1 - self.ml_weight)
        )
        
        return AggregatedSignal(
            stock_symbol=stock_symbol,
            final_score=final_score,
            decision=decision,
            confidence=confidence,
            supporting_agents=list(set(ml_signal.supporting_agents + rule_signal.supporting_agents)),
            conflicting_agents=list(set(ml_signal.conflicting_agents + rule_signal.conflicting_agents)),
            agent_signals=signals,
            regime=regime,
            timestamp=datetime.now()
        )
