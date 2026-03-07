"""
Orchestration Module - Agent Dispatcher and Orchestration System.

This module provides:
- AgentDispatcher: Main class for parallel agent execution
- DispatcherBuilder: Builder for creating configured dispatchers
- DispatchResult, BatchDispatchResult: Result types for dispatch operations
- DispatcherConfig: Configuration for dispatcher behavior
"""

from orchestration.dispatcher import (
    AgentDispatcher,
    BatchDispatchResult,
    DispatcherBuilder,
    DispatcherConfig,
    DispatchResult,
    ExecutionBackend,
)

# AgentRegistry is imported from agents.base_agent
from agents.base_agent import AgentRegistry

__all__ = [
    "AgentDispatcher",
    "AgentRegistry",
    "BatchDispatchResult",
    "DispatcherBuilder",
    "DispatcherConfig",
    "DispatchResult",
    "ExecutionBackend",
]
