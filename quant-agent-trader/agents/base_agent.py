"""
Base Agent Class - Abstract base for all trading agents.

This module provides the BaseAgent abstract class that all trading agents
must inherit from. It includes caching, error handling, async support,
and structured signal output.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, Future
import hashlib
import json
import logging
import asyncio

from signals.signal_schema import AgentSignal, AgentCategory


logger = logging.getLogger(__name__)


@dataclass
class AgentMetadata:
    """Metadata for agent configuration and capabilities."""
    version: str = "1.0.0"
    description: str = ""
    required_features: List[str] = field(default_factory=list)
    author: str = ""
    tags: List[str] = field(default_factory=list)
    max_cache_age_seconds: int = 300


@dataclass
class AgentConfig:
    """Configuration for agent execution."""
    enable_cache: bool = True
    cache_ttl_seconds: int = 300
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    enable_parallel: bool = True
    max_workers: int = 4


class AgentError(Exception):
    """Base exception for agent-related errors."""
    pass


class AgentExecutionError(AgentError):
    """Raised when agent execution fails."""
    pass


class AgentCacheError(AgentError):
    """Raised when cache operations fail."""
    pass


class AgentValidationError(AgentError):
    """Raised when input validation fails."""
    pass


class BaseAgent(ABC):
    """
    Abstract base class for all trading agents.
    
    All agents must inherit from this class and implement the `compute_signal`
    method. The class provides:
    - Structured signal output via AgentSignal
    - Built-in caching mechanism
    - Error handling with retries
    - Async/parallel execution support
    - Input validation
    
    Attributes:
        agent_name: Unique identifier for the agent
        agent_category: Category classification from AgentCategory enum
        metadata: AgentMetadata containing version, description, features
        config: AgentConfig for execution settings
    
    Example:
        class MyAgent(BaseAgent):
            def __init__(self):
                super().__init__(
                    agent_name="my_agent",
                    agent_category=AgentCategory.TECHNICAL,
                    metadata=AgentMetadata(
                        version="1.0.0",
                        description="My custom agent",
                        required_features=["price", "volume"]
                    )
                )
            
            def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
                # Implementation here
                pass
    """
    
    def __init__(
        self,
        agent_name: str,
        agent_category: AgentCategory,
        metadata: Optional[AgentMetadata] = None,
        config: Optional[AgentConfig] = None
    ) -> None:
        """
        Initialize the base agent.
        
        Args:
            agent_name: Unique identifier for this agent
            agent_category: Category classification from AgentCategory enum
            metadata: Optional metadata (version, description, features)
            config: Optional execution configuration
        """
        self._agent_name = agent_name
        self._agent_category = agent_category
        self._metadata = metadata or AgentMetadata()
        self._config = config or AgentConfig()
        self._cache: Dict[str, tuple[AgentSignal, datetime]] = {}
        self._executor: Optional[ThreadPoolExecutor] = None
        
        self._validate_metadata()
        
        logger.debug(
            f"Initialized agent: {agent_name} "
            f"(category: {agent_category.value}, version: {self._metadata.version})"
        )
    
    @property
    def agent_name(self) -> str:
        """Get the agent's unique name."""
        return self._agent_name
    
    @property
    def agent_category(self) -> AgentCategory:
        """Get the agent's category."""
        return self._agent_category
    
    @property
    def metadata(self) -> AgentMetadata:
        """Get the agent's metadata."""
        return self._metadata
    
    @property
    def config(self) -> AgentConfig:
        """Get the agent's configuration."""
        return self._config
    
    @property
    def version(self) -> str:
        """Get the agent's version."""
        return self._metadata.version
    
    @property
    def description(self) -> str:
        """Get the agent's description."""
        return self._metadata.description
    
    @property
    def required_features(self) -> List[str]:
        """Get the list of required features for this agent."""
        return self._metadata.required_features
    
    def _validate_metadata(self) -> None:
        """Validate agent metadata."""
        if not self._agent_name or not self._agent_name.strip():
            raise AgentValidationError("Agent name cannot be empty")
        
        if not isinstance(self._agent_category, AgentCategory):
            raise AgentValidationError(
                f"Invalid agent category: {self._agent_category}"
            )
    
    def _validate_features(self, features: Dict[str, Any]) -> None:
        """
        Validate that required features are present in input.
        Skips validation if no required features are defined or config says to skip.
        
        Args:
            features: Dictionary of features to validate
            
        Note:
            Agents should gracefully handle missing features in compute_signal()
            rather than failing here. This is a soft validation.
        """
        # Skip validation if no required features defined
        if not self._required_features:
            return
        
        # Skip validation if explicitly disabled in config
        # Agents should handle missing data gracefully in compute_signal()
        if hasattr(self._config, 'skip_validation') and self._config.skip_validation:
            missing = set(self._required_features) - set(features.keys())
            if missing:
                logger.debug(f"Agent '{self._agent_name}' skipping validation for missing: {missing}")
            return
        
        missing_features = set(self._required_features) - set(features.keys())
        
        if missing_features:
            # Log but don't fail - let the agent handle it gracefully
            logger.debug(
                f"Agent '{self._agent_name}' missing optional features: {missing_features}"
            )
    
    @property
    def _required_features(self) -> Set[str]:
        """Get set of required features."""
        return set(self._metadata.required_features)
    
    def _generate_cache_key(self, features: Dict[str, Any]) -> str:
        """
        Generate a cache key from features.
        
        Args:
            features: Dictionary of features
            
        Returns:
            Cache key string
        """
        features_json = json.dumps(features, sort_keys=True, default=str)
        return hashlib.sha256(features_json.encode()).hexdigest()
    
    def _get_cached_signal(self, cache_key: str) -> Optional[AgentSignal]:
        """
        Retrieve cached signal if valid.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached AgentSignal or None if expired/missing
        """
        if not self._config.enable_cache:
            return None
        
        cached = self._cache.get(cache_key)
        
        if cached is None:
            return None
        
        signal, timestamp = cached
        age = (datetime.now() - timestamp).total_seconds()
        
        if age > self._config.cache_ttl_seconds:
            del self._cache[cache_key]
            return None
        
        logger.debug(f"Cache hit for agent '{self._agent_name}': {cache_key[:8]}...")
        return signal
    
    def _set_cached_signal(self, cache_key: str, signal: AgentSignal) -> None:
        """
        Store signal in cache.
        
        Args:
            cache_key: Cache key
            signal: AgentSignal to cache
        """
        if not self._config.enable_cache:
            return
        
        if len(self._cache) > 1000:
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k][1]
            )
            del self._cache[oldest_key]
        
        self._cache[cache_key] = (signal, datetime.now())
    
    def clear_cache(self) -> None:
        """Clear all cached signals for this agent."""
        self._cache.clear()
        logger.debug(f"Cache cleared for agent '{self._agent_name}'")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._cache)
        expired_entries = 0
        now = datetime.now()
        
        for _, timestamp in self._cache.values():
            age = (now - timestamp).total_seconds()
            if age > self._config.cache_ttl_seconds:
                expired_entries += 1
        
        return {
            "agent_name": self._agent_name,
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "cache_enabled": self._config.enable_cache,
            "cache_ttl_seconds": self._config.cache_ttl_seconds
        }
    
    def _create_error_signal(
        self,
        error_message: str,
        confidence: float = 0.0
    ) -> AgentSignal:
        """
        Create an error signal when execution fails.
        
        Args:
            error_message: Description of the error
            confidence: Confidence level (default 0.0)
            
        Returns:
            AgentSignal with error information
        """
        return AgentSignal(
            agent_name=self._agent_name,
            agent_category=self._agent_category.value,
            signal="hold",
            confidence=confidence,
            numerical_score=0.0,
            reasoning=f"Error: {error_message}",
            supporting_data={"error": True, "message": error_message}
        )
    
    @abstractmethod
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute trading signal from features.
        
        This method must be implemented by all concrete agents.
        
        Args:
            features: Dictionary of market features and indicators
            
        Returns:
            AgentSignal with trading recommendation
            
        Raises:
            AgentExecutionError: If signal computation fails
        """
        pass
    
    def run(
        self,
        features: Dict[str, Any],
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> AgentSignal:
        """
        Execute the agent to generate a trading signal.
        
        This is the main entry point for running the agent. It handles:
        - Input validation
        - Caching
        - Error handling with retries
        
        Args:
            features: Dictionary of market features
            use_cache: Whether to use caching (default True)
            force_refresh: Force cache refresh (default False)
            
        Returns:
            AgentSignal with trading recommendation
            
        Example:
            features = {"price": 150.0, "volume": 1000000, "rsi": 65.0}
            signal = agent.run(features)
            print(f"Signal: {signal.signal}, Confidence: {signal.confidence}")
        """
        cache_key = self._generate_cache_key(features)
        
        if use_cache and not force_refresh:
            cached_signal = self._get_cached_signal(cache_key)
            if cached_signal is not None:
                return cached_signal
        
        self._validate_features(features)
        
        last_error: Optional[Exception] = None
        
        for attempt in range(self._config.max_retries):
            try:
                signal = self.compute_signal(features)
                
                signal.agent_name = self._agent_name
                signal.agent_category = self._agent_category.value
                
                if use_cache and not force_refresh:
                    self._set_cached_signal(cache_key, signal)
                
                logger.debug(
                    f"Agent '{self._agent_name}' generated signal: "
                    f"{signal.signal} (confidence: {signal.confidence})"
                )
                
                return signal
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Agent '{self._agent_name}' attempt {attempt + 1} failed: {e}"
                )
                
                if attempt < self._config.max_retries - 1:
                    import time
                    time.sleep(self._config.retry_delay_seconds * (attempt + 1))
        
        error_msg = f"Failed after {self._config.max_retries} attempts: {last_error}"
        logger.error(f"Agent '{self._agent_name}' execution failed: {error_msg}")
        
        return self._create_error_signal(error_msg)
    
    async def run_async(
        self,
        features: Dict[str, Any],
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> AgentSignal:
        """
        Execute the agent asynchronously to generate a trading signal.
        
        Args:
            features: Dictionary of market features
            use_cache: Whether to use caching
            force_refresh: Force cache refresh
            
        Returns:
            AgentSignal with trading recommendation
        """
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            None,
            self.run,
            features,
            use_cache,
            force_refresh
        )
    
    def run_parallel(
        self,
        features_list: List[Dict[str, Any]]
    ) -> List[AgentSignal]:
        """
        Execute the agent in parallel on multiple feature sets.
        
        Args:
            features_list: List of feature dictionaries
            
        Returns:
            List of AgentSignals
            
        Example:
            features_list = [
                {"price": 150.0, "volume": 1000000},
                {"price": 151.0, "volume": 1100000},
            ]
            signals = agent.run_parallel(features_list)
        """
        if not self._config.enable_parallel:
            return [self.run(features) for features in features_list]
        
        with ThreadPoolExecutor(max_workers=self._config.max_workers) as executor:
            futures = [
                executor.submit(self.run, features)
                for features in features_list
            ]
            
            return [future.result() for future in futures]
    
    async def run_parallel_async(
        self,
        features_list: List[Dict[str, Any]]
    ) -> List[AgentSignal]:
        """
        Execute the agent in parallel asynchronously.
        
        Args:
            features_list: List of feature dictionaries
            
        Returns:
            List of AgentSignals
        """
        tasks = [
            self.run_async(features)
            for features in features_list
        ]
        
        return await asyncio.gather(*tasks)
    
    def run_batch(
        self,
        batch_features: Dict[str, Dict[str, Any]]
    ) -> Dict[str, AgentSignal]:
        """
        Execute the agent on a batch of stocks.
        
        Args:
            batch_features: Dict mapping stock symbols to feature dicts
            
        Returns:
            Dict mapping stock symbols to AgentSignals
            
        Example:
            batch = {
                "AAPL": {"price": 150.0, "volume": 1000000},
                "GOOGL": {"price": 2800.0, "volume": 500000},
            }
            signals = agent.run_batch(batch)
        """
        symbols = list(batch_features.keys())
        features_list = [batch_features[s] for s in symbols]
        
        signals = self.run_parallel(features_list)
        
        return dict(zip(symbols, signals))
    
    async def run_batch_async(
        self,
        batch_features: Dict[str, Dict[str, Any]]
    ) -> Dict[str, AgentSignal]:
        """
        Execute the agent on a batch of stocks asynchronously.
        
        Args:
            batch_features: Dict mapping stock symbols to feature dicts
            
        Returns:
            Dict mapping stock symbols to AgentSignals
        """
        symbols = list(batch_features.keys())
        features_list = [batch_features[s] for s in symbols]
        
        signals = await self.run_parallel_async(features_list)
        
        return dict(zip(symbols, signals))
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about this agent.
        
        Returns:
            Dictionary with agent information
        """
        return {
            "agent_name": self._agent_name,
            "agent_category": self._agent_category.value,
            "version": self._metadata.version,
            "description": self._metadata.description,
            "required_features": self._metadata.required_features,
            "author": self._metadata.author,
            "tags": self._metadata.tags,
            "config": {
                "enable_cache": self._config.enable_cache,
                "cache_ttl_seconds": self._config.cache_ttl_seconds,
                "timeout_seconds": self._config.timeout_seconds,
                "max_retries": self._config.max_retries,
                "enable_parallel": self._config.enable_parallel,
                "max_workers": self._config.max_workers
            },
            "cache_stats": self.get_cache_stats()
        }
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return (
            f"{self.__class__.__name__}("
            f"name='{self._agent_name}', "
            f"category={self._agent_category.value}, "
            f"version='{self._metadata.version}')"
        )
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"Agent: {self._agent_name} "
            f"(v{self._metadata.version}, {self._agent_category.value})"
        )


class AgentRegistry:
    """
    Registry for managing multiple agents.
    
    Provides a centralized way to register, retrieve, and manage
    multiple trading agents.
    """
    
    def __init__(self) -> None:
        """Initialize the agent registry."""
        self._agents: Dict[str, BaseAgent] = {}
        self._logger = logging.getLogger(__name__)
    
    def register(self, agent: BaseAgent) -> None:
        """
        Register an agent.
        
        Args:
            agent: Agent to register
            
        Raises:
            AgentError: If agent name already exists
        """
        if agent.agent_name in self._agents:
            raise AgentError(
                f"Agent '{agent.agent_name}' is already registered"
            )
        
        self._agents[agent.agent_name] = agent
        self._logger.info(f"Registered agent: {agent.agent_name}")
    
    def unregister(self, agent_name: str) -> None:
        """
        Unregister an agent.
        
        Args:
            agent_name: Name of agent to unregister
        """
        if agent_name in self._agents:
            del self._agents[agent_name]
            self._logger.info(f"Unregistered agent: {agent_name}")
    
    def get(self, agent_name: str) -> Optional[BaseAgent]:
        """
        Get an agent by name.
        
        Args:
            agent_name: Name of agent to retrieve
            
        Returns:
            Agent or None if not found
        """
        return self._agents.get(agent_name)
    
    def list_agents(self) -> List[str]:
        """
        List all registered agent names.
        
        Returns:
            List of agent names
        """
        return list(self._agents.keys())
    
    def get_agents_by_category(
        self,
        category: AgentCategory
    ) -> List[BaseAgent]:
        """
        Get all agents of a specific category.
        
        Args:
            category: AgentCategory to filter by
            
        Returns:
            List of agents in that category
        """
        return [
            agent for agent in self._agents.values()
            if agent.agent_category == category
        ]
    
    def get_all_agent_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all registered agents.
        
        Returns:
            List of agent info dictionaries
        """
        return [agent.get_agent_info() for agent in self._agents.values()]
    
    def clear_cache_all(self) -> None:
        """Clear cache for all registered agents."""
        for agent in self._agents.values():
            agent.clear_cache()
        self._logger.info("Cleared cache for all agents")
    
    def __len__(self) -> int:
        """Get number of registered agents."""
        return len(self._agents)
    
    def __contains__(self, agent_name: str) -> bool:
        """Check if agent is registered."""
        return agent_name in self._agents
