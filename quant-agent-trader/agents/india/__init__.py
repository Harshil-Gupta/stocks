"""
India-Specific Trading Agents

Agents specialized for Indian stock market analysis:
- India VIX volatility analysis
- F&O (Futures & Options) analysis
- NIFTY market breadth and sentiment
"""

from agents.india.india_vix_agent import IndiaVIXAgent
from agents.india.fno_agent import FNOAgent
from agents.india.nifty_sentiment_agent import NiftySentimentAgent

__all__ = [
    "IndiaVIXAgent",
    "FNOAgent",
    "NiftySentimentAgent",
]
