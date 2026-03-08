"""
Integration Tests

End-to-end integration tests for the trading system.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from signals.signal_schema import AgentSignal
from signals.signal_aggregator import SignalAggregator
from portfolio.portfolio_engine import PortfolioEngine
from agents.technical.rsi_agent import RSIAgent
from features.indicators import TechnicalFeatures
import pandas as pd
import numpy as np


class TestAgentPipeline:
    """Integration tests for agent execution pipeline."""
    
    @pytest.mark.integration
    def test_complete_agent_flow(self):
        """Test complete flow from features to signal."""
        # Create sample price data
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        np.random.seed(42)
        prices = 1500 + np.cumsum(np.random.randn(50) * 5)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': prices + 10,
            'low': prices - 10,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, 50),
        })
        
        # Calculate features
        features_df = TechnicalFeatures.calculate_all(df)
        features = TechnicalFeatures.get_current_features(features_df)
        
        # Run agent
        agent = RSIAgent()
        signal = agent.run(features)
        
        assert signal is not None
        assert signal.signal in ['buy', 'sell', 'hold']
    
    @pytest.mark.integration
    def test_multiple_agents_flow(self):
        """Test flow with multiple agents."""
        features = {
            'close': 1550.0,
            'rsi': 25.0,
            'price_position_20': 0.3,
            'atr': 25.0,
        }
        
        # Run RSI agent
        rsi_agent = RSIAgent()
        rsi_signal = rsi_agent.run(features)
        
        # Create aggregated signal
        aggregator = SignalAggregator()
        aggregated = aggregator.aggregate_signals(
            signals=[rsi_signal],
            regime="bull",
            stock_symbol="RELIANCE"
        )
        
        assert aggregated.final_score >= 0.6
        assert aggregated.decision == "buy"


class TestPortfolioFlow:
    """Integration tests for portfolio management flow."""
    
    @pytest.mark.integration
    def test_signal_to_portfolio_decision(self):
        """Test flow from signal to portfolio decision."""
        from signals.signal_schema import AggregatedSignal
        
        # Create mock aggregated signal
        signal = AggregatedSignal(
            stock_symbol="RELIANCE",
            final_score=0.75,
            decision="buy",
            confidence=80.0,
            supporting_agents=["rsi_agent", "macd_agent"],
            conflicting_agents=[],
            agent_signals=[],
            regime="bull"
        )
        
        # Create portfolio engine
        engine = PortfolioEngine()
        
        # Evaluate decision
        decision = engine.evaluate_decision(
            signal=signal,
            current_prices={"RELIANCE": 2950.0}
        )
        
        assert decision.decision in ["buy", "hold"]
        assert decision.confidence >= 0
    
    @pytest.mark.integration
    def test_complete_trading_flow(self):
        """Test complete trading flow."""
        from signals.signal_schema import AggregatedSignal, AgentSignal
        
        # Step 1: Generate agent signal
        features = {
            'rsi': 25.0,
            'close': 1500.0,
            'price_position_20': 0.3,
            'atr': 25.0,
        }
        
        agent = RSIAgent()
        signal = agent.compute_signal(features)
        
        # Step 2: Aggregate signals
        aggregator = SignalAggregator()
        aggregated = aggregator.aggregate_signals(
            signals=[signal],
            regime="bull",
            stock_symbol="RELIANCE"
        )
        
        # Step 3: Generate portfolio decision
        engine = PortfolioEngine()
        decision = engine.evaluate_decision(
            signal=aggregated,
            current_prices={"RELIANCE": 1500.0}
        )
        
        # Step 4: Open position if buy
        if decision.decision == "buy":
            position = engine.open_position("RELIANCE", decision, 1500.0)
            assert "RELIANCE" in engine.positions


class TestDataPipeline:
    """Integration tests for data pipeline."""
    
    @pytest.mark.integration
    def test_unified_data_service_cache(self):
        """Test unified data service caching."""
        from data.services import UnifiedDataService
        
        service = UnifiedDataService()
        
        # Set cache
        service._set_cache("test_key", {"data": "test"})
        
        # Get from cache
        result = service._get_cache("test_key")
        
        assert result == {"data": "test"}
    
    @pytest.mark.integration
    def test_data_service_clear_cache(self):
        """Test clearing service cache."""
        from data.services import UnifiedDataService
        
        service = UnifiedDataService()
        
        service._set_cache("key1", "value1")
        service._set_cache("key2", "value2")
        
        service.clear_cache()
        
        assert len(service._cache) == 0


class TestFeaturePipeline:
    """Integration tests for feature engineering pipeline."""
    
    @pytest.mark.integration
    def test_full_feature_calculation(self):
        """Test complete feature calculation pipeline."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        prices = 1500 + np.cumsum(np.random.randn(100) * 10)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices + np.random.randn(100) * 2,
            'high': prices + np.abs(np.random.randn(100) * 5),
            'low': prices - np.abs(np.random.randn(100) * 5),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 100),
        })
        
        result = TechnicalFeatures.calculate_all(df)
        
        # Verify all expected columns exist
        expected_columns = [
            'returns', 'log_returns', 'sma_20', 'sma_50', 'sma_200',
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'bb_upper', 'bb_middle', 'bb_lower', 'atr',
            'volume_sma_20', 'volume_ratio', 'momentum_5',
            'stoch_k', 'stoch_d', 'pivot'
        ]
        
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"
    
    @pytest.mark.integration
    def test_features_to_agent_flow(self):
        """Test features flowing to agent correctly."""
        dates = pd.date_range(start='2024-01-01', periods=60, freq='D')
        np.random.seed(42)
        prices = 1500 + np.cumsum(np.random.randn(60) * 5)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': prices + 10,
            'low': prices - 10,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, 60),
        })
        
        # Calculate all features
        features_df = TechnicalFeatures.calculate_all(df)
        
        # Get current features
        current = TechnicalFeatures.get_current_features(features_df)
        
        # Run agent
        agent = RSIAgent()
        signal = agent.compute_signal(current)
        
        assert signal.signal in ['buy', 'sell', 'hold']


class TestRegimeBasedWeights:
    """Integration tests for regime-based weights."""
    
    @pytest.mark.integration
    def test_bull_regime_weights(self):
        """Test weights in bull regime."""
        aggregator = SignalAggregator()
        
        weights = aggregator._get_regime_weights("bull")
        
        assert weights is not None
        assert abs(sum(weights.values()) - 1.0) < 0.001
    
    @pytest.mark.integration
    def test_bear_regime_weights(self):
        """Test weights in bear regime."""
        aggregator = SignalAggregator()
        
        weights = aggregator._get_regime_weights("bear")
        
        assert weights is not None
        assert weights["risk"] >= 0.15
    
    @pytest.mark.integration
    def test_regime_aggregation(self):
        """Test signal aggregation with different regimes."""
        signals = [
            AgentSignal(
                agent_name="rsi_agent",
                agent_category="technical",
                signal="buy",
                confidence=80.0,
                numerical_score=-0.8,
            ),
        ]
        
        aggregator = SignalAggregator()
        
        # Aggregate with bull regime
        result_bull = aggregator.aggregate_signals(
            signals=signals,
            regime="bull",
            stock_symbol="TEST"
        )
        
        # Aggregate with bear regime
        result_bear = aggregator.aggregate_signals(
            signals=signals,
            regime="bear",
            stock_symbol="TEST"
        )
        
        # Both should produce buy signal for strong buy signal
        assert result_bull.decision == "buy"
        assert result_bear.decision == "buy"
