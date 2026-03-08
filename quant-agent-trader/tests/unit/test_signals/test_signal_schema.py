"""
Signal Schema Tests

Tests for signal data structures and serialization.
"""

import pytest
from datetime import datetime
from signals.signal_schema import (
    AgentSignal,
    AggregatedSignal,
    PortfolioDecision,
    TradeResult,
    MarketRegime,
    SignalType,
    AgentCategory,
)


class TestAgentSignal:
    """Tests for AgentSignal dataclass."""
    
    def test_create_signal(self):
        """Test creating an AgentSignal."""
        signal = AgentSignal(
            agent_name="test_agent",
            agent_category="technical",
            signal="buy",
            confidence=75.0,
            numerical_score=0.5,
            reasoning="Test reasoning",
            supporting_data={"key": "value"},
        )
        
        assert signal.agent_name == "test_agent"
        assert signal.agent_category == "technical"
        assert signal.signal == "buy"
        assert signal.confidence == 75.0
        assert signal.numerical_score == 0.5
    
    def test_signal_defaults(self):
        """Test default values."""
        signal = AgentSignal(
            agent_name="test_agent",
            agent_category="technical",
            signal="hold",
            confidence=50.0,
        )
        
        assert signal.numerical_score == 0.0
        assert signal.reasoning == ""
        assert signal.supporting_data == {}
        assert isinstance(signal.timestamp, datetime)
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        signal = AgentSignal(
            agent_name="test_agent",
            agent_category="technical",
            signal="buy",
            confidence=75.0,
            numerical_score=0.5,
            reasoning="Test reasoning",
        )
        
        result = signal.to_dict()
        
        assert isinstance(result, dict)
        assert result["agent_name"] == "test_agent"
        assert result["signal"] == "buy"
        assert result["confidence"] == 75.0
        assert "timestamp" in result
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "agent_name": "test_agent",
            "agent_category": "technical",
            "signal": "sell",
            "confidence": 80.0,
            "numerical_score": 0.8,
            "reasoning": "Test reasoning",
            "supporting_data": {},
            "timestamp": "2024-01-01T00:00:00",
        }
        
        signal = AgentSignal.from_dict(data)
        
        assert signal.agent_name == "test_agent"
        assert signal.signal == "sell"
        assert signal.confidence == 80.0
    
    def test_to_json(self):
        """Test serialization to JSON."""
        signal = AgentSignal(
            agent_name="test_agent",
            agent_category="technical",
            signal="hold",
            confidence=50.0,
        )
        
        json_str = signal.to_json()
        
        assert isinstance(json_str, str)
        assert "test_agent" in json_str
        assert "hold" in json_str
    
    def test_signal_type_validation(self):
        """Test that signal accepts valid signal types."""
        for signal_type in ["buy", "sell", "hold"]:
            signal = AgentSignal(
                agent_name="test",
                agent_category="technical",
                signal=signal_type,
                confidence=50.0,
            )
            assert signal.signal == signal_type


class TestAggregatedSignal:
    """Tests for AggregatedSignal dataclass."""
    
    def test_create_aggregated_signal(self):
        """Test creating an AggregatedSignal."""
        signal = AgentSignal(
            agent_name="test",
            agent_category="technical",
            signal="buy",
            confidence=70.0,
            numerical_score=0.5,
        )
        
        aggregated = AggregatedSignal(
            stock_symbol="RELIANCE",
            final_score=0.7,
            decision="buy",
            confidence=75.0,
            supporting_agents=["rsi_agent", "macd_agent"],
            conflicting_agents=["valuation_agent"],
            agent_signals=[signal],
            regime="bull",
        )
        
        assert aggregated.stock_symbol == "RELIANCE"
        assert aggregated.final_score == 0.7
        assert aggregated.decision == "buy"
        assert len(aggregated.supporting_agents) == 2
        assert len(aggregated.conflicting_agents) == 1
    
    def test_aggregated_to_dict(self):
        """Test AggregatedSignal serialization."""
        signal = AgentSignal(
            agent_name="test",
            agent_category="technical",
            signal="buy",
            confidence=70.0,
            numerical_score=0.5,
        )
        
        aggregated = AggregatedSignal(
            stock_symbol="RELIANCE",
            final_score=0.7,
            decision="buy",
            confidence=75.0,
            supporting_agents=["rsi_agent"],
            conflicting_agents=[],
            agent_signals=[signal],
        )
        
        result = aggregated.to_dict()
        
        assert isinstance(result, dict)
        assert result["stock_symbol"] == "RELIANCE"
        assert result["decision"] == "buy"
        assert "signal_breakdown" in result
    
    def test_decision_bounds(self):
        """Test decision based on score bounds."""
        # Test buy decision (score >= 0.6)
        assert AggregatedSignal(
            stock_symbol="TEST",
            final_score=0.7,
            decision="buy",
            confidence=50.0,
            supporting_agents=[],
            conflicting_agents=[],
            agent_signals=[],
        ).decision == "buy"
        
        # Test sell decision (score <= 0.4)
        assert AggregatedSignal(
            stock_symbol="TEST",
            final_score=0.3,
            decision="sell",
            confidence=50.0,
            supporting_agents=[],
            conflicting_agents=[],
            agent_signals=[],
        ).decision == "sell"
        
        # Test hold decision (0.4 < score < 0.6)
        assert AggregatedSignal(
            stock_symbol="TEST",
            final_score=0.5,
            decision="hold",
            confidence=50.0,
            supporting_agents=[],
            conflicting_agents=[],
            agent_signals=[],
        ).decision == "hold"


class TestPortfolioDecision:
    """Tests for PortfolioDecision dataclass."""
    
    def test_create_portfolio_decision(self):
        """Test creating a PortfolioDecision."""
        decision = PortfolioDecision(
            stock_symbol="RELIANCE",
            decision="buy",
            position_size=0.1,
            confidence=75.0,
            risk_level="medium",
            stop_loss=2800.0,
            take_profit=3100.0,
            reasoning="Test reasoning",
        )
        
        assert decision.stock_symbol == "RELIANCE"
        assert decision.decision == "buy"
        assert decision.position_size == 0.1
        assert decision.risk_level == "medium"
    
    def test_portfolio_decision_defaults(self):
        """Test PortfolioDecision default values."""
        decision = PortfolioDecision(
            stock_symbol="RELIANCE",
            decision="hold",
            position_size=0.0,
            confidence=0.0,
            risk_level="low",
        )
        
        assert decision.stop_loss is None
        assert decision.take_profit is None
        assert decision.reasoning == ""
        assert isinstance(decision.timestamp, datetime)
    
    def test_portfolio_decision_to_dict(self):
        """Test PortfolioDecision serialization."""
        decision = PortfolioDecision(
            stock_symbol="RELIANCE",
            decision="buy",
            position_size=0.1,
            confidence=75.0,
            risk_level="medium",
        )
        
        result = decision.to_dict()
        
        assert isinstance(result, dict)
        assert result["stock_symbol"] == "RELIANCE"
        assert result["position_size"] == 0.1


class TestTradeResult:
    """Tests for TradeResult dataclass."""
    
    def test_create_trade_result(self):
        """Test creating a TradeResult."""
        result = TradeResult(
            stock_symbol="RELIANCE",
            entry_price=2900.0,
            exit_price=2950.0,
            position_size=100,
            pnl=5000.0,
            pnl_percent=1.72,
            holding_period=5,
            decision="closed",
        )
        
        assert result.stock_symbol == "RELIANCE"
        assert result.entry_price == 2900.0
        assert result.pnl == 5000.0
        assert result.holding_period == 5
    
    def test_trade_result_to_dict(self):
        """Test TradeResult serialization."""
        result = TradeResult(
            stock_symbol="RELIANCE",
            entry_price=2900.0,
            exit_price=2950.0,
            position_size=100,
            pnl=5000.0,
            pnl_percent=1.72,
            holding_period=5,
            decision="closed",
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["pnl"] == 5000.0
        assert result_dict["holding_period"] == 5


class TestMarketRegime:
    """Tests for MarketRegime dataclass."""
    
    def test_create_market_regime(self):
        """Test creating a MarketRegime."""
        regime = MarketRegime(
            regime_type="bull",
            volatility=0.15,
            trend_strength=0.75,
            liquidity_score=0.8,
            confidence=85.0,
        )
        
        assert regime.regime_type == "bull"
        assert regime.volatility == 0.15
        assert regime.confidence == 85.0
    
    def test_market_regime_types(self):
        """Test valid regime types."""
        for regime_type in ["bull", "bear", "sideways", "high_volatility"]:
            regime = MarketRegime(
                regime_type=regime_type,
                volatility=0.15,
                trend_strength=0.5,
                liquidity_score=0.5,
                confidence=50.0,
            )
            assert regime.regime_type == regime_type
    
    def test_market_regime_to_dict(self):
        """Test MarketRegime serialization."""
        regime = MarketRegime(
            regime_type="bull",
            volatility=0.15,
            trend_strength=0.75,
            liquidity_score=0.8,
            confidence=85.0,
        )
        
        result = regime.to_dict()
        
        assert isinstance(result, dict)
        assert result["regime_type"] == "bull"
        assert "timestamp" in result


class TestEnums:
    """Tests for signal enums."""
    
    def test_signal_type_enum(self):
        """Test SignalType enum values."""
        assert SignalType.BUY.value == "buy"
        assert SignalType.SELL.value == "sell"
        assert SignalType.HOLD.value == "hold"
    
    def test_agent_category_enum(self):
        """Test AgentCategory enum values."""
        assert AgentCategory.TECHNICAL.value == "technical"
        assert AgentCategory.FUNDAMENTAL.value == "fundamental"
        assert AgentCategory.SENTIMENT.value == "sentiment"
        assert AgentCategory.MACRO.value == "macro"
        assert AgentCategory.RISK.value == "risk"
