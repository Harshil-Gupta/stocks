"""
Quantitative Agents Package.

This package contains quantitative trading agents:
- MeanReversionAgent: Mean reversion signals
- StatArbAgent: Statistical arbitrage signals
- FactorModelAgent: Factor-based signals
- PairsTradingAgent: Pairs trading signals
"""

from agents.quant.mean_reversion_agent import MeanReversionAgent
from agents.quant.stat_arb_agent import StatArbAgent
from agents.quant.factor_model_agent import FactorModelAgent
from agents.quant.pairs_trading_agent import PairsTradingAgent

__all__ = [
    "MeanReversionAgent",
    "StatArbAgent",
    "FactorModelAgent",
    "PairsTradingAgent",
]
