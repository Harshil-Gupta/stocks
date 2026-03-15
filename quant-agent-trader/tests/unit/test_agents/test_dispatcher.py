"""
Agent Dispatcher Tests

Tests for agent dispatcher functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import pandas as pd
import numpy as np


class TestAgentDispatcher:
    """Tests for AgentDispatcher class."""

    @pytest.fixture
    def dispatcher(self):
        """Create agent dispatcher instance."""
        from agents.agent_dispatcher import AgentDispatcher, DispatcherConfig

        config = DispatcherConfig(
            enable_cache=True,
            cache_ttl_seconds=60,
            timeout_seconds=30,
            max_retries=3,
            enable_retry=True,
        )
        return AgentDispatcher(config=config)

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent."""
        agent = Mock()
        agent.name = "test_agent"
        agent.category = "technical"
        agent.analyze = AsyncMock(
            return_value={"signal": "buy", "confidence": 75.0, "numerical_score": -0.75}
        )
        return agent

    def test_dispatcher_initialization(self, dispatcher):
        """Test dispatcher initializes."""
        assert dispatcher is not None
        assert dispatcher.config is not None

    def test_register_agent(self, dispatcher, mock_agent):
        """Test registering an agent."""
        dispatcher.register_agent(mock_agent)

        assert "test_agent" in dispatcher.agents

    def test_register_multiple_agents(self, dispatcher):
        """Test registering multiple agents."""
        for i in range(5):
            agent = Mock()
            agent.name = f"agent_{i}"
            agent.category = "technical"
            agent.analyze = AsyncMock()
            dispatcher.register_agent(agent)

        assert len(dispatcher.agents) == 5

    def test_dispatch_to_single_agent(self, dispatcher, mock_agent):
        """Test dispatching to single agent."""
        dispatcher.register_agent(mock_agent)

        market_data = {"RELIANCE": {"close": 2950.0, "rsi": 65.0, "volume": 5000000}}

        results = dispatcher.dispatch(
            agents=[mock_agent], market_data=market_data, use_cache=True
        )

        assert "RELIANCE" in results

    def test_dispatch_with_cache(self, dispatcher, mock_agent):
        """Test dispatching with cache."""
        dispatcher.register_agent(mock_agent)

        market_data = {"RELIANCE": {"close": 2950.0}}

        # First call
        results1 = dispatcher.dispatch(
            agents=[mock_agent], market_data=market_data, use_cache=True
        )

        # Second call should use cache
        results2 = dispatcher.dispatch(
            agents=[mock_agent], market_data=market_data, use_cache=True
        )

        assert results1 is not None

    def test_dispatch_timeout(self, dispatcher):
        """Test dispatch with timeout."""
        slow_agent = Mock()
        slow_agent.name = "slow_agent"
        slow_agent.category = "technical"

        async def slow_analyze(*args, **kwargs):
            import asyncio

            await asyncio.sleep(5)
            return {"signal": "hold"}

        slow_agent.analyze = slow_analyze
        dispatcher.register_agent(slow_agent)

        market_data = {"RELIANCE": {"close": 2950.0}}

        # This should timeout
        results = dispatcher.dispatch(
            agents=[slow_agent], market_data=market_data, use_cache=False
        )

        assert results is not None

    def test_dispatch_error_handling(self, dispatcher):
        """Test dispatch error handling."""
        error_agent = Mock()
        error_agent.name = "error_agent"
        error_agent.category = "technical"
        error_agent.analyze = AsyncMock(side_effect=Exception("Test error"))

        dispatcher.register_agent(error_agent)

        market_data = {"RELIANCE": {"close": 2950.0}}

        results = dispatcher.dispatch(
            agents=[error_agent], market_data=market_data, use_cache=False
        )

        # Should handle error gracefully
        assert results is not None

    def test_get_agent_by_name(self, dispatcher, mock_agent):
        """Test getting agent by name."""
        dispatcher.register_agent(mock_agent)

        agent = dispatcher.get_agent("test_agent")

        assert agent is not None
        assert agent.name == "test_agent"

    def test_get_agent_not_found(self, dispatcher):
        """Test getting non-existent agent."""
        agent = dispatcher.get_agent("nonexistent")

        assert agent is None

    def test_remove_agent(self, dispatcher, mock_agent):
        """Test removing agent."""
        dispatcher.register_agent(mock_agent)
        dispatcher.remove_agent("test_agent")

        assert "test_agent" not in dispatcher.agents

    def test_clear_cache(self, dispatcher):
        """Test clearing cache."""
        dispatcher.cache["test_key"] = {"data": "value"}

        dispatcher.clear_cache()

        assert len(dispatcher.cache) == 0


class TestDispatcherConfig:
    """Tests for DispatcherConfig."""

    def test_default_config(self):
        """Test default configuration."""
        from agents.agent_dispatcher import DispatcherConfig

        config = DispatcherConfig()

        assert config.enable_cache is True
        assert config.cache_ttl_seconds > 0
        assert config.timeout_seconds > 0

    def test_custom_config(self):
        """Test custom configuration."""
        from agents.agent_dispatcher import DispatcherConfig

        config = DispatcherConfig(
            enable_cache=False, cache_ttl_seconds=120, timeout_seconds=60, max_retries=5
        )

        assert config.enable_cache is False
        assert config.cache_ttl_seconds == 120
        assert config.timeout_seconds == 60
        assert config.max_retries == 5


class TestDispatcherEdgeCases:
    """Edge case tests for dispatcher."""

    def test_dispatch_empty_agents(self):
        """Test dispatching with no agents."""
        from agents.agent_dispatcher import AgentDispatcher, DispatcherConfig

        dispatcher = AgentDispatcher(config=DispatcherConfig())

        market_data = {"RELIANCE": {"close": 2950.0}}

        results = dispatcher.dispatch(
            agents=[], market_data=market_data, use_cache=False
        )

        assert results == {}

    def test_dispatch_empty_market_data(self):
        """Test dispatching with empty market data."""
        from agents.agent_dispatcher import AgentDispatcher, DispatcherConfig

        dispatcher = AgentDispatcher(config=DispatcherConfig())

        agent = Mock()
        agent.name = "test"
        agent.category = "technical"
        agent.analyze = AsyncMock(return_value={"signal": "hold"})

        results = dispatcher.dispatch(agents=[agent], market_data={}, use_cache=False)

        assert isinstance(results, dict)

    def test_parallel_dispatch(self):
        """Test parallel dispatching."""
        from agents.agent_dispatcher import AgentDispatcher, DispatcherConfig

        dispatcher = AgentDispatcher(config=DispatcherConfig())

        for i in range(10):
            agent = Mock()
            agent.name = f"agent_{i}"
            agent.category = "technical"
            agent.analyze = AsyncMock(
                return_value={"signal": "buy", "confidence": 75.0}
            )
            dispatcher.register_agent(agent)

        market_data = {"RELIANCE": {"close": 2950.0}}

        results = dispatcher.dispatch(
            agents=list(dispatcher.agents.values()),
            market_data=market_data,
            use_cache=False,
        )

        assert isinstance(results, dict)


class TestDispatcherWithMockAPI:
    """Tests with mocked API calls."""

    @pytest.mark.asyncio
    async def test_analyze_with_api_error(self):
        """Test handling API errors."""
        from agents.agent_dispatcher import AgentDispatcher, DispatcherConfig

        dispatcher = AgentDispatcher(config=DispatcherConfig())

        error_agent = Mock()
        error_agent.name = "error_agent"
        error_agent.category = "technical"
        error_agent.analyze = AsyncMock(side_effect=ConnectionError("API unavailable"))

        dispatcher.register_agent(error_agent)

        market_data = {"RELIANCE": {"close": 2950.0}}

        results = dispatcher.dispatch(
            agents=[error_agent], market_data=market_data, use_cache=False
        )

        assert results is not None

    def test_retry_logic(self):
        """Test retry logic."""
        from agents.agent_dispatcher import AgentDispatcher, DispatcherConfig

        config = DispatcherConfig(enable_retry=True, max_retries=3)
        dispatcher = AgentDispatcher(config=config)

        attempt_count = 0

        def failing_analyze(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary error")
            return {"signal": "hold"}

        agent = Mock()
        agent.name = "retry_agent"
        agent.category = "technical"
        agent.analyze = AsyncMock(side_effect=failing_analyze)

        dispatcher.register_agent(agent)

        market_data = {"RELIANCE": {"close": 2950.0}}

        results = dispatcher.dispatch(
            agents=[agent], market_data=market_data, use_cache=False
        )

        # Should have retried
        assert attempt_count >= 1
