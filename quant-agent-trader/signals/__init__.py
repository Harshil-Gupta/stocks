"""
Signals Module - Signal schemas and aggregation.

This module provides:
- AgentSignal: Standardized output from each agent
- AggregatedSignal: Aggregated signal from multiple agents
- PortfolioDecision: Final portfolio decision including position sizing
- TradeResult: Trade execution result for learning
- MarketRegime: Detected market regime
- SignalAggregator: Multi-agent signal aggregation system
- SignalType, AgentCategory: Enums for signal types and categories
"""

from signals.signal_schema import (
    AgentSignal,
    AggregatedSignal,
    PortfolioDecision,
    TradeResult,
    MarketRegime,
    SignalType,
    AgentCategory,
)
from signals.signal_aggregator import SignalAggregator, aggregate_signals

__all__ = [
    # Schemas
    "AgentSignal",
    "AggregatedSignal", 
    "PortfolioDecision",
    "TradeResult",
    "MarketRegime",
    # Enums
    "SignalType",
    "AgentCategory",
    # Aggregator
    "SignalAggregator",
    "aggregate_signals",
]
