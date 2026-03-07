"""
AgentDispatcher - Orchestrates multiple trading agents.

This module provides the AgentDispatcher class which manages multiple agents,
handles parallel execution, and coordinates signal generation across
different agent categories.
"""

from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import logging
from datetime import datetime

from agents.base_agent import BaseAgent, AgentRegistry
from signals.signal_schema import AgentSignal, AgentCategory


logger = logging.getLogger(__name__)


class AgentDispatcherError(Exception):
    """Base exception for dispatcher-related errors."""
    pass


class AgentDispatcher:
    """
    Orchestrates multiple trading agents.
    
    Manages agent registration, parallel execution, and coordinates
    signal generation across different agent categories.
    
    Attributes:
        registry: Internal agent registry
        default_timeout: Default timeout for agent execution in seconds
    
    Example:
        dispatcher = AgentDispatcher()
        dispatcher.register_agent(RSIAgent())
        
        signals = dispatcher.dispatch("AAPL", {"rsi": 65.0, "close": 150.0})
    """
    
    def __init__(
        self,
        default_timeout: float = 30.0,
        max_workers: int = 4
    ) -> None:
        """
        Initialize the agent dispatcher.
        
        Args:
            default_timeout: Default timeout for agent execution (seconds)
            max_workers: Maximum number of parallel workers
        """
        self._registry = AgentRegistry()
        self._default_timeout = default_timeout
        self._max_workers = max_workers
        self._logger = logging.getLogger(__name__)
        
        self._agents_by_category: Dict[AgentCategory, List[BaseAgent]] = {}
        
        logger.info(
            f"Initialized AgentDispatcher with timeout={default_timeout}s, "
            f"max_workers={max_workers}"
        )
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Add agent to dispatcher.
        
        Args:
            agent: Agent to register
            
        Raises:
            AgentDispatcherError: If agent is already registered
        """
        if agent.agent_name in self._registry.list_agents():
            raise AgentDispatcherError(
                f"Agent '{agent.agent_name}' is already registered"
            )
        
        self._registry.register(agent)
        
        category = agent.agent_category
        if category not in self._agents_by_category:
            self._agents_by_category[category] = []
        
        if agent not in self._agents_by_category[category]:
            self._agents_by_category[category].append(agent)
        
        logger.info(
            f"Registered agent '{agent.agent_name}' under category "
            f"'{category.value}'"
        )
    
    def register_agents_by_category(self, agents: List[BaseAgent]) -> None:
        """
        Register multiple agents at once.
        
        Args:
            agents: List of agents to register
        """
        for agent in agents:
            self.register_agent(agent)
        
        logger.info(f"Registered {len(agents)} agents")
    
    def dispatch(
        self,
        symbol: str,
        features: Dict[str, Any],
        categories: Optional[List[str]] = None
    ) -> List[AgentSignal]:
        """
        Run matching agents for a symbol.
        
        Args:
            symbol: Stock symbol
            features: Feature dictionary for agents
            categories: Optional list of category names to filter by
            
        Returns:
            List of AgentSignals from all matching agents
        """
        agents = self._get_agents_to_run(categories)
        
        if not agents:
            self._logger.warning(
                f"No agents available for categories: {categories}"
            )
            return []
        
        signals = []
        
        for agent in agents:
            try:
                signal = agent.run(features)
                signal.agent_name = agent.agent_name
                signals.append(signal)
                
                self._logger.debug(
                    f"Agent '{agent.agent_name}' for {symbol}: "
                    f"{signal.signal} (confidence: {signal.confidence})"
                )
                
            except Exception as e:
                self._logger.error(
                    f"Agent '{agent.agent_name}' failed for {symbol}: {e}"
                )
                signals.append(agent._create_error_signal(str(e)))
        
        self._logger.info(
            f"Dispatched to {len(signals)} agents for {symbol}"
        )
        
        return signals
    
    def dispatch_parallel(
        self,
        symbol: str,
        features: Dict[str, Any],
        categories: Optional[List[str]] = None,
        max_workers: Optional[int] = None
    ) -> List[AgentSignal]:
        """
        Run agents in parallel for a symbol.
        
        Args:
            symbol: Stock symbol
            features: Feature dictionary for agents
            categories: Optional list of category names to filter by
            max_workers: Maximum number of parallel workers
            
        Returns:
            List of AgentSignals from all matching agents
        """
        agents = self._get_agents_to_run(categories)
        
        if not agents:
            self._logger.warning(
                f"No agents available for categories: {categories}"
            )
            return []
        
        workers = max_workers or self._max_workers
        signals = []
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_agent = {
                executor.submit(self._run_agent_safe, agent, features): agent
                for agent in agents
            }
            
            for future in as_completed(future_to_agent):
                agent = future_to_agent[future]
                
                try:
                    signal = future.result(timeout=self._default_timeout)
                    signals.append(signal)
                    
                except TimeoutError:
                    self._logger.error(
                        f"Agent '{agent.agent_name}' timed out for {symbol}"
                    )
                    signals.append(
                        agent._create_error_signal(
                            f"Timeout after {self._default_timeout}s"
                        )
                    )
                except Exception as e:
                    self._logger.error(
                        f"Agent '{agent.agent_name}' failed for {symbol}: {e}"
                    )
                    signals.append(agent._create_error_signal(str(e)))
        
        self._logger.info(
            f"Parallel dispatch to {len(signals)} agents for {symbol}"
        )
        
        return signals
    
    def _run_agent_safe(
        self,
        agent: BaseAgent,
        features: Dict[str, Any]
    ) -> AgentSignal:
        """
        Safely run an agent and return its signal.
        
        Args:
            agent: Agent to run
            features: Features dictionary
            
        Returns:
            AgentSignal from the agent
        """
        return agent.run(features)
    
    def _get_agents_to_run(
        self,
        categories: Optional[List[str]] = None
    ) -> List[BaseAgent]:
        """
        Get list of agents to run based on category filter.
        
        Args:
            categories: Optional list of category names
            
        Returns:
            List of agents to run
        """
        if categories is None:
            agents: List[BaseAgent] = []
            for name in self._registry.list_agents():
                agent = self._registry.get(name)
                if agent is not None:
                    agents.append(agent)
            return agents
        
        agents = []
        for cat_name in categories:
            try:
                category = AgentCategory(cat_name)
                agents.extend(self.get_agents_by_category(category))
            except ValueError:
                self._logger.warning(f"Unknown category: {cat_name}")
        
        return agents
    
    def get_available_agents(self) -> Dict[str, List[str]]:
        """
        Get agents grouped by category.
        
        Returns:
            Dictionary mapping category names to list of agent names
        """
        result: Dict[str, List[str]] = {}
        
        for category, agents in self._agents_by_category.items():
            result[category.value] = [agent.agent_name for agent in agents]
        
        return result
    
    def get_agents_by_category(self, category: AgentCategory) -> List[BaseAgent]:
        """
        Get all agents of a specific category.
        
        Args:
            category: AgentCategory to filter by
            
        Returns:
            List of agents in that category
        """
        return self._agents_by_category.get(category, [])
    
    def clear_cache(self) -> None:
        """Clear all agent caches."""
        self._registry.clear_cache_all()
        self._logger.info("Cleared cache for all agents")
    
    def get_dispatcher_info(self) -> Dict[str, Any]:
        """
        Get information about the dispatcher.
        
        Returns:
            Dictionary with dispatcher information
        """
        return {
            "total_agents": len(self._registry),
            "agents_by_category": self.get_available_agents(),
            "default_timeout": self._default_timeout,
            "max_workers": self._max_workers
        }


def create_default_dispatcher() -> AgentDispatcher:
    """
    Create a dispatcher with common technical agents pre-registered.
    
    Creates and registers RSI, MACD, Momentum, Trend, Breakout, and
    Volume agents.
    
    Returns:
        Configured AgentDispatcher instance
        
    Example:
        dispatcher = create_default_dispatcher()
        signals = dispatcher.dispatch("AAPL", features)
    """
    from agents.technical.rsi_agent import RSIAgent
    from agents.technical.macd_agent import MACDAgent
    from agents.technical.momentum_agent import MomentumAgent
    from agents.technical.trend_agent import TrendAgent
    from agents.technical.breakout_agent import BreakoutAgent
    from agents.technical.volume_agent import VolumeAgent
    
    dispatcher = AgentDispatcher()
    
    agents = [
        RSIAgent(),
        MACDAgent(),
        MomentumAgent(),
        TrendAgent(),
        BreakoutAgent(),
        VolumeAgent()
    ]
    
    dispatcher.register_agents_by_category(agents)
    
    logger.info(
        f"Created default dispatcher with {len(agents)} technical agents"
    )
    
    return dispatcher
