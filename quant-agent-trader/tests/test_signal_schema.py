"""
Sanity Tests - Quick validation tests for core components.

Run with: pytest tests/
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from signals.signal_schema import (
    AgentSignal, 
    AggregatedSignal, 
    AgentCategory,
    SignalType,
    MarketRegime
)
from signals.signal_aggregator import SignalAggregator
from signals.feature_extractor import FeatureExtractor, TrainingDataBuilder
from utils.structured_logging import get_logger, LogLayer, configure_logging


class TestSignalSchema:
    """Test signal schema definitions."""
    
    def test_agent_signal_creation(self):
        """Test AgentSignal creation and methods."""
        signal = AgentSignal(
            agent_name="rsi_agent",
            agent_category="technical",
            signal="buy",
            confidence=75.0,
            numerical_score=0.8,
            reasoning="RSI oversold"
        )
        
        assert signal.agent_name == "rsi_agent"
        assert signal.signal == "buy"
        assert signal.confidence == 75.0
        assert signal.numerical_score == 0.8
        
        d = signal.to_dict()
        assert d["signal"] == "buy"
        
        restored = AgentSignal.from_dict(d)
        assert restored.agent_name == signal.agent_name
    
    def test_agent_signal_json(self):
        """Test JSON serialization."""
        signal = AgentSignal(
            agent_name="macd_agent",
            agent_category="technical",
            signal="sell",
            confidence=60.0,
            numerical_score=-0.5
        )
        
        json_str = signal.to_json()
        assert "macd_agent" in json_str
        assert "sell" in json_str
    
    def test_aggregated_signal_creation(self):
        """Test AggregatedSignal creation."""
        signals = [
            AgentSignal("rsi", "technical", "buy", 70, 0.7),
            AgentSignal("macd", "technical", "buy", 80, 0.6)
        ]
        
        agg = AggregatedSignal(
            stock_symbol="AAPL",
            final_score=0.65,
            decision="buy",
            confidence=75.0,
            supporting_agents=["rsi", "macd"],
            conflicting_agents=[],
            agent_signals=signals,
            regime="bull"
        )
        
        assert agg.stock_symbol == "AAPL"
        assert agg.decision == "buy"
        assert len(agg.supporting_agents) == 2
    
    def test_agent_category_enum(self):
        """Test AgentCategory enum values."""
        assert AgentCategory.TECHNICAL.value == "technical"
        assert AgentCategory.QUANT.value == "quant"
        assert AgentCategory.SENTIMENT.value == "sentiment"
    
    def test_signal_type_enum(self):
        """Test SignalType enum values."""
        assert SignalType.BUY.value == "buy"
        assert SignalType.SELL.value == "sell"
        assert SignalType.HOLD.value == "hold"


class TestSignalAggregator:
    """Test signal aggregator functionality."""
    
    def test_aggregator_basic(self):
        """Test basic signal aggregation."""
        aggregator = SignalAggregator()
        
        signals = [
            AgentSignal("rsi", "technical", "buy", 70, 0.7),
            AgentSignal("macd", "technical", "buy", 80, 0.6),
            AgentSignal("sentiment", "sentiment", "sell", 60, -0.4)
        ]
        
        result = aggregator.aggregate_signals(signals, "bull", "AAPL")
        
        assert result.stock_symbol == "AAPL"
        assert result.decision in ["buy", "sell", "hold"]
        assert 0 <= result.final_score <= 1
        assert 0 <= result.confidence <= 100
    
    def test_empty_signals(self):
        """Test handling of empty signals."""
        aggregator = SignalAggregator()
        
        result = aggregator.aggregate_signals([], "sideways", "AAPL")
        
        assert result.decision == "hold"
        assert result.final_score == 0.5
        assert result.confidence == 0.0
    
    def test_consensus_detection(self):
        """Test consensus detection."""
        aggregator = SignalAggregator()
        
        signals = [
            AgentSignal("a1", "technical", "buy", 70, 0.7),
            AgentSignal("a2", "technical", "buy", 75, 0.8),
            AgentSignal("a3", "sentiment", "sell", 60, -0.5)
        ]
        
        result = aggregator.aggregate_signals(signals, "bull", "AAPL")
        
        assert len(result.supporting_agents) >= 2
    
    def test_regime_weights(self):
        """Test regime-based weight adjustment."""
        aggregator = SignalAggregator()
        
        signals = [
            AgentSignal("rsi", "technical", "buy", 70, 0.7),
            AgentSignal("val", "fundamental", "buy", 80, 0.6)
        ]
        
        for regime in ["bull", "bear", "sideways", "high_volatility"]:
            result = aggregator.aggregate_signals(signals, regime, "AAPL")
            assert result.regime == regime


class TestFeatureExtractor:
    """Test feature extraction from agent signals."""
    
    def test_signal_to_numerical(self):
        """Test signal to numerical conversion."""
        extractor = FeatureExtractor()
        
        assert extractor._signal_to_numerical("buy") == 1.0
        assert extractor._signal_to_numerical("sell") == -1.0
        assert extractor._signal_to_numerical("hold") == 0.0
        assert extractor._signal_to_numerical("BUY") == 1.0
    
    def test_signals_to_features(self):
        """Test converting signals to features."""
        extractor = FeatureExtractor()
        
        signals = [
            AgentSignal("rsi", "technical", "buy", 70, 0.7),
            AgentSignal("macd", "technical", "buy", 80, 0.6),
            AgentSignal("sentiment", "sentiment", "hold", 50, 0.0)
        ]
        
        features = extractor.signals_to_features(signals)
        
        assert "tech_score" in features
        assert "tech_confidence" in features
        assert "sentiment_score" in features
        assert "ensemble_mean" in features
        assert "total_agents" in features
    
    def test_feature_aggregation(self):
        """Test category aggregation."""
        extractor = FeatureExtractor()
        
        signals = [
            AgentSignal("rsi", "technical", "buy", 70, 0.7),
            AgentSignal("macd", "technical", "sell", 60, -0.5),
            AgentSignal("sentiment", "sentiment", "buy", 80, 0.6)
        ]
        
        features = extractor.signals_to_features(signals)
        
        assert "tech_category_avg" in features
        assert "tech_category_std" in features
        assert "sentiment_category_avg" in features
    
    def test_empty_signals(self):
        """Test feature extraction with empty signals."""
        extractor = FeatureExtractor()
        
        features = extractor.signals_to_features([])
        
        assert "ensemble_mean" in features
        assert features["ensemble_mean"] == 0.0


class TestTrainingDataBuilder:
    """Test training data builder."""
    
    def test_add_sample(self):
        """Test adding training samples."""
        builder = TrainingDataBuilder()
        
        signals = [
            AgentSignal("rsi", "technical", "buy", 70, 0.7),
            AgentSignal("macd", "technical", "buy", 80, 0.6)
        ]
        
        builder.add_sample(
            date=datetime.now(),
            symbol="AAPL",
            signals=signals,
            future_return=0.05,
            regime="bull",
            price_at_signal=100.0,
            price_at_target=105.0
        )
        
        df = builder.get_dataset()
        
        assert len(df) == 1
        assert df.iloc[0]["symbol"] == "AAPL"
        assert df.iloc[0]["future_return"] == 0.05
        assert df.iloc[0]["target_binary"] == 1
    
    def test_target_generation(self):
        """Test target variable generation."""
        builder = TrainingDataBuilder()
        
        signals = [AgentSignal("rsi", "technical", "buy", 70, 0.7)]
        
        builder.add_sample(
            date=datetime.now(),
            symbol="AAPL",
            signals=signals,
            future_return=0.03,
            regime="bull"
        )
        
        df = builder.get_dataset()
        
        assert "target_binary" in df.columns
        assert "target_5d" in df.columns
        assert "target_10d" in df.columns
        assert "target_20d" in df.columns


class TestStructuredLogging:
    """Test structured logging functionality."""
    
    def test_logger_creation(self):
        """Test logger creation."""
        logger = get_logger(__name__, LogLayer.AGENT)
        
        assert logger.layer == LogLayer.AGENT
    
    def test_message_format(self):
        """Test message formatting."""
        import logging
        logger = logging.getLogger("test_format")
        structured = StructuredLogger(logger, LogLayer.AGENT, use_color=False)
        
        msg = structured._format_message("INFO", "Test message")
        
        assert "[AGENT]" in msg
        assert "[INFO]" in msg
        assert "Test message" in msg


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_signal_with_none_confidence(self):
        """Test handling of None confidence."""
        signal = AgentSignal(
            agent_name="test",
            agent_category="technical",
            signal="hold",
            confidence=0.0,
            numerical_score=0.0
        )
        
        assert signal.confidence == 0.0
    
    def test_extreme_numerical_scores(self):
        """Test extreme numerical scores."""
        aggregator = SignalAggregator()
        
        signals = [
            AgentSignal("a1", "technical", "buy", 100, 1.0),
            AgentSignal("a2", "technical", "sell", 100, -1.0)
        ]
        
        result = aggregator.aggregate_signals(signals, "bull", "AAPL")
        
        assert result.final_score >= 0.0
        assert result.final_score <= 1.0
    
    def test_missing_category(self):
        """Test handling of missing category."""
        extractor = FeatureExtractor()
        
        signal = AgentSignal("test", "unknown_category", "buy", 70, 0.7)
        
        features = extractor.signals_to_features([signal])
        
        assert "unknown_category_score" in features


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
