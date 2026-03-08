"""
RSI Agent Tests

Tests for RSI-based trading signals.
"""

import pytest
from agents.technical.rsi_agent import RSIAgent


class TestRSIAgent:
    """Tests for RSIAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create an RSI agent."""
        return RSIAgent()
    
    def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent.agent_name == "rsi_agent"
        assert agent.agent_category.value == "technical"
    
    def test_oversold_signal(self, agent):
        """Test buy signal when RSI is oversold."""
        features = {
            "rsi": 25.0,
            "close": 1500.0,
            "price_position_20": 0.3,
            "atr": 25.0,
        }
        
        signal = agent.compute_signal(features)
        
        assert signal.signal == "buy"
        assert signal.confidence > 50
        assert signal.numerical_score < 0
    
    def test_overbought_signal(self, agent):
        """Test sell signal when RSI is overbought."""
        features = {
            "rsi": 78.0,
            "close": 1550.0,
            "price_position_20": 0.8,
            "atr": 25.0,
        }
        
        signal = agent.compute_signal(features)
        
        assert signal.signal == "sell"
        assert signal.confidence > 50
        assert signal.numerical_score > 0
    
    def test_neutral_zone_buy(self, agent):
        """Test buy signal in neutral zone leaning bearish."""
        features = {
            "rsi": 42.0,
            "close": 1500.0,
            "price_position_20": 0.5,
            "atr": 25.0,
        }
        
        signal = agent.compute_signal(features)
        
        assert signal.signal == "buy"
    
    def test_neutral_zone_hold(self, agent):
        """Test hold signal in neutral zone."""
        features = {
            "rsi": 55.0,
            "close": 1500.0,
            "price_position_20": 0.5,
            "atr": 25.0,
        }
        
        signal = agent.compute_signal(features)
        
        assert signal.signal == "hold"
    
    def test_elevated_momentum(self, agent):
        """Test hold signal for elevated momentum."""
        features = {
            "rsi": 65.0,
            "close": 1500.0,
            "price_position_20": 0.7,
            "atr": 25.0,
        }
        
        signal = agent.compute_signal(features)
        
        assert signal.signal == "hold"
        assert signal.confidence > 50
    
    def test_depressed_momentum(self, agent):
        """Test hold signal for depressed momentum."""
        features = {
            "rsi": 38.0,
            "close": 1500.0,
            "price_position_20": 0.3,
            "atr": 25.0,
        }
        
        signal = agent.compute_signal(features)
        
        assert signal.signal == "hold"
    
    def test_rsi_boundary_oversold(self, agent):
        """Test RSI at oversold boundary."""
        features = {
            "rsi": 30.0,
            "close": 1500.0,
            "price_position_20": 0.2,
            "atr": 25.0,
        }
        
        signal = agent.compute_signal(features)
        
        # At exactly 30, still considered oversold
        assert signal.signal == "buy"
    
    def test_rsi_boundary_overbought(self, agent):
        """Test RSI at overbought boundary."""
        features = {
            "rsi": 70.0,
            "close": 1500.0,
            "price_position_20": 0.8,
            "atr": 25.0,
        }
        
        signal = agent.compute_signal(features)
        
        # At exactly 70, still considered overbought
        assert signal.signal == "sell"
    
    def test_missing_features(self, agent):
        """Test agent handles missing features gracefully."""
        features = {}
        
        signal = agent.compute_signal(features)
        
        # Should still return a valid signal with default values
        assert signal.signal in ["buy", "sell", "hold"]
        assert isinstance(signal.confidence, float)
    
    def test_supporting_data_oversold(self, agent):
        """Test supporting data is included in oversold signal."""
        features = {
            "rsi": 25.0,
            "close": 1500.0,
            "price_position_20": 0.3,
            "atr": 25.0,
        }
        
        signal = agent.compute_signal(features)
        
        assert "rsi_value" in signal.supporting_data
        assert signal.supporting_data["rsi_condition"] == "oversold"
        assert signal.supporting_data["threshold_oversold"] == 30.0
    
    def test_supporting_data_overbought(self, agent):
        """Test supporting data is included in overbought signal."""
        features = {
            "rsi": 75.0,
            "close": 1500.0,
            "price_position_20": 0.8,
            "atr": 25.0,
        }
        
        signal = agent.compute_signal(features)
        
        assert "rsi_value" in signal.supporting_data
        assert signal.supporting_data["rsi_condition"] == "overbought"
        assert signal.supporting_data["threshold_overbought"] == 70.0
    
    def test_confidence_bounds(self, agent):
        """Test confidence is within valid bounds."""
        features_oversold = {"rsi": 10.0, "close": 1500.0, "price_position_20": 0.1, "atr": 25.0}
        features_overbought = {"rsi": 90.0, "close": 1500.0, "price_position_20": 0.9, "atr": 25.0}
        
        signal_oversold = agent.compute_signal(features_oversold)
        signal_overbought = agent.compute_signal(features_overbought)
        
        assert 0 <= signal_oversold.confidence <= 100
        assert 0 <= signal_overbought.confidence <= 100
    
    def test_numerical_score_range(self, agent):
        """Test numerical score is in valid range."""
        features_buy = {"rsi": 20.0, "close": 1500.0, "price_position_20": 0.2, "atr": 25.0}
        features_sell = {"rsi": 80.0, "close": 1500.0, "price_position_20": 0.8, "atr": 25.0}
        
        signal_buy = agent.compute_signal(features_buy)
        signal_sell = agent.compute_signal(features_sell)
        
        assert -1 <= signal_buy.numerical_score <= 1
        assert -1 <= signal_sell.numerical_score <= 1
    
    def test_custom_thresholds(self, agent):
        """Test custom threshold setting."""
        agent.set_thresholds(overbought=80.0, oversold=20.0)
        
        assert agent._overbought_threshold == 80.0
        assert agent._oversold_threshold == 20.0
    
    def test_run_agent(self, agent):
        """Test running the agent via run() method."""
        features = {"rsi": 25.0, "close": 1500.0, "price_position_20": 0.3, "atr": 25.0}
        
        signal = agent.run(features)
        
        assert signal.signal == "buy"
    
    def test_agent_metadata(self, agent):
        """Test agent metadata is set correctly."""
        assert agent.metadata.version == "1.0.0"
        assert "rsi" in agent.metadata.tags
        assert "oscillator" in agent.metadata.tags
