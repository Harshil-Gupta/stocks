"""
Order Imbalance Agent - Order book imbalance analysis.

This agent analyzes order book imbalances to provide signals:
- Buy order imbalance: upward price pressure
- Sell order imbalance: downward price pressure
- Imbalance extremes: potential reversal points
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class OrderImbalanceAgent(BaseAgent):
    """
    Agent for order book imbalance analysis.
    
    Analyzes bid/ask imbalances and order book pressure.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Order Imbalance agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Order book imbalance for short-term price direction",
                required_features=["imbalance_ratio", "imbalance_change", "bid_volume", "ask_volume"],
                author="Quant Team",
                tags=["market_structure", "order_book", "imbalance", "liquidity"]
            )
        
        super().__init__(
            agent_name="order_imbalance_agent",
            agent_category=AgentCategory.MARKET_STRUCTURE,
            metadata=metadata,
            config=config
        )
        
        self._buy_imbalance_threshold: float = 2.0
        self._sell_imbalance_threshold: float = 0.5
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute order imbalance based trading signal.
        
        Args:
            features: Dictionary containing order imbalance data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            imbalance_ratio: float = features.get("imbalance_ratio", 1.0)
            imbalance_change: float = features.get("imbalance_change", 0.0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if imbalance_ratio > self._buy_imbalance_threshold:
                if imbalance_change > 0.5:
                    signal = "buy"
                    confidence = 75.0
                    numerical_score = -0.5
                    reasoning = (
                        f"Strong buy imbalance ({imbalance_ratio:.2f}x) increasing. "
                        f"Immediate upward price pressure."
                    )
                else:
                    signal = "buy"
                    confidence = 65.0
                    numerical_score = -0.4
                    reasoning = (
                        f"Buy order imbalance ({imbalance_ratio:.2f}x). "
                        f"Upward price pressure."
                    )
                supporting_data = {
                    "imbalance_ratio": imbalance_ratio,
                    "imbalance_change": imbalance_change,
                    "direction": "buy"
                }
                
            elif imbalance_ratio < self._sell_imbalance_threshold:
                if imbalance_change < -0.5:
                    signal = "sell"
                    confidence = 75.0
                    numerical_score = 0.5
                    reasoning = (
                        f"Strong sell imbalance ({imbalance_ratio:.2f}x) increasing. "
                        f"Immediate downward price pressure."
                    )
                else:
                    signal = "sell"
                    confidence = 65.0
                    numerical_score = 0.4
                    reasoning = (
                        f"Sell order imbalance ({imbalance_ratio:.2f}x). "
                        f"Downward price pressure."
                    )
                supporting_data = {
                    "imbalance_ratio": imbalance_ratio,
                    "imbalance_change": imbalance_change,
                    "direction": "sell"
                }
                
            else:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.0
                reasoning = (
                    f"Balanced order book ({imbalance_ratio:.2f}x). "
                    f"No immediate price pressure."
                )
                supporting_data = {
                    "imbalance_ratio": imbalance_ratio,
                    "imbalance_change": imbalance_change,
                    "direction": "balanced"
                }
            
            return AgentSignal(
                agent_name=self._agent_name,
                agent_category=self._agent_category.value,
                signal=signal,
                confidence=confidence,
                numerical_score=numerical_score,
                reasoning=reasoning,
                supporting_data=supporting_data
            )
            
        except Exception as e:
            return self._create_error_signal(f"Order imbalance signal computation failed: {str(e)}")
