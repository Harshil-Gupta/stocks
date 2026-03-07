"""
Agent Dispatcher / Orchestration System for Parallel Agent Execution.

This module provides the AgentDispatcher class for managing and executing
multiple agents in parallel using Ray (if available) or asyncio.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    TypeVar,
    Union,
)

import numpy as np

from signals.signal_schema import AgentCategory, AgentSignal
from agents.base_agent import AgentRegistry, BaseAgent, AgentError, AgentConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ExecutionBackend(Enum):
    """Execution backend types."""
    RAY = "ray"
    ASYNCIO = "asyncio"
    THREADPOOL = "threadpool"


@dataclass
class DispatchResult:
    """Result of agent dispatch operation."""
    agent_name: str
    success: bool
    signal: Optional[AgentSignal] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "agent_name": self.agent_name,
            "success": self.success,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.signal:
            result["signal"] = self.signal.to_dict()
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class BatchDispatchResult:
    """Result of batch dispatch operation."""
    symbol: str
    dispatch_results: List[DispatchResult]
    aggregated_signal: Optional[AgentSignal] = None
    total_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def success_count(self) -> int:
        """Count of successful agent executions."""
        return sum(1 for r in self.dispatch_results if r.success)
    
    @property
    def failure_count(self) -> int:
        """Count of failed agent executions."""
        return len(self.dispatch_results) - self.success_count
    
    @property
    def all_success(self) -> bool:
        """Check if all agents succeeded."""
        return self.failure_count == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_time_ms": self.total_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "dispatch_results": [r.to_dict() for r in self.dispatch_results],
            "aggregated_signal": self.aggregated_signal.to_dict() if self.aggregated_signal else None,
        }


@dataclass
class DispatcherConfig:
    """Configuration for agent dispatcher."""
    max_workers: int = 8
    timeout_seconds: float = 30.0
    enable_ray: bool = True
    ray_address: Optional[str] = None
    enable_retry: bool = True
    max_retries: int = 2
    retry_delay_seconds: float = 0.5
    aggregation_method: str = "weighted_average"
    default_confidence_threshold: float = 50.0
    log_execution_time: bool = True


class RayClient:
    """Mock Ray client for when Ray is not available."""
    
    def __init__(self, address: Optional[str] = None):
        self._available = False
        self._address = address
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def remote(self, func: Callable) -> Callable:
        """Mock remote decorator."""
        return func
    
    def get(self, futures: List[Any]) -> List[Any]:
        """Mock get method."""
        return futures
    
    def shutdown(self) -> None:
        """Mock shutdown method."""
        pass


def _get_ray_client(address: Optional[str] = None) -> Union["RayClient", Any]:
    """
    Get Ray client if available.
    
    Args:
        address: Ray cluster address
        
    Returns:
        RayClient instance
    """
    try:
        import ray
        ray.init(address=address, ignore_reinit_error=True)
        logger.info("Ray initialized successfully")
        return ray
    except ImportError:
        logger.warning("Ray not available, falling back to asyncio/threadpool")
        return RayClient(address=address)
    except Exception as e:
        logger.warning(f"Failed to initialize Ray: {e}, falling back to asyncio/threadpool")
        return RayClient(address=address)


class AgentDispatcher:
    """
    Dispatcher for parallel agent execution.
    
    Manages lifecycle of multiple agents and executes them in parallel
    using Ray (if available) or asyncio/threadpool.
    
    Attributes:
        config: DispatcherConfig for execution settings
        registry: AgentRegistry for managing agents
        
    Example:
        dispatcher = AgentDispatcher(config=DispatcherConfig(max_workers=8))
        
        # Register agents
        dispatcher.register_agent(rsi_agent)
        dispatcher.register_agent(macd_agent)
        
        # Dispatch multiple agents
        results = dispatcher.dispatch_agents(
            agents=[rsi_agent, macd_agent],
            market_data={"AAPL": {"price": 150.0, "rsi": 65.0}}
        )
    """
    
    def __init__(
        self,
        config: Optional[DispatcherConfig] = None,
        registry: Optional[AgentRegistry] = None,
    ) -> None:
        """
        Initialize the agent dispatcher.
        
        Args:
            config: Optional dispatcher configuration
            registry: Optional agent registry
        """
        self._config = config or DispatcherConfig()
        self._registry = registry or AgentRegistry()
        self._ray_client: Union[RayClient, Any] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._execution_backend: ExecutionBackend = ExecutionBackend.ASYNCIO
        
        self._initialize_backend()
        self._active_agents: Dict[str, BaseAgent] = {}
        
        logger.info(
            f"AgentDispatcher initialized with backend: {self._execution_backend.value}"
        )
    
    def _initialize_backend(self) -> None:
        """Initialize the execution backend."""
        if self._config.enable_ray:
            self._ray_client = _get_ray_client(self._config.ray_address)
            if hasattr(self._ray_client, "is_available") and self._ray_client.is_available:
                self._execution_backend = ExecutionBackend.RAY
                logger.info("Using Ray backend for distributed execution")
                return
        
        self._execution_backend = ExecutionBackend.THREADPOOL
        self._executor = ThreadPoolExecutor(max_workers=self._config.max_workers)
        logger.info(f"Using ThreadPoolExecutor with {self._config.max_workers} workers")
    
    @property
    def config(self) -> DispatcherConfig:
        """Get dispatcher configuration."""
        return self._config
    
    @property
    def registry(self) -> AgentRegistry:
        """Get agent registry."""
        return self._registry
    
    @property
    def execution_backend(self) -> ExecutionBackend:
        """Get execution backend type."""
        return self._execution_backend
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the dispatcher.
        
        Args:
            agent: Agent to register
        """
        self._registry.register(agent)
        self._active_agents[agent.agent_name] = agent
        logger.debug(f"Registered agent: {agent.agent_name}")
    
    def register_agents(self, agents: List[BaseAgent]) -> None:
        """
        Register multiple agents.
        
        Args:
            agents: List of agents to register
        """
        for agent in agents:
            self.register_agent(agent)
    
    def unregister_agent(self, agent_name: str) -> None:
        """
        Unregister an agent.
        
        Args:
            agent_name: Name of agent to unregister
        """
        self._registry.unregister(agent_name)
        if agent_name in self._active_agents:
            del self._active_agents[agent_name]
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """
        Get an agent by name.
        
        Args:
            agent_name: Name of agent to retrieve
            
        Returns:
            Agent or None if not found
        """
        return self._registry.get(agent_name)
    
    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return self._registry.list_agents()
    
    def _execute_agent(
        self,
        agent: BaseAgent,
        features: Dict[str, Any],
        use_cache: bool = True,
    ) -> DispatchResult:
        """
        Execute a single agent with error handling.
        
        Args:
            agent: Agent to execute
            features: Features for signal computation
            use_cache: Whether to use caching
            
        Returns:
            DispatchResult with execution details
        """
        start_time = time.perf_counter()
        agent_name = agent.agent_name
        
        try:
            signal = agent.run(features, use_cache=use_cache)
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return DispatchResult(
                agent_name=agent_name,
                success=True,
                signal=signal,
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"Agent '{agent_name}' execution failed: {error_msg}")
            
            return DispatchResult(
                agent_name=agent_name,
                success=False,
                error=error_msg,
                execution_time_ms=execution_time,
            )
    
    async def _execute_agent_async(
        self,
        agent: BaseAgent,
        features: Dict[str, Any],
        use_cache: bool = True,
    ) -> DispatchResult:
        """
        Execute a single agent asynchronously.
        
        Args:
            agent: Agent to execute
            features: Features for signal computation
            use_cache: Whether to use caching
            
        Returns:
            DispatchResult with execution details
        """
        loop = asyncio.get_event_loop()
        
        result = await loop.run_in_executor(
            None,
            self._execute_agent,
            agent,
            features,
            use_cache,
        )
        
        return result
    
    def _aggregate_signals(
        self,
        dispatch_results: List[DispatchResult],
        method: str = "weighted_average",
    ) -> Optional[AgentSignal]:
        """
        Aggregate signals from multiple agents.
        
        Args:
            dispatch_results: List of dispatch results
            method: Aggregation method
            
        Returns:
            Aggregated AgentSignal or None
        """
        successful_results = [r for r in dispatch_results if r.success and r.signal]
        
        if not successful_results:
            return None
        
        if len(successful_results) == 1:
            return successful_results[0].signal
        
        total_confidence = 0.0
        weighted_score = 0.0
        signal_votes: Dict[str, float] = {"buy": 0.0, "sell": 0.0, "hold": 0.0}
        
        for result in successful_results:
            signal = result.signal
            if signal is None:
                continue
            confidence = signal.confidence
            
            total_confidence += confidence
            weighted_score += signal.numerical_score * confidence
            signal_votes[signal.signal] += confidence
        
        if total_confidence > 0:
            final_score = weighted_score / total_confidence
            avg_confidence = total_confidence / len(successful_results)
        else:
            final_score = 0.0
            avg_confidence = 0.0
        
        # Get the decision with highest votes, with fallback
        if signal_votes:
            decision = max(signal_votes, key=signal_votes.get)  # type: ignore
        else:
            decision = "hold"
        
        return AgentSignal(
            agent_name="aggregated",
            agent_category="meta",
            signal=decision,
            confidence=avg_confidence,
            numerical_score=final_score,
            reasoning=f"Aggregated {len(successful_results)} agents using {method}",
            supporting_data={
                "method": method,
                "agent_count": len(successful_results),
                "signal_votes": signal_votes,
            },
        )
    
    def dispatch_agents(
        self,
        agents: Union[List[BaseAgent], List[str]],
        market_data: Dict[str, Dict[str, Any]],
        use_cache: bool = True,
        aggregate: bool = True,
    ) -> Dict[str, List[DispatchResult]]:
        """
        Dispatch multiple agents to run in parallel.
        
        Args:
            agents: List of agents or agent names to dispatch
            market_data: Dict mapping symbols to feature dicts
            use_cache: Whether to use caching
            aggregate: Whether to aggregate results
            
        Returns:
            Dict mapping symbols to list of DispatchResults
            
        Example:
            results = dispatcher.dispatch_agents(
                agents=[rsi_agent, macd_agent],
                market_data={
                    "AAPL": {"price": 150.0, "rsi": 65.0},
                    "GOOGL": {"price": 2800.0, "rsi": 45.0}
                }
            )
        """
        resolved_agents = self._resolve_agents(agents)
        
        if not resolved_agents:
            logger.warning("No valid agents to dispatch")
            return {}
        
        results: Dict[str, List[DispatchResult]] = {}
        
        for symbol, features in market_data.items():
            dispatch_results: List[DispatchResult] = []
            
            if self._execution_backend == ExecutionBackend.RAY:
                dispatch_results = self._dispatch_ray(resolved_agents, features, use_cache)
            else:
                dispatch_results = self._dispatch_threadpool(resolved_agents, features, use_cache)
            
            if aggregate and dispatch_results:
                aggregated = self._aggregate_signals(dispatch_results)
                if aggregated:
                    dispatch_results.append(DispatchResult(
                        agent_name="aggregated",
                        success=True,
                        signal=aggregated,
                    ))
            
            results[symbol] = dispatch_results
        
        return results
    
    def _resolve_agents(
        self,
        agents: Union[List[BaseAgent], List[str]]
    ) -> List[BaseAgent]:
        """Resolve agent names to agent instances."""
        resolved = []
        
        for agent in agents:
            if isinstance(agent, str):
                retrieved = self._registry.get(agent)
                if retrieved:
                    resolved.append(retrieved)
                else:
                    logger.warning(f"Agent '{agent}' not found in registry")
            elif isinstance(agent, BaseAgent):
                resolved.append(agent)
        
        return resolved
    
    def _dispatch_ray(
        self,
        agents: List[BaseAgent],
        features: Dict[str, Any],
        use_cache: bool,
    ) -> List[DispatchResult]:
        """Dispatch agents using Ray."""
        if not hasattr(self._ray_client, "remote"):
            return self._dispatch_threadpool(agents, features, use_cache)
        
        try:
            remote_funcs = [
                self._ray_client.remote(self._execute_agent)(agent, features, use_cache)
                for agent in agents
            ]
            
            ray_results = self._ray_client.get(remote_funcs)
            return list(ray_results)
            
        except Exception as e:
            logger.warning(f"Ray execution failed: {e}, falling back to threadpool")
            return self._dispatch_threadpool(agents, features, use_cache)
    
    def _dispatch_threadpool(
        self,
        agents: List[BaseAgent],
        features: Dict[str, Any],
        use_cache: bool,
    ) -> List[DispatchResult]:
        """Dispatch agents using ThreadPoolExecutor."""
        results: List[DispatchResult] = []
        
        with ThreadPoolExecutor(max_workers=self._config.max_workers) as executor:
            futures = {
                executor.submit(
                    self._execute_agent,
                    agent,
                    features,
                    use_cache,
                ): agent
                for agent in agents
            }
            
            agent_results: Dict[str, DispatchResult] = {}
            
            for future in as_completed(futures):
                agent = futures[future]
                try:
                    result = future.result(timeout=self._config.timeout_seconds)
                    agent_results[agent.agent_name] = result
                except Exception as e:
                    logger.error(f"Future execution error for {agent.agent_name}: {e}")
                    agent_results[agent.agent_name] = DispatchResult(
                        agent_name=agent.agent_name,
                        success=False,
                        error=str(e),
                    )
            
            for agent in agents:
                result = agent_results.get(agent.agent_name)
                if result is not None:
                    results.append(result)
        
        return results
    
    async def dispatch_agents_async(
        self,
        agents: Union[List[BaseAgent], List[str]],
        market_data: Dict[str, Dict[str, Any]],
        use_cache: bool = True,
        aggregate: bool = True,
    ) -> Dict[str, List[DispatchResult]]:
        """
        Dispatch multiple agents to run in parallel asynchronously.
        
        Args:
            agents: List of agents or agent names to dispatch
            market_data: Dict mapping symbols to feature dicts
            use_cache: Whether to use caching
            aggregate: Whether to aggregate results
            
        Returns:
            Dict mapping symbols to list of DispatchResults
        """
        resolved_agents = self._resolve_agents(agents)
        
        if not resolved_agents:
            logger.warning("No valid agents to dispatch")
            return {}
        
        results: Dict[str, List[DispatchResult]] = {}
        
        tasks = []
        symbols = list(market_data.keys())
        
        for symbol in symbols:
            features = market_data[symbol]
            for agent in resolved_agents:
                tasks.append(
                    self._execute_agent_async(agent, features, use_cache)
                )
        
        dispatch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        idx = 0
        for symbol in symbols:
            symbol_results: List[DispatchResult] = []
            
            for _ in resolved_agents:
                result = dispatch_results[idx]
                idx += 1
                
                if isinstance(result, Exception):
                    symbol_results.append(DispatchResult(
                        agent_name="unknown",
                        success=False,
                        error=str(result),
                    ))
                elif isinstance(result, DispatchResult):
                    symbol_results.append(result)
                else:
                    # Handle unexpected result types
                    symbol_results.append(DispatchResult(
                        agent_name="unknown",
                        success=False,
                        error=f"Unexpected result type: {type(result)}",
                    ))
            
            if aggregate and symbol_results:
                aggregated = self._aggregate_signals(symbol_results)
                if aggregated:
                    symbol_results.append(DispatchResult(
                        agent_name="aggregated",
                        success=True,
                        signal=aggregated,
                    ))
            
            results[symbol] = symbol_results
        
        return results
    
    def dispatch_category(
        self,
        category: AgentCategory,
        market_data: Dict[str, Dict[str, Any]],
        use_cache: bool = True,
        aggregate: bool = True,
    ) -> Dict[str, List[DispatchResult]]:
        """
        Dispatch all agents of a specific category.
        
        Args:
            category: AgentCategory to filter by
            market_data: Dict mapping symbols to feature dicts
            use_cache: Whether to use caching
            aggregate: Whether to aggregate results
            
        Returns:
            Dict mapping symbols to list of DispatchResults
            
        Example:
            results = dispatcher.dispatch_category(
                category=AgentCategory.TECHNICAL,
                market_data={"AAPL": {"price": 150.0}}
            )
        """
        agents = self._registry.get_agents_by_category(category)
        
        if not agents:
            logger.warning(f"No agents found for category: {category.value}")
            return {}
        
        logger.info(f"Dispatching {len(agents)} agents for category: {category.value}")
        
        return self.dispatch_agents(
            agents=agents,
            market_data=market_data,
            use_cache=use_cache,
            aggregate=aggregate,
        )
    
    async def dispatch_category_async(
        self,
        category: AgentCategory,
        market_data: Dict[str, Dict[str, Any]],
        use_cache: bool = True,
        aggregate: bool = True,
    ) -> Dict[str, List[DispatchResult]]:
        """
        Dispatch all agents of a specific category asynchronously.
        
        Args:
            category: AgentCategory to filter by
            market_data: Dict mapping symbols to feature dicts
            use_cache: Whether to use caching
            aggregate: Whether to aggregate results
            
        Returns:
            Dict mapping symbols to list of DispatchResults
        """
        agents = self._registry.get_agents_by_category(category)
        
        if not agents:
            logger.warning(f"No agents found for category: {category.value}")
            return {}
        
        return await self.dispatch_agents_async(
            agents=agents,
            market_data=market_data,
            use_cache=use_cache,
            aggregate=aggregate,
        )
    
    def dispatch_batch(
        self,
        symbols: List[str],
        agents: Union[List[BaseAgent], List[str]],
        market_data: Dict[str, Dict[str, Any]],
        use_cache: bool = True,
    ) -> Dict[str, BatchDispatchResult]:
        """
        Run agents for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            agents: List of agents or agent names
            market_data: Dict mapping symbols to feature dicts
            use_cache: Whether to use caching
            
        Returns:
            Dict mapping symbols to BatchDispatchResult
            
        Example:
            results = dispatcher.dispatch_batch(
                symbols=["AAPL", "GOOGL", "MSFT"],
                agents=[rsi_agent, macd_agent],
                market_data={
                    "AAPL": {"price": 150.0},
                    "GOOGL": {"price": 2800.0},
                    "MSFT": {"price": 300.0}
                }
            )
        """
        results: Dict[str, BatchDispatchResult] = {}
        
        symbol_market_data = {s: market_data.get(s, {}) for s in symbols}
        
        dispatch_results = self.dispatch_agents(
            agents=agents,
            market_data=symbol_market_data,
            use_cache=use_cache,
            aggregate=True,
        )
        
        for symbol in symbols:
            symbol_results = dispatch_results.get(symbol, [])
            aggregated = None
            
            for result in symbol_results:
                if result.agent_name == "aggregated" and result.signal:
                    aggregated = result.signal
                    break
            
            batch_result = BatchDispatchResult(
                symbol=symbol,
                dispatch_results=[
                    r for r in symbol_results
                    if r.agent_name != "aggregated"
                ],
                aggregated_signal=aggregated,
            )
            
            results[symbol] = batch_result
        
        return results
    
    async def dispatch_batch_async(
        self,
        symbols: List[str],
        agents: Union[List[BaseAgent], List[str]],
        market_data: Dict[str, Dict[str, Any]],
        use_cache: bool = True,
    ) -> Dict[str, BatchDispatchResult]:
        """
        Run agents for multiple stocks asynchronously.
        
        Args:
            symbols: List of stock symbols
            agents: List of agents or agent names
            market_data: Dict mapping symbols to feature dicts
            use_cache: Whether to use caching
            
        Returns:
            Dict mapping symbols to BatchDispatchResult
        """
        results: Dict[str, BatchDispatchResult] = {}
        
        symbol_market_data = {s: market_data.get(s, {}) for s in symbols}
        
        dispatch_results = await self.dispatch_agents_async(
            agents=agents,
            market_data=symbol_market_data,
            use_cache=use_cache,
            aggregate=True,
        )
        
        for symbol in symbols:
            symbol_results = dispatch_results.get(symbol, [])
            aggregated = None
            
            for result in symbol_results:
                if result.agent_name == "aggregated" and result.signal:
                    aggregated = result.signal
                    break
            
            batch_result = BatchDispatchResult(
                symbol=symbol,
                dispatch_results=[
                    r for r in symbol_results
                    if r.agent_name != "aggregated"
                ],
                aggregated_signal=aggregated,
            )
            
            results[symbol] = batch_result
        
        return results
    
    def dispatch_all(
        self,
        market_data: Dict[str, Dict[str, Any]],
        use_cache: bool = True,
        aggregate: bool = True,
    ) -> Dict[str, List[DispatchResult]]:
        """
        Dispatch all registered agents.
        
        Args:
            market_data: Dict mapping symbols to feature dicts
            use_cache: Whether to use caching
            aggregate: Whether to aggregate results
            
        Returns:
            Dict mapping symbols to list of DispatchResults
        """
        all_agents = list(self._registry.list_agents())
        
        if not all_agents:
            logger.warning("No agents registered")
            return {}
        
        return self.dispatch_agents(
            agents=all_agents,
            market_data=market_data,
            use_cache=use_cache,
            aggregate=aggregate,
        )
    
    async def dispatch_all_async(
        self,
        market_data: Dict[str, Dict[str, Any]],
        use_cache: bool = True,
        aggregate: bool = True,
    ) -> Dict[str, List[DispatchResult]]:
        """
        Dispatch all registered agents asynchronously.
        
        Args:
            market_data: Dict mapping symbols to feature dicts
            use_cache: Whether to use caching
            aggregate: Whether to aggregate results
            
        Returns:
            Dict mapping symbols to list of DispatchResults
        """
        all_agents = list(self._registry.list_agents())
        
        if not all_agents:
            logger.warning("No agents registered")
            return {}
        
        return await self.dispatch_agents_async(
            agents=all_agents,
            market_data=market_data,
            use_cache=use_cache,
            aggregate=aggregate,
        )
    
    def get_dispatcher_info(self) -> Dict[str, Any]:
        """
        Get comprehensive dispatcher information.
        
        Returns:
            Dictionary with dispatcher information
        """
        return {
            "execution_backend": self._execution_backend.value,
            "max_workers": self._config.max_workers,
            "timeout_seconds": self._config.timeout_seconds,
            "ray_enabled": self._config.enable_ray,
            "registered_agents": len(self._registry),
            "agent_names": self._registry.list_agents(),
            "categories": {
                cat.value: len(self._registry.get_agents_by_category(cat))
                for cat in AgentCategory
            },
        }
    
    def clear_cache_all(self) -> None:
        """Clear cache for all registered agents."""
        self._registry.clear_cache_all()
        logger.info("Cleared cache for all agents")
    
    def shutdown(self) -> None:
        """Shutdown the dispatcher and cleanup resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
        
        if hasattr(self._ray_client, "shutdown"):
            try:
                self._ray_client.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down Ray: {e}")
        
        logger.info("AgentDispatcher shutdown complete")
    
    def __enter__(self) -> "AgentDispatcher":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.shutdown()
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"AgentDispatcher("
            f"backend={self._execution_backend.value}, "
            f"agents={len(self._registry)})"
        )


class DispatcherBuilder:
    """
    Builder class for creating configured AgentDispatcher instances.
    
    Example:
        dispatcher = (
            DispatcherBuilder()
            .with_max_workers(16)
            .with_ray(enabled=True)
            .with_registry(registry)
            .build()
        )
    """
    
    def __init__(self) -> None:
        """Initialize the builder."""
        self._config = DispatcherConfig()
        self._registry: Optional[AgentRegistry] = None
    
    def with_max_workers(self, max_workers: int) -> "DispatcherBuilder":
        """Set maximum worker threads."""
        self._config.max_workers = max_workers
        return self
    
    def with_timeout(self, timeout_seconds: float) -> "DispatcherBuilder":
        """Set execution timeout."""
        self._config.timeout_seconds = timeout_seconds
        return self
    
    def with_ray(self, enabled: bool = True, address: Optional[str] = None) -> "DispatcherBuilder":
        """Configure Ray execution."""
        self._config.enable_ray = enabled
        self._config.ray_address = address
        return self
    
    def with_retry(self, enabled: bool = True, max_retries: int = 2) -> "DispatcherBuilder":
        """Configure retry behavior."""
        self._config.enable_retry = enabled
        self._config.max_retries = max_retries
        return self
    
    def with_aggregation_method(self, method: str) -> "DispatcherBuilder":
        """Set signal aggregation method."""
        self._config.aggregation_method = method
        return self
    
    def with_registry(self, registry: AgentRegistry) -> "DispatcherBuilder":
        """Set agent registry."""
        self._registry = registry
        return self
    
    def build(self) -> AgentDispatcher:
        """Build the AgentDispatcher instance."""
        return AgentDispatcher(
            config=self._config,
            registry=self._registry,
        )
