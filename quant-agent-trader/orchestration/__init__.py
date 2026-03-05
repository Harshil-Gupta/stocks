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
    AgentRegistry,
    BatchDispatchResult,
    DispatcherBuilder,
    DispatcherConfig,
    DispatchResult,
    ExecutionBackend,
)

__all__ = [
    "AgentDispatcher",
    "AgentRegistry",
    "BatchDispatchResult",
    "DispatcherBuilder",
    "DispatcherConfig",
    "DispatchResult",
    "ExecutionBackend",
]
