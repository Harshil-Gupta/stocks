"""
Agents package - Trading agents for quantitative analysis.
"""

# Technical agents
from agents.technical.rsi_agent import RSIAgent
from agents.technical.macd_agent import MACDAgent
from agents.technical.momentum_agent import MomentumAgent
from agents.technical.trend_agent import TrendAgent
from agents.technical.breakout_agent import BreakoutAgent
from agents.technical.volume_agent import VolumeAgent

# Fundamental agents
from agents.fundamental.valuation_agent import ValuationAgent
from agents.fundamental.earnings_agent import EarningsAgent
from agents.fundamental.cashflow_agent import CashflowAgent
from agents.fundamental.growth_agent import GrowthAgent

# Sentiment agents
from agents.sentiment.news_sentiment_agent import NewsSentimentAgent
from agents.sentiment.analyst_rating_agent import AnalystRatingAgent

# Risk agents
from agents.risk.volatility_regime_agent import VolatilityRegimeAgent
from agents.risk.tail_risk_agent import TailRiskAgent

# Core
from agents.agent_dispatcher import AgentDispatcher, create_default_dispatcher
from agents.regime_classifier import RegimeClassifier, create_regime_classifier

__all__ = [
    # Technical
    "RSIAgent", "MACDAgent", "MomentumAgent", "TrendAgent", "BreakoutAgent", "VolumeAgent",
    # Fundamental
    "ValuationAgent", "EarningsAgent", "CashflowAgent", "GrowthAgent",
    # Sentiment
    "NewsSentimentAgent", "AnalystRatingAgent",
    # Risk
    "VolatilityRegimeAgent", "TailRiskAgent",
    # Core
    "AgentDispatcher", "create_default_dispatcher",
    "RegimeClassifier", "create_regime_classifier",
]
