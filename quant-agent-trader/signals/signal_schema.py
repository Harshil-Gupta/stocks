"""
Signal Schema - Structured output format for all agents.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import json


class SignalType(Enum):
    """Trading signal types."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class AgentCategory(Enum):
    """Agent category types."""
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    MACRO = "macro"
    MARKET_STRUCTURE = "market_structure"
    RISK = "risk"
    QUANT = "quant"
    META = "meta"


@dataclass
class AgentSignal:
    """
    Standardized output from each agent.
    All agents must produce this structured format.
    """
    agent_name: str
    agent_category: str
    signal: str  # buy, sell, hold
    confidence: float  # 0-100
    numerical_score: float = 0.0  # -1 to 1
    reasoning: str = ""
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "agent_category": self.agent_category,
            "signal": self.signal,
            "confidence": self.confidence,
            "numerical_score": self.numerical_score,
            "reasoning": self.reasoning,
            "supporting_data": self.supporting_data,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentSignal':
        """Create from dictionary."""
        return cls(
            agent_name=data.get("agent_name", ""),
            agent_category=data.get("agent_category", ""),
            signal=data.get("signal", "hold"),
            confidence=data.get("confidence", 50),
            numerical_score=data.get("numerical_score", 0.0),
            reasoning=data.get("reasoning", ""),
            supporting_data=data.get("supporting_data", {}),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
        )
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class AggregatedSignal:
    """
    Aggregated signal from multiple agents.
    """
    stock_symbol: str
    final_score: float  # 0-1
    decision: str  # buy, sell, hold
    confidence: float  # 0-100
    supporting_agents: List[str] = field(default_factory=list)
    conflicting_agents: List[str] = field(default_factory=list)
    agent_signals: List[AgentSignal] = field(default_factory=list)
    regime: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "stock_symbol": self.stock_symbol,
            "final_score": self.final_score,
            "decision": self.decision,
            "confidence": self.confidence,
            "supporting_agents": self.supporting_agents,
            "conflicting_agents": self.conflicting_agents,
            "regime": self.regime,
            "timestamp": self.timestamp.isoformat(),
            "signal_breakdown": {
                cat: [s.to_dict() for s in self.agent_signals if s.agent_category == cat]
                for cat in set(s.agent_category for s in self.agent_signals)
            }
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class PortfolioDecision:
    """
    Final portfolio decision including position sizing.
    """
    stock_symbol: str
    decision: str  # buy, sell, hold
    position_size: float  # 0-1 (percentage of portfolio)
    confidence: float
    risk_level: str  # low, medium, high
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reasoning: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "stock_symbol": self.stock_symbol,
            "decision": self.decision,
            "position_size": self.position_size,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class TradeResult:
    """
    Trade execution result for learning.
    """
    stock_symbol: str
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    pnl_percent: float
    holding_period: int  # days
    decision: str
    agent_signals: List[Dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "stock_symbol": self.stock_symbol,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "position_size": self.position_size,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
            "holding_period": self.holding_period,
            "decision": self.decision,
            "agent_signals": self.agent_signals,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class MarketRegime:
    """Detected market regime."""
    regime_type: str  # bull, bear, sideways, high_volatility
    volatility: float
    trend_strength: float
    liquidity_score: float
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "regime_type": self.regime_type,
            "volatility": self.volatility,
            "trend_strength": self.trend_strength,
            "liquidity_score": self.liquidity_score,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }
