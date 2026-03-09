"""
Base Agent Tests

Tests for BaseAgent abstract class.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from agents.base_agent import (
    BaseAgent,
    AgentMetadata,
    AgentConfig,
    AgentError,
    AgentExecutionError,
    AgentValidationError,
    AgentRegistry,
)
from signals.signal_schema import AgentSignal, AgentCategory


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""
    
    def compute_signal(self, features):
        """Compute a simple test signal."""
        rsi = features.get("rsi", 50)
        
        if rsi < 30:
            return AgentSignal(
                agent_name=self.agent_name,
                agent_category=self.agent_category.value,
                signal="buy",
                confidence=80.0,
                numerical_score=-0.8,
                reasoning="RSI oversold"
            )
        elif rsi > 70:
            return AgentSignal(
                agent_name=self.agent_name,
                agent_category=self.agent_category.value,
                signal="sell",
                confidence=80.0,
                numerical_score=0.8,
                reasoning="RSI overbought"
            )
        else:
            return AgentSignal(
                agent_name=self.agent_name,
                agent_category=self.agent_category.value,
                signal="hold",
                confidence=50.0,
                numerical_score=0.0,
                reasoning="RSI neutral"
            )


class TestAgentMetadata:
    """Tests for AgentMetadata."""
    
    def test_default_values(self):
        """Test default metadata values."""
        metadata = AgentMetadata()
        
        assert metadata.version == "1.0.0"
        assert metadata.description == ""
        assert metadata.required_features == []
        assert metadata.author == ""
        assert metadata.tags == []
        assert metadata.max_cache_age_seconds == 300
    
    def test_custom_values(self):
        """Test custom metadata values."""
        metadata = AgentMetadata(
            version="2.0.0",
            description="Test agent",
            required_features=["price", "volume"],
            author="Test Author",
            tags=["test", "demo"],
        )
        
        assert metadata.version == "2.0.0"
        assert metadata.description == "Test agent"
        assert metadata.required_features == ["price", "volume"]
        assert metadata.author == "Test Author"
        assert "test" in metadata.tags


class TestAgentConfig:
    """Tests for AgentConfig."""
    
    def test_default_values(self):
        """Test default config values."""
        config = AgentConfig()
        
        assert config.enable_cache is True
        assert config.cache_ttl_seconds == 300
        assert config.timeout_seconds == 30
        assert config.max_retries == 3
        assert config.enable_parallel is True
        assert config.max_workers == 16
    
    def test_custom_values(self):
        """Test custom config values."""
        config = AgentConfig(
            enable_cache=False,
            cache_ttl_seconds=600,
            max_retries=5,
        )
        
        assert config.enable_cache is False
        assert config.cache_ttl_seconds == 600
        assert config.max_retries == 5


class TestBaseAgent:
    """Tests for BaseAgent class."""
    
    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        return ConcreteAgent(
            agent_name="test_agent",
            agent_category=AgentCategory.TECHNICAL,
        )
    
    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.agent_name == "test_agent"
        assert agent.agent_category == AgentCategory.TECHNICAL
    
    def test_agent_version(self, agent):
        """Test agent version property."""
        assert agent.version == "1.0.0"
    
    def test_agent_description(self, agent):
        """Test agent description property."""
        assert agent.description == ""
    
    def test_required_features(self, agent):
        """Test required features property."""
        assert agent.required_features == []
    
    def test_compute_signal_oversold(self, agent):
        """Test signal computation with oversold RSI."""
        features = {"rsi": 25}
        
        signal = agent.compute_signal(features)
        
        assert signal.signal == "buy"
        assert signal.confidence > 50
    
    def test_compute_signal_overbought(self, agent):
        """Test signal computation with overbought RSI."""
        features = {"rsi": 75}
        
        signal = agent.compute_signal(features)
        
        assert signal.signal == "sell"
        assert signal.confidence > 50
    
    def test_compute_signal_neutral(self, agent):
        """Test signal computation with neutral RSI."""
        features = {"rsi": 50}
        
        signal = agent.compute_signal(features)
        
        assert signal.signal == "hold"
    
    def test_run_agent(self, agent):
        """Test running the agent."""
        features = {"rsi": 25}
        
        signal = agent.run(features)
        
        assert isinstance(signal, AgentSignal)
        assert signal.signal == "buy"
    
    def test_run_with_cache(self, agent):
        """Test agent with caching."""
        features = {"rsi": 25}
        
        # First run
        signal1 = agent.run(features)
        
        # Second run should hit cache
        signal2 = agent.run(features)
        
        assert signal1.signal == signal2.signal
    
    def test_run_force_refresh(self, agent):
        """Test force refresh."""
        features = {"rsi": 25}
        
        signal1 = agent.run(features)
        signal2 = agent.run(features, force_refresh=True)
        
        assert isinstance(signal2, AgentSignal)
    
    def test_clear_cache(self, agent):
        """Test cache clearing."""
        features = {"rsi": 25}
        
        agent.run(features)
        agent.clear_cache()
        
        stats = agent.get_cache_stats()
        assert stats["total_entries"] == 0
    
    def test_cache_stats(self, agent):
        """Test cache statistics."""
        features = {"rsi": 25}
        
        agent.run(features)
        
        stats = agent.get_cache_stats()
        
        assert stats["agent_name"] == "test_agent"
        assert stats["total_entries"] == 1
        assert stats["cache_enabled"] is True
    
    def test_generate_cache_key(self, agent):
        """Test cache key generation."""
        features1 = {"rsi": 25, "price": 100}
        features2 = {"rsi": 25, "price": 100}
        features3 = {"rsi": 30, "price": 100}
        
        key1 = agent._generate_cache_key(features1)
        key2 = agent._generate_cache_key(features2)
        key3 = agent._generate_cache_key(features3)
        
        assert key1 == key2  # Same features should produce same key
        assert key1 != key3  # Different features should produce different key
    
    def test_error_signal_creation(self, agent):
        """Test error signal creation."""
        error_signal = agent._create_error_signal("Test error", 0.5)
        
        assert error_signal.signal == "hold"
        assert error_signal.confidence == 0.0
        assert "error" in error_signal.reasoning.lower()
    
    def test_validation(self, agent):
        """Test feature validation."""
        # Should not raise - validation is soft
        features = {"rsi": 50}
        agent._validate_features(features)
    
    def test_agent_info(self, agent):
        """Test getting agent info."""
        info = agent.get_agent_info()
        
        assert info["agent_name"] == "test_agent"
        assert info["agent_category"] == "technical"
        assert "config" in info
        assert "cache_stats" in info
    
    def test_agent_repr(self, agent):
        """Test agent string representation."""
        repr_str = repr(agent)
        
        assert "test_agent" in repr_str
        assert "technical" in repr_str
    
    def test_agent_str(self, agent):
        """Test agent string."""
        str_val = str(agent)
        
        assert "test_agent" in str_val


class TestAgentRegistry:
    """Tests for AgentRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create a test registry."""
        return AgentRegistry()
    
    def test_register_agent(self, registry):
        """Test registering an agent."""
        agent = ConcreteAgent(
            agent_name="test_agent",
            agent_category=AgentCategory.TECHNICAL,
        )
        
        registry.register(agent)
        
        assert "test_agent" in registry.list_agents()
    
    def test_register_duplicate(self, registry):
        """Test registering duplicate agent raises error."""
        agent1 = ConcreteAgent(
            agent_name="test_agent",
            agent_category=AgentCategory.TECHNICAL,
        )
        agent2 = ConcreteAgent(
            agent_name="test_agent",
            agent_category=AgentCategory.FUNDAMENTAL,
        )
        
        registry.register(agent1)
        
        with pytest.raises(AgentError):
            registry.register(agent2)
    
    def test_unregister_agent(self, registry):
        """Test unregistering an agent."""
        agent = ConcreteAgent(
            agent_name="test_agent",
            agent_category=AgentCategory.TECHNICAL,
        )
        
        registry.register(agent)
        registry.unregister("test_agent")
        
        assert "test_agent" not in registry.list_agents()
    
    def test_get_agent(self, registry):
        """Test getting an agent."""
        agent = ConcreteAgent(
            agent_name="test_agent",
            agent_category=AgentCategory.TECHNICAL,
        )
        
        registry.register(agent)
        retrieved = registry.get("test_agent")
        
        assert retrieved is agent
    
    def test_get_nonexistent_agent(self, registry):
        """Test getting nonexistent agent returns None."""
        result = registry.get("nonexistent")
        
        assert result is None
    
    def test_get_agents_by_category(self, registry):
        """Test getting agents by category."""
        agent1 = ConcreteAgent(
            agent_name="agent1",
            agent_category=AgentCategory.TECHNICAL,
        )
        
        registry.register(agent1)
        
        tech_agents = registry.get_agents_by_category(AgentCategory.TECHNICAL)
        
        assert len(tech_agents) == 1
    
    def test_clear_cache_all(self, registry):
        """Test clearing cache for all agents."""
        agent = ConcreteAgent(
            agent_name="test_agent",
            agent_category=AgentCategory.TECHNICAL,
        )
        
        agent.run({"rsi": 25})
        registry.register(agent)
        
        registry.clear_cache_all()
        
        stats = agent.get_cache_stats()
        assert stats["total_entries"] == 0
    
    def test_registry_len(self, registry):
        """Test registry length."""
        agent = ConcreteAgent(
            agent_name="test_agent",
            agent_category=AgentCategory.TECHNICAL,
        )
        
        assert len(registry) == 0
        
        registry.register(agent)
        
        assert len(registry) == 1
    
    def test_registry_contains(self, registry):
        """Test registry contains check."""
        agent = ConcreteAgent(
            agent_name="test_agent",
            agent_category=AgentCategory.TECHNICAL,
        )
        
        assert "test_agent" not in registry
        
        registry.register(agent)
        
        assert "test_agent" in registry
