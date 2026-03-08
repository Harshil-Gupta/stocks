"""
MACD Agent Tests

Tests for MACD-based trading signals.
"""

import pytest
from agents.technical.macd_agent import MACDAgent


class TestMACDAgent:
    """Tests for MACDAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create a MACD agent."""
        return MACDAgent()
    
    def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent.agent_name == "macd_agent"
        assert agent.agent_category.value == "technical"
    
    def test_bullish_crossover(self, agent):
        """Test buy signal on bullish MACD crossover."""
        features = {
            "macd": 15.5,
            "macd_signal": 12.0,
            "macd_hist": 3.5,
            "close": 1550.0,
        }
        
        signal = agent.compute_signal(features)
        
        assert signal.signal == "buy"
        assert signal.confidence > 50
    
    def test_bearish_crossover(self, agent):
        """Test sell signal on bearish MACD crossover."""
        features = {
            "macd": -15.5,
            "macd_signal": -12.0,
            "macd_hist": -3.5,
            "close": 1550.0,
        }
        
        signal = agent.compute_signal(features)
        
        assert signal.signal == "sell"
        assert signal.confidence > 50
    
    def test_weak_bullish(self, agent):
        """Test signal when bullish but weak."""
        features = {
            "macd": 2.0,
            "macd_signal": 1.5,
            "macd_hist": 0.5,
            "close": 1550.0,
        }
        
        signal = agent.compute_signal(features)
        
        assert signal.signal == "hold"
    
    def test_missing_features(self, agent):
        """Test agent handles missing features."""
        features = {}
        
        signal = agent.compute_signal(features)
        
        assert signal.signal in ["buy", "sell", "hold"]
    
    def test_run_agent(self, agent):
        """Test running the agent via run() method."""
        features = {
            "macd": 15.5,
            "macd_signal": 12.0,
            "macd_hist": 3.5,
            "close": 1550.0,
        }
        
        signal = agent.run(features)
        
        assert signal.signal == "buy"
