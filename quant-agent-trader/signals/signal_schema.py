"""
Signal Schema - Structured output format for all agents.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import json


class SignalType(Enum):
    """Trading signal types with 5-level classification."""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

    @property
    def direction(self) -> int:
        """Convert signal to position direction (-2 to +2)."""
        mapping = {
            SignalType.STRONG_BUY: 2,
            SignalType.BUY: 1,
            SignalType.HOLD: 0,
            SignalType.SELL: -1,
            SignalType.STRONG_SELL: -2,
        }
        return mapping.get(self, 0)

    @staticmethod
    def from_string(value: str) -> "SignalType":
        """Create SignalType from string."""
        value = value.lower().strip()
        mapping = {
            "strong_buy": SignalType.STRONG_BUY,
            "buy": SignalType.BUY,
            "hold": SignalType.HOLD,
            "sell": SignalType.SELL,
            "strong_sell": SignalType.STRONG_SELL,
        }
        return mapping.get(value, SignalType.HOLD)

    @staticmethod
    def from_score(score: float) -> "SignalType":
        """Create SignalType from numerical score (0-100 scale).

        Thresholds:
        - >= 85: STRONG_BUY
        - 60 to 85: BUY
        - 40 to 60: HOLD
        - 25 to 40: SELL
        - < 25: STRONG_SELL

        Boundary values (like 25, 40, 60, 85) choose lower signal.
        """
        if score >= 85:
            return SignalType.STRONG_BUY
        elif score >= 60:
            return SignalType.BUY
        elif score >= 40:
            return SignalType.HOLD
        elif score >= 25:
            return SignalType.SELL
        else:
            return SignalType.STRONG_SELL

    @staticmethod
    def from_score_normalized(score: float) -> "SignalType":
        """Create SignalType from normalized score (-1 to 1).

        Converts -1 to 1 scale to 0-100 then applies thresholds.
        """
        # Normalize from [-1, 1] to [0, 100]
        normalized = (score + 1) * 50
        return SignalType.from_score(normalized)


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


VALID_SIGNALS = {"strong_buy", "buy", "hold", "sell", "strong_sell"}


@dataclass
class AgentSignal:
    """
    Standardized output from each agent.
    All agents must produce this structured format.
    Supports 5-class signals: strong_buy, buy, hold, sell, strong_sell
    """

    agent_name: str
    agent_category: str
    signal: str  # strong_buy, buy, hold, sell, strong_sell
    confidence: float  # 0-100
    numerical_score: float = 0.0  # -1 to 1
    reasoning: str = ""
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate and normalize signal value."""
        self.signal = self.signal.lower().strip()
        if self.signal not in VALID_SIGNALS:
            self.signal = "hold"

    @property
    def signal_type(self) -> SignalType:
        """Get SignalType enum from signal string."""
        return SignalType.from_string(self.signal)

    @property
    def direction(self) -> int:
        """Get numeric direction (-2 to +2) from signal."""
        return self.signal_type.direction

    @property
    def is_buy(self) -> bool:
        """Check if signal is bullish."""
        return self.signal in ("strong_buy", "buy")

    @property
    def is_sell(self) -> bool:
        """Check if signal is bearish."""
        return self.signal in ("sell", "strong_sell")

    @property
    def is_strong(self) -> bool:
        """Check if signal is strong (strong_buy or strong_sell)."""
        return self.signal in ("strong_buy", "strong_sell")

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "agent_category": self.agent_category,
            "signal": self.signal,
            "signal_type": self.signal_type.value,
            "direction": self.direction,
            "confidence": self.confidence,
            "numerical_score": self.numerical_score,
            "reasoning": self.reasoning,
            "supporting_data": self.supporting_data,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AgentSignal":
        """Create from dictionary."""
        return cls(
            agent_name=data.get("agent_name", ""),
            agent_category=data.get("agent_category", ""),
            signal=data.get("signal", "hold"),
            confidence=data.get("confidence", 50),
            numerical_score=data.get("numerical_score", 0.0),
            reasoning=data.get("reasoning", ""),
            supporting_data=data.get("supporting_data", {}),
            timestamp=datetime.fromisoformat(
                data.get("timestamp", datetime.now().isoformat())
            ),
        )

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class AggregatedSignal:
    """
    Aggregated signal from multiple agents.
    Supports 5-class output: strong_buy, buy, hold, sell, strong_sell
    """

    stock_symbol: str
    final_score: float  # -1 to 1
    decision: str  # strong_buy, buy, hold, sell, strong_sell
    confidence: float  # 0-100
    supporting_agents: List[str] = field(default_factory=list)
    conflicting_agents: List[str] = field(default_factory=list)
    agent_signals: List[AgentSignal] = field(default_factory=list)
    regime: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate and normalize decision value."""
        self.decision = self.decision.lower().strip()
        if self.decision not in VALID_SIGNALS:
            self.decision = "hold"

    @property
    def signal_type(self) -> SignalType:
        """Get SignalType enum from decision string."""
        return SignalType.from_string(self.decision)

    @property
    def direction(self) -> int:
        """Get numeric direction (-2 to +2)."""
        return self.signal_type.direction

    @property
    def is_buy(self) -> bool:
        """Check if decision is bullish."""
        return self.decision in ("strong_buy", "buy")

    @property
    def is_sell(self) -> bool:
        """Check if decision is bearish."""
        return self.decision in ("sell", "strong_sell")

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "stock_symbol": self.stock_symbol,
            "final_score": self.final_score,
            "decision": self.decision,
            "decision_type": self.signal_type.value,
            "direction": self.direction,
            "confidence": self.confidence,
            "supporting_agents": self.supporting_agents,
            "conflicting_agents": self.conflicting_agents,
            "regime": self.regime,
            "timestamp": self.timestamp.isoformat(),
            "signal_breakdown": {
                cat: [
                    s.to_dict() for s in self.agent_signals if s.agent_category == cat
                ]
                for cat in set(s.agent_category for s in self.agent_signals)
            },
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class PortfolioDecision:
    """
    Final portfolio decision including position sizing.
    Supports 5-class signals.
    """

    stock_symbol: str
    decision: str  # strong_buy, buy, hold, sell, strong_sell
    position_size: float  # 0-1 (percentage of portfolio)
    confidence: float
    risk_level: str  # low, medium, high
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reasoning: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate and normalize decision value."""
        self.decision = self.decision.lower().strip()
        if self.decision not in VALID_SIGNALS:
            self.decision = "hold"

    @property
    def direction(self) -> int:
        """Get numeric direction (-2 to +2)."""
        return SignalType.from_string(self.decision).direction

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "stock_symbol": self.stock_symbol,
            "decision": self.decision,
            "direction": self.direction,
            "position_size": self.position_size,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
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
    decision: str  # strong_buy, buy, hold, sell, strong_sell
    agent_signals: List[Dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate and normalize decision value."""
        self.decision = self.decision.lower().strip()
        if self.decision not in VALID_SIGNALS:
            self.decision = "hold"

    @property
    def direction(self) -> int:
        """Get numeric direction (-2 to +2)."""
        return SignalType.from_string(self.decision).direction

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
            "direction": self.direction,
            "agent_signals": self.agent_signals,
            "timestamp": self.timestamp.isoformat(),
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
            "timestamp": self.timestamp.isoformat(),
        }
