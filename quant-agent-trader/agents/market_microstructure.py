"""
Market Microstructure Signals - Short-term alpha generators.

These signals capture short-term market dynamics:
- Order book imbalance
- Bid-ask spread dynamics
- Volume profile
- VWAP deviation
- Price impact
- Market depth

Usage:
    from agents.market_microstructure import OrderBookAgent, VolumeProfileAgent
    
    agent = OrderBookAgent()
    signal = agent.run(order_book_data)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import numpy as np
import logging

from agents.base_agent import BaseAgent, AgentConfig, AgentSignal

logger = logging.getLogger(__name__)


@dataclass
class OrderBookData:
    """Order book snapshot."""
    bids: List[Dict[float, float]]  # price, quantity
    asks: List[Dict[float, float]]  # price, quantity
    spread: float
    mid_price: float
    depth_bid: float  # Total bid depth
    depth_ask: float  # Total ask depth


@dataclass
class TickData:
    """Tick-by-tick trade data."""
    price: float
    volume: float
    timestamp: float
    side: str  # buy, sell


class OrderBookImbalanceAgent(BaseAgent):
    """
    Order Book Imbalance Signal.
    
    Measures the imbalance between bid and ask orders.
    High bid imbalance suggests upward pressure.
    """
    
    agent_name = "order_book_imbalance"
    agent_category = "market_structure"
    description = "Measures order book imbalance for short-term direction"
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        bid_depth = features.get("bid_depth", 0)
        ask_depth = features.get("ask_depth", 0)
        
        if bid_depth + ask_depth == 0:
            return self._create_signal("hold", 50, 0.0, "No order book data")
        
        imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
        
        if imbalance > 0.3:
            signal = "buy"
            score = min(1.0, imbalance * 2)
            confidence = 60 + abs(imbalance) * 30
            reasoning = f"Strong bid imbalance: {imbalance:.2%}"
        elif imbalance < -0.3:
            signal = "sell"
            score = max(-1.0, imbalance * 2)
            confidence = 60 + abs(imbalance) * 30
            reasoning = f"Strong ask imbalance: {imbalance:.2%}"
        else:
            signal = "hold"
            score = 0
            confidence = 50
            reasoning = f"Balanced order book: {imbalance:.2%}"
        
        return self._create_signal(signal, confidence, score, reasoning)
    
    def _create_signal(self, signal: str, confidence: float, numerical_score: float, reasoning: str) -> AgentSignal:
        return AgentSignal(
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            signal=signal,
            confidence=confidence,
            numerical_score=numerical_score,
            reasoning=reasoning,
            supporting_data={}
        )


class BidAskSpreadAgent(BaseAgent):
    """
    Bid-Ask Spread Signal.
    
    Analyzes spread dynamics for volatility signal.
    """
    
    agent_name = "bid_ask_spread"
    agent_category = "market_structure"
    description = "Analyzes bid-ask spread for volatility signals"
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        spread_bps = features.get("spread_bps", 0)  # basis points
        spread_pct = spread_bps / 10000
        
        if spread_pct > 0.005:  # > 0.5%
            signal = "sell"
            confidence = 65
            score = -0.6
            reasoning = f"Wide spread indicates uncertainty: {spread_pct:.2%}"
        elif spread_pct > 0.002:  # > 0.2%
            signal = "hold"
            confidence = 55
            score = 0
            reasoning = f"Normal spread: {spread_pct:.2%}"
        else:
            signal = "buy"
            confidence = 60
            score = 0.4
            reasoning = f"Tight spread indicates liquidity: {spread_pct:.2%}"
        
        return AgentSignal(
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            signal=signal,
            confidence=confidence,
            numerical_score=score,
            reasoning=reasoning,
            supporting_data={"spread_bps": spread_bps}
        )


class VWAPDeviationAgent(BaseAgent):
    """
    VWAP Deviation Signal.
    
    Price deviation from VWAP indicates fair value.
    """
    
    agent_name = "vwap_deviation"
    agent_category = "technical"
    description = "Price deviation from VWAP for fair value signal"
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        vwap = features.get("vwap", 0)
        price = features.get("price", 0)
        
        if vwap == 0:
            return self._create_signal("hold", 50, 0.0, "No VWAP data")
        
        deviation = (price - vwap) / vwap
        
        if deviation < -0.005:  # > 0.5% below VWAP
            signal = "buy"
            score = min(1.0, abs(deviation) * 10)
            confidence = 65
            reasoning = f"Price below VWAP by {abs(deviation):.2%}, potential bounce"
        elif deviation > 0.005:
            signal = "sell"
            score = max(-1.0, -deviation * 10)
            confidence = 65
            reasoning = f"Price above VWAP by {deviation:.2%}, potential pullback"
        else:
            signal = "hold"
            confidence = 60
            score = 0
            reasoning = f"Price near VWAP: {deviation:.2%}"
        
        return self._create_signal(signal, confidence, score, reasoning)
    
    def _create_signal(self, signal: str, confidence: float, numerical_score: float, reasoning: str) -> AgentSignal:
        return AgentSignal(
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            signal=signal,
            confidence=confidence,
            numerical_score=numerical_score,
            reasoning=reasoning,
            supporting_data={}
        )


class VolumeProfileAgent(BaseAgent):
    """
    Volume Profile Signal.
    
    Identifies high-volume price nodes (zones of support/resistance).
    """
    
    agent_name = "volume_profile"
    agent_category = "technical"
    description = "Volume profile for support/resistance zones"
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        volume_profile = features.get("volume_profile", {})
        current_price = features.get("price", 0)
        
        if not volume_profile or current_price == 0:
            return self._create_signal("hold", 50, 0.0, "No volume profile data")
        
        high_volume_nodes = volume_profile.get("high_volume_nodes", [])
        
        if not high_volume_nodes:
            return self._create_signal("hold", 50, 0.0, "No significant volume nodes")
        
        distance_to_node = min(
            abs(current_price - node) / current_price 
            for node in high_volume_nodes
        )
        
        if distance_to_node < 0.005:  # Within 0.5% of high volume node
            signal = "buy"
            confidence = 70
            score = 0.7
            reasoning = f"Price near high volume node"
        elif distance_to_node < 0.01:  # Within 1%
            signal = "hold"
            confidence = 55
            score = 0
            reasoning = f"Approaching volume node"
        else:
            signal = "hold"
            confidence = 50
            score = 0
            reasoning = f"No nearby volume nodes"
        
        return self._create_signal(signal, confidence, score, reasoning)
    
    def _create_signal(self, signal: str, confidence: float, numerical_score: float, reasoning: str) -> AgentSignal:
        return AgentSignal(
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            signal=signal,
            confidence=confidence,
            numerical_score=numerical_score,
            reasoning=reasoning,
            supporting_data={}
        )


class MarketDepthAgent(BaseAgent):
    """
    Market Depth Signal.
    
    Analyzes order book depth for liquidity.
    """
    
    agent_name = "market_depth"
    agent_category = "market_structure"
    description = "Market depth analysis for liquidity signals"
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        bid_depth_5 = features.get("bid_depth_5", 0)  # Top 5 bids
        ask_depth_5 = features.get("ask_depth_5", 0)  # Top 5 asks
        
        total_depth = bid_depth_5 + ask_depth_5
        
        if total_depth == 0:
            return self._create_signal("hold", 50, 0.0, "No depth data")
        
        depth_imbalance = (bid_depth_5 - ask_depth_5) / total_depth
        
        if abs(depth_imbalance) > 0.6 and total_depth > 100000:
            if depth_imbalance > 0:
                signal = "buy"
                score = depth_imbalance
                confidence = 70
                reasoning = f"Strong bid depth: {depth_imbalance:.2%}"
            else:
                signal = "sell"
                score = depth_imbalance
                confidence = 70
                reasoning = f"Strong ask depth: {depth_imbalance:.2%}"
        else:
            signal = "hold"
            confidence = 50
            score = 0
            reasoning = f"Balanced depth: {depth_imbalance:.2%}"
        
        return self._create_signal(signal, confidence, score, reasoning)
    
    def _create_signal(self, signal: str, confidence: float, numerical_score: float, reasoning: str) -> AgentSignal:
        return AgentSignal(
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            signal=signal,
            confidence=confidence,
            numerical_score=numerical_score,
            reasoning=reasoning,
            supporting_data={}
        )


class PriceImpactAgent(BaseAgent):
    """
    Price Impact Signal.
    
    Measures price impact of recent trades.
    """
    
    agent_name = "price_impact"
    agent_category = "market_structure"
    description = "Price impact analysis for momentum"
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        traded_volume = features.get("traded_volume", 0)
        price_change = features.get("price_change_5m", 0)  # 5 min change
        
        if traded_volume == 0:
            return self._create_signal("hold", 50, 0.0, "No trade data")
        
        impact_per_volume = abs(price_change) / traded_volume if traded_volume > 0 else 0
        
        if impact_per_volume > 0.0001:  # High impact
            signal = "buy" if price_change > 0 else "sell"
            confidence = 60
            score = np.sign(price_change) * 0.5
            reasoning = f"Significant price impact detected"
        else:
            signal = "hold"
            confidence = 55
            score = 0
            reasoning = f"Low impact trading"
        
        return self._create_signal(signal, confidence, score, reasoning)
    
    def _create_signal(self, signal: str, confidence: float, numerical_score: float, reasoning: str) -> AgentSignal:
        return AgentSignal(
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            signal=signal,
            confidence=confidence,
            numerical_score=numerical_score,
            reasoning=reasoning,
            supporting_data={}
        )


class AmihudIlliquidityAgent(BaseAgent):
    """
    Amihud Illiquidity Ratio.
    
    Measures price impact of trades (illiquidity).
    """
    
    agent_name = "amihud_illiquidity"
    agent_category = "risk"
    description = "Amihud illiquidity ratio for liquidity risk"
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        illiquidity = features.get("amihud_ratio", 0)
        
        if illiquidity < 0.001:
            signal = "buy"
            confidence = 65
            score = -illiquidity * 100
            reasoning = f"High liquidity: {illiquidity:.6f}"
        elif illiquidity > 0.01:
            signal = "sell"
            confidence = 65
            score = -0.7
            reasoning = f"Low liquidity: {illiquidity:.6f}"
        else:
            signal = "hold"
            confidence = 50
            score = 0
            reasoning = f"Normal liquidity: {illiquidity:.6f}"
        
        return AgentSignal(
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            signal=signal,
            confidence=confidence,
            numerical_score=score,
            reasoning=reasoning,
            supporting_data={"amihud_ratio": illiquidity}
        )


class MarketMicrostructureAggregator:
    """
    Aggregate all microstructure signals.
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.agents = [
            OrderBookImbalanceAgent(config or AgentConfig()),
            BidAskSpreadAgent(config or AgentConfig()),
            VWAPDeviationAgent(config or AgentConfig()),
            MarketDepthAgent(config or AgentConfig()),
            PriceImpactAgent(config or AgentConfig()),
            AmihudIlliquidityAgent(config or AgentConfig()),
        ]
    
    def run_all(self, features: Dict[str, Any]) -> List[AgentSignal]:
        """Run all microstructure agents."""
        signals = []
        
        for agent in self.agents:
            try:
                signal = agent.run(features, use_cache=False)
                signals.append(signal)
            except Exception as e:
                logger.warning(f"Agent {agent.agent_name} failed: {e}")
        
        return signals


def simulate_order_book(
    mid_price: float = 100,
    spread_pct: float = 0.001,
    levels: int = 10
) -> OrderBookData:
    """Simulate order book data for testing."""
    bids = []
    asks = []
    
    bid_price = mid_price * (1 - spread_pct / 2)
    ask_price = mid_price * (1 + spread_pct / 2)
    
    for i in range(levels):
        depth = np.random.exponential(1000) * (0.9 ** i)
        
        bids.append({bid_price * (1 - 0.001 * i): depth})
        asks.append({ask_price * (1 + 0.001 * i): depth})
    
    depth_bid = sum(d for b in bids for d in b.values())
    depth_ask = sum(d for a in asks for d in a.values())
    
    return OrderBookData(
        bids=bids,
        asks=asks,
        spread=ask_price - bid_price,
        mid_price=mid_price,
        depth_bid=depth_bid,
        depth_ask=depth_ask
    )
