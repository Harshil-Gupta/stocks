"""
Signal Aggregator Tests

Tests for signal aggregation logic.
"""

import pytest
from signals.signal_aggregator import SignalAggregator, aggregate_signals
from signals.signal_schema import AgentSignal, AggregatedSignal


class TestSignalAggregator:
    """Tests for SignalAggregator class."""
    
    @pytest.fixture
    def aggregator(self):
        """Create a SignalAggregator instance."""
        return SignalAggregator()
    
    def test_default_weights(self, aggregator):
        """Test default weights sum to 1.0."""
        total = sum(aggregator.base_weights.values())
        assert abs(total - 1.0) < 0.001
    
    def test_custom_weights(self):
        """Test custom weights initialization."""
        custom_weights = {
            "technical": 0.40,
            "fundamental": 0.30,
            "sentiment": 0.10,
            "macro": 0.05,
            "market_structure": 0.10,
            "risk": 0.05,
        }
        aggregator = SignalAggregator(custom_weights=custom_weights)
        
        assert aggregator.base_weights["technical"] == 0.40
        assert aggregator.base_weights["fundamental"] == 0.30
    
    def test_invalid_weights_sum(self):
        """Test that invalid weight sums raise error."""
        invalid_weights = {
            "technical": 0.50,
            "fundamental": 0.50,
            "sentiment": 0.10,
            "macro": 0.10,
            "market_structure": 0.10,
            "risk": 0.10,
        }
        
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            SignalAggregator(custom_weights=invalid_weights)
    
    def test_missing_weight_categories(self):
        """Test that missing categories raise error."""
        invalid_weights = {
            "technical": 0.60,
            "fundamental": 0.40,
        }
        
        with pytest.raises(ValueError, match="Missing weight categories"):
            SignalAggregator(custom_weights=invalid_weights)
    
    def test_aggregate_empty_signals(self, aggregator):
        """Test aggregation with no signals."""
        result = aggregator.aggregate_signals(
            signals=[],
            regime="bull",
            stock_symbol="RELIANCE"
        )
        
        assert result.decision == "hold"
        assert result.confidence == 0.0
        assert result.final_score == 0.5
    
    def test_aggregate_buy_signals(self, aggregator):
        """Test aggregation with buy signals."""
        signals = [
            AgentSignal(
                agent_name="rsi_agent",
                agent_category="technical",
                signal="buy",
                confidence=80.0,
                numerical_score=-0.8,
            ),
            AgentSignal(
                agent_name="macd_agent",
                agent_category="technical",
                signal="buy",
                confidence=70.0,
                numerical_score=-0.6,
            ),
        ]
        
        result = aggregator.aggregate_signals(
            signals=signals,
            regime="bull",
            stock_symbol="RELIANCE"
        )
        
        assert result.decision == "buy"
        assert result.final_score >= 0.6
    
    def test_aggregate_sell_signals(self, aggregator):
        """Test aggregation with sell signals."""
        signals = [
            AgentSignal(
                agent_name="rsi_agent",
                agent_category="technical",
                signal="sell",
                confidence=80.0,
                numerical_score=0.8,
            ),
            AgentSignal(
                agent_name="macd_agent",
                agent_category="technical",
                signal="sell",
                confidence=70.0,
                numerical_score=0.6,
            ),
        ]
        
        result = aggregator.aggregate_signals(
            signals=signals,
            regime="bull",
            stock_symbol="RELIANCE"
        )
        
        assert result.decision == "sell"
        assert result.final_score <= 0.4
    
    def test_aggregate_mixed_signals(self, aggregator):
        """Test aggregation with mixed signals."""
        signals = [
            AgentSignal(
                agent_name="rsi_agent",
                agent_category="technical",
                signal="buy",
                confidence=80.0,
                numerical_score=-0.8,
            ),
            AgentSignal(
                agent_name="valuation_agent",
                agent_category="fundamental",
                signal="sell",
                confidence=70.0,
                numerical_score=0.6,
            ),
        ]
        
        result = aggregator.aggregate_signals(
            signals=signals,
            regime="bull",
            stock_symbol="RELIANCE"
        )
        
        # Result depends on weights - technical has 0.30, fundamental 0.25
        assert result.final_score >= 0.3  # Between buy and sell
        assert result.decision in ["buy", "sell", "hold"]
    
    def test_consensus_detection(self, aggregator):
        """Test consensus detection logic."""
        signals = [
            AgentSignal(
                agent_name="rsi_agent",
                agent_category="technical",
                signal="buy",
                confidence=80.0,
                numerical_score=-0.8,
            ),
            AgentSignal(
                agent_name="macd_agent",
                agent_category="technical",
                signal="buy",
                confidence=70.0,
                numerical_score=-0.6,
            ),
            AgentSignal(
                agent_name="valuation_agent",
                agent_category="fundamental",
                signal="sell",
                confidence=60.0,
                numerical_score=0.5,
            ),
        ]
        
        result = aggregator.aggregate_signals(
            signals=signals,
            regime="bull",
            stock_symbol="RELIANCE"
        )
        
        assert len(result.supporting_agents) == 2
        assert len(result.conflicting_agents) == 1
    
    def test_confidence_calculation(self, aggregator):
        """Test confidence calculation."""
        signals = [
            AgentSignal(
                agent_name="rsi_agent",
                agent_category="technical",
                signal="buy",
                confidence=90.0,
                numerical_score=-0.9,
            ),
            AgentSignal(
                agent_name="macd_agent",
                agent_category="technical",
                signal="buy",
                confidence=85.0,
                numerical_score=-0.85,
            ),
        ]
        
        result = aggregator.aggregate_signals(
            signals=signals,
            regime="bull",
            stock_symbol="RELIANCE"
        )
        
        assert result.confidence > 50.0
    
    def test_regime_based_weights_bull(self, aggregator):
        """Test regime-based weight adjustment for bull market."""
        weights = aggregator._get_regime_weights("bull")
        
        # In bull market, technical weight should be higher
        assert weights["technical"] >= aggregator.base_weights["technical"]
    
    def test_regime_based_weights_bear(self, aggregator):
        """Test regime-based weight adjustment for bear market."""
        weights = aggregator._get_regime_weights("bear")
        
        # In bear market, risk weight should be higher
        assert weights["risk"] >= aggregator.base_weights["risk"]
    
    def test_regime_based_weights_sideways(self, aggregator):
        """Test regime-based weight adjustment for sideways market."""
        weights = aggregator._get_regime_weights("sideways")
        
        assert weights is not None
    
    def test_normalize_score(self, aggregator):
        """Test score normalization."""
        # Test score -1 to 1 -> 0 to 1
        assert aggregator._normalize_score(-1.0) == 0.0
        assert aggregator._normalize_score(0.0) == 0.5
        assert aggregator._normalize_score(1.0) == 1.0
        assert aggregator._normalize_score(0.5) == 0.75
    
    def test_score_to_decision(self, aggregator):
        """Test score to decision conversion."""
        assert aggregator._score_to_decision(0.7) == "buy"
        assert aggregator._score_to_decision(0.3) == "sell"
        assert aggregator._score_to_decision(0.5) == "hold"
    
    def test_weight_breakdown(self, aggregator):
        """Test weight breakdown calculation."""
        signals = [
            AgentSignal(
                agent_name="rsi_agent",
                agent_category="technical",
                signal="buy",
                confidence=80.0,
                numerical_score=-0.8,
            ),
            AgentSignal(
                agent_name="macd_agent",
                agent_category="technical",
                signal="buy",
                confidence=70.0,
                numerical_score=-0.6,
            ),
        ]
        
        breakdown = aggregator.get_weight_breakdown(signals, "bull")
        
        assert "technical" in breakdown
        assert breakdown["technical"]["agent_count"] == 2
        assert breakdown["technical"]["weight"] > 0


class TestAggregateSignalsFunction:
    """Tests for the aggregate_signals convenience function."""
    
    def test_aggregate_signals_convenience(self):
        """Test the convenience function."""
        signals = [
            AgentSignal(
                agent_name="rsi_agent",
                agent_category="technical",
                signal="buy",
                confidence=80.0,
                numerical_score=-0.8,
            ),
        ]
        
        result = aggregate_signals(
            signals=signals,
            regime="bull",
            stock_symbol="RELIANCE"
        )
        
        assert isinstance(result, AggregatedSignal)
        assert result.stock_symbol == "RELIANCE"
    
    def test_aggregate_signals_with_custom_weights(self):
        """Test with custom weights."""
        signals = [
            AgentSignal(
                agent_name="rsi_agent",
                agent_category="technical",
                signal="buy",
                confidence=80.0,
                numerical_score=-0.8,
            ),
        ]
        
        custom_weights = {
            "technical": 1.0,
            "fundamental": 0.0,
            "sentiment": 0.0,
            "macro": 0.0,
            "market_structure": 0.0,
            "risk": 0.0,
        }
        
        result = aggregate_signals(
            signals=signals,
            regime="bull",
            stock_symbol="RELIANCE",
            custom_weights=custom_weights
        )
        
        assert result is not None
