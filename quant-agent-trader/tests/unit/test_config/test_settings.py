"""
Configuration Tests

Tests for system configuration and settings.
"""

import pytest
from config.settings import (
    SystemConfig,
    DataConfig,
    AgentConfig,
    SignalConfig,
    PortfolioConfig,
    BacktestConfig,
    RLConfig,
    IndiaConfig,
    REGIME_WEIGHTS,
    AGENT_CATEGORIES,
    config,
)


class TestDataConfig:
    """Tests for DataConfig."""
    
    def test_default_values(self):
        """Test DataConfig default values."""
        data_config = DataConfig()
        
        assert data_config.cache_ttl == 300
        assert data_config.max_retries == 3
        assert data_config.rate_limit_delay == 0.1
    
    def test_custom_values(self):
        """Test DataConfig with custom values."""
        data_config = DataConfig(
            cache_ttl=600,
            max_retries=5,
            rate_limit_delay=0.2,
        )
        
        assert data_config.cache_ttl == 600
        assert data_config.max_retries == 5


class TestAgentConfig:
    """Tests for AgentConfig."""
    
    def test_default_values(self):
        """Test AgentConfig default values."""
        agent_config = AgentConfig()
        
        assert agent_config.agent_timeout == 30
        assert agent_config.enable_caching is True
        assert agent_config.cache_ttl == 3600
        assert agent_config.retry_failed is True
        assert agent_config.max_retries == 2
    
    def test_custom_values(self):
        """Test AgentConfig with custom values."""
        agent_config = AgentConfig(
            agent_timeout=60,
            enable_caching=False,
            max_retries=5,
        )
        
        assert agent_config.agent_timeout == 60
        assert agent_config.enable_caching is False
        assert agent_config.max_retries == 5


class TestSignalConfig:
    """Tests for SignalConfig."""
    
    def test_default_weights(self):
        """Test SignalConfig default weights."""
        signal_config = SignalConfig()
        
        assert signal_config.weights["technical"] == 0.30
        assert signal_config.weights["fundamental"] == 0.25
        assert signal_config.weights["sentiment"] == 0.15
        assert signal_config.weights["macro"] == 0.10
        assert signal_config.weights["market_structure"] == 0.10
        assert signal_config.weights["risk"] == 0.10
    
    def test_weights_sum_to_one(self):
        """Test that weights sum to 1.0."""
        signal_config = SignalConfig()
        
        total = sum(signal_config.weights.values())
        assert abs(total - 1.0) < 0.001
    
    def test_custom_weights(self):
        """Test SignalConfig with custom weights."""
        custom_weights = {
            "technical": 0.35,
            "fundamental": 0.30,
            "sentiment": 0.10,
            "macro": 0.10,
            "market_structure": 0.10,
            "risk": 0.05,
        }
        
        signal_config = SignalConfig(weights=custom_weights)
        
        assert signal_config.weights["technical"] == 0.35
        assert signal_config.weights["fundamental"] == 0.30


class TestPortfolioConfig:
    """Tests for PortfolioConfig."""
    
    def test_default_values(self):
        """Test PortfolioConfig default values."""
        portfolio_config = PortfolioConfig()
        
        assert portfolio_config.max_position_size == 0.10
        assert portfolio_config.default_position_size == 0.05
        assert portfolio_config.max_portfolio_stocks == 20
        assert portfolio_config.rebalance_threshold == 0.15
        assert portfolio_config.risk_per_trade == 0.02
    
    def test_position_size_bounds(self):
        """Test position size bounds."""
        portfolio_config = PortfolioConfig()
        
        # Max position should be 10%
        assert portfolio_config.max_position_size <= 0.10
        # Default position should be 5%
        assert portfolio_config.default_position_size <= 0.05


class TestBacktestConfig:
    """Tests for BacktestConfig."""
    
    def test_default_values(self):
        """Test BacktestConfig default values."""
        backtest_config = BacktestConfig()
        
        assert backtest_config.initial_capital == 100000.0
        assert backtest_config.commission == 0.001
        assert backtest_config.slippage == 0.0005
        assert backtest_config.benchmark == "SPY"


class TestRLConfig:
    """Tests for RLConfig."""
    
    def test_default_values(self):
        """Test RLConfig default values."""
        rl_config = RLConfig()
        
        assert rl_config.learning_rate == 0.01
        assert rl_config.discount_factor == 0.95
        assert rl_config.exploration_rate == 0.1
        assert rl_config.memory_size == 10000
        assert rl_config.batch_size == 32
        assert rl_config.update_frequency == 100


class TestIndiaConfig:
    """Tests for IndiaConfig."""
    
    def test_default_values(self):
        """Test IndiaConfig default values."""
        india_config = IndiaConfig()
        
        assert india_config.enable_india_mode is True
        assert india_config.use_nse is True
        assert india_config.use_bse is False
        assert india_config.include_fno is True
        assert india_config.include_india_vix is True
        assert india_config.default_currency == "INR"
    
    def test_nse_holidays_list(self):
        """Test that NSE holidays list exists."""
        india_config = IndiaConfig()
        
        assert isinstance(india_config.nse_holidays, list)
        assert len(india_config.nse_holidays) > 0


class TestSystemConfig:
    """Tests for SystemConfig."""
    
    def test_default_config(self):
        """Test default SystemConfig."""
        sys_config = SystemConfig()
        
        assert isinstance(sys_config.data, DataConfig)
        assert isinstance(sys_config.agents, AgentConfig)
        assert isinstance(sys_config.signals, SignalConfig)
        assert isinstance(sys_config.portfolio, PortfolioConfig)
        assert isinstance(sys_config.backtest, BacktestConfig)
        assert isinstance(sys_config.rl, RLConfig)
        assert isinstance(sys_config.india, IndiaConfig)
    
    def test_config_singleton(self):
        """Test that config is a singleton."""
        assert config is not None
        assert isinstance(config, SystemConfig)


class TestRegimeWeights:
    """Tests for regime weights."""
    
    def test_all_regimes_defined(self):
        """Test that all regimes are defined."""
        assert "bull" in REGIME_WEIGHTS
        assert "bear" in REGIME_WEIGHTS
        assert "sideways" in REGIME_WEIGHTS
        assert "high_volatility" in REGIME_WEIGHTS
    
    def test_regime_weights_sum(self):
        """Test that each regime's weights sum to 1.0."""
        for regime, weights in REGIME_WEIGHTS.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.001, f"Regime {regime} weights don't sum to 1.0"
    
    def test_all_categories_present(self):
        """Test that all required categories are present."""
        required_categories = {
            "technical", "fundamental", "sentiment",
            "macro", "market_structure", "risk"
        }
        
        for regime, weights in REGIME_WEIGHTS.items():
            assert required_categories == set(weights.keys()), f"Regime {regime} missing categories"


class TestAgentCategories:
    """Tests for agent categories."""
    
    def test_all_categories_defined(self):
        """Test that all categories are defined."""
        assert "technical" in AGENT_CATEGORIES
        assert "fundamental" in AGENT_CATEGORIES
        assert "sentiment" in AGENT_CATEGORIES
        assert "macro" in AGENT_CATEGORIES
        assert "market_structure" in AGENT_CATEGORIES
        assert "risk" in AGENT_CATEGORIES
        assert "india" in AGENT_CATEGORIES
        assert "meta" in AGENT_CATEGORIES
    
    def test_technical_agents(self):
        """Test technical agents list."""
        assert "rsi_agent" in AGENT_CATEGORIES["technical"]
        assert "macd_agent" in AGENT_CATEGORIES["technical"]
        assert "momentum_agent" in AGENT_CATEGORIES["technical"]
    
    def test_india_agents(self):
        """Test India-specific agents."""
        assert "india_vix_agent" in AGENT_CATEGORIES["india"]
        assert "fno_agent" in AGENT_CATEGORIES["india"]
        assert "nifty_sentiment_agent" in AGENT_CATEGORIES["india"]
    
    def test_agents_are_strings(self):
        """Test that agent names are strings."""
        for category, agents in AGENT_CATEGORIES.items():
            for agent in agents:
                assert isinstance(agent, str), f"Agent {agent} in {category} is not a string"


class TestIndiaMarketConfig:
    """Tests for India-specific market configuration."""
    
    def test_nse_symbols_exist(self):
        """Test that NSE symbols are defined."""
        from config.settings import INDIA_NSE_SYMBOLS
        
        assert len(INDIA_NSE_SYMBOLS) > 0
        assert "RELIANCE" in INDIA_NSE_SYMBOLS
        assert "TCS" in INDIA_NSE_SYMBOLS
    
    def test_bse_symbols_exist(self):
        """Test that BSE symbols are defined."""
        from config.settings import INDIA_BSE_SYMBOLS
        
        assert len(INDIA_BSE_SYMBOLS) > 0
    
    def test_indices_defined(self):
        """Test that indices are defined."""
        from config.settings import INDIA_INDICES
        
        assert "NIFTY 50" in INDIA_INDICES
        assert "NIFTY BANK" in INDIA_INDICES
        assert "INDIA VIX" in INDIA_INDICES
    
    def test_fno_stocks_defined(self):
        """Test that F&O stocks are defined."""
        from config.settings import INDIA_FNO_STOCKS
        
        assert len(INDIA_FNO_STOCKS) > 0
    
    def test_trading_rules_defined(self):
        """Test that trading rules are defined."""
        from config.settings import INDIA_TRADING_RULES
        
        assert "lot_sizes" in INDIA_TRADING_RULES
        assert "tick_size" in INDIA_TRADING_RULES
        assert INDIA_TRADING_RULES["tick_size"] == 0.05
