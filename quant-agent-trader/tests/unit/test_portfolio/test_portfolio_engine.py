"""
Portfolio Engine Tests

Tests for portfolio management and position handling.
"""

import pytest
from datetime import datetime
from portfolio.portfolio_engine import PortfolioEngine, Position, Portfolio, RiskLevel
from signals.signal_schema import AggregatedSignal, AgentSignal


class TestPortfolioEngine:
    """Tests for PortfolioEngine class."""
    
    @pytest.fixture
    def engine(self):
        """Create a portfolio engine."""
        return PortfolioEngine()
    
    def test_engine_initialization(self, engine):
        """Test engine initializes correctly."""
        assert engine.portfolio.cash == 100000.0
        assert engine.positions == {}
    
    def test_evaluate_decision_hold(self, engine):
        """Test hold decision when confidence is low."""
        signal = AggregatedSignal(
            stock_symbol="RELIANCE",
            final_score=0.5,
            decision="hold",
            confidence=40.0,
            supporting_agents=[],
            conflicting_agents=[],
            agent_signals=[],
            regime="bull",
        )
        
        result = engine.evaluate_decision(signal, {"RELIANCE": 2950.0})
        
        assert result.decision == "hold"
    
    def test_evaluate_decision_invalid_price(self, engine):
        """Test decision with invalid price."""
        signal = AggregatedSignal(
            stock_symbol="RELIANCE",
            final_score=0.7,
            decision="buy",
            confidence=75.0,
            supporting_agents=[],
            conflicting_agents=[],
            agent_signals=[],
            regime="bull",
        )
        
        result = engine.evaluate_decision(signal, {"RELIANCE": 0.0})
        
        assert result.decision == "hold"
    
    def test_calculate_position_size(self, engine):
        """Test position size calculation."""
        signal = AggregatedSignal(
            stock_symbol="RELIANCE",
            final_score=0.7,
            decision="buy",
            confidence=75.0,
            supporting_agents=[],
            conflicting_agents=[],
            agent_signals=[],
            regime="bull",
        )
        
        size = engine.calculate_position_size(
            signal=signal,
            portfolio_value=100000.0,
            risk_level="low"
        )
        
        assert 0 <= size <= engine.config.max_position_size
    
    def test_calculate_stop_loss(self, engine):
        """Test stop loss calculation."""
        stop_loss = engine.calculate_stop_loss(
            entry_price=3000.0,
            atr=50.0,
            regime="bull"
        )
        
        assert stop_loss is not None
        assert stop_loss < 3000.0
    
    def test_calculate_stop_loss_no_atr(self, engine):
        """Test stop loss calculation without ATR."""
        stop_loss = engine.calculate_stop_loss(
            entry_price=3000.0,
            atr=0.0,
            regime="bull"
        )
        
        assert stop_loss is not None
        assert stop_loss < 3000.0
    
    def test_calculate_take_profit(self, engine):
        """Test take profit calculation."""
        take_profit = engine.calculate_take_profit(
            entry_price=3000.0,
            risk_reward_ratio=2.0
        )
        
        assert take_profit is not None
        assert take_profit > 3000.0
    
    def test_update_position(self, engine):
        """Test position update."""
        from dataclasses import replace
        position = Position(
            stock_symbol="RELIANCE",
            entry_price=2900.0,
            current_price=2900.0,
            position_size=100,
        )
        engine.positions["RELIANCE"] = position
        
        engine.update_position("RELIANCE", 2950.0)
        
        assert engine.positions["RELIANCE"].current_price == 2950.0
    
    def test_close_position(self, engine):
        """Test closing a position."""
        position = Position(
            stock_symbol="RELIANCE",
            entry_price=2900.0,
            current_price=2950.0,
            position_size=100,
        )
        engine.positions["RELIANCE"] = position
        
        result = engine.close_position("RELIANCE", 2950.0)
        
        assert result is not None
        assert "RELIANCE" not in engine.positions
    
    def test_close_nonexistent_position(self, engine):
        """Test closing nonexistent position."""
        result = engine.close_position("RELIANCE", 2950.0)
        
        assert result is None
    
    def test_open_position(self, engine):
        """Test opening a new position."""
        from signals.signal_schema import PortfolioDecision
        
        decision = PortfolioDecision(
            stock_symbol="RELIANCE",
            decision="buy",
            position_size=0.1,
            confidence=75.0,
            risk_level="medium",
            stop_loss=2800.0,
            take_profit=3100.0,
        )
        
        position = engine.open_position("RELIANCE", decision, 2950.0)
        
        assert "RELIANCE" in engine.positions
        assert position.entry_price == 2950.0
    
    def test_get_portfolio_summary(self, engine):
        """Test portfolio summary."""
        position = Position(
            stock_symbol="RELIANCE",
            entry_price=2900.0,
            current_price=2950.0,
            position_size=100,
        )
        engine.positions["RELIANCE"] = position
        
        summary = engine.get_portfolio_summary()
        
        assert "total_value" in summary
        assert "cash" in summary
        assert "positions" in summary
    
    def test_rebalance_portfolio(self, engine):
        """Test portfolio rebalancing."""
        position = Position(
            stock_symbol="RELIANCE",
            entry_price=2900.0,
            current_price=2950.0,
            position_size=100,
        )
        engine.positions["RELIANCE"] = position
        
        decisions = engine.rebalance_portfolio(
            positions=engine.positions,
            target_allocation={"RELIANCE": 0.2, "TCS": 0.1},
            current_prices={"RELIANCE": 2950.0, "TCS": 3800.0}
        )
        
        assert isinstance(decisions, list)


class TestPosition:
    """Tests for Position dataclass."""
    
    def test_create_position(self):
        """Test creating a position."""
        position = Position(
            stock_symbol="RELIANCE",
            entry_price=2900.0,
            current_price=2950.0,
            position_size=100,
        )
        
        assert position.stock_symbol == "RELIANCE"
        assert position.entry_price == 2900.0
        assert position.current_price == 2950.0
        assert position.position_size == 100


class TestPortfolio:
    """Tests for Portfolio dataclass."""
    
    def test_create_portfolio(self):
        """Test creating a portfolio."""
        portfolio = Portfolio(
            cash=100000.0,
            positions={},
        )
        
        assert portfolio.cash == 100000.0
        assert portfolio.positions == {}


class TestRiskLevel:
    """Tests for RiskLevel enum."""
    
    def test_risk_level_values(self):
        """Test RiskLevel enum values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
