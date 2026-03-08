"""
Insider Trading Agent - Insider buying/selling analysis.

This agent analyzes insider trading patterns:
- Recent insider buying
- Recent insider selling
- Insider buying/selling ratio
- Bulk block deals
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class InsiderTradingAgent(BaseAgent):
    """
    Agent for Insider Trading pattern analysis.
    
    Analyzes insider buying/selling activity.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Insider Trading agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Insider buying and selling pattern analysis for sentiment signals",
                required_features=["insider_buy_value", "insider_sell_value", "insider_net_position"],
                author="Quant Team",
                tags=["insider", "ownership", "sentiment", "smart_money"]
            )
        
        super().__init__(
            agent_name="insider_trading_agent",
            agent_category=AgentCategory.SENTIMENT,
            metadata=metadata,
            config=config
        )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Insider Trading signal.
        
        Args:
            features: Dictionary containing insider trading data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            insider_buy: float = features.get("insider_buy_value", 0)
            insider_sell: float = features.get("insider_sell_value", 0)
            insider_net: float = features.get("insider_net_position", 0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if insider_net > 0 and insider_buy > insider_sell * 2:
                signal = "buy"
                confidence = min(75.0, 60.0 + (insider_buy / (insider_sell + 1)) * 5)
                numerical_score = -0.5
                reasoning = (
                    f"Strong insider buying (₹{insider_buy:,.0f} vs ₹{insider_sell:,.0f} selling). "
                    f"Insiders are bullish."
                )
                supporting_data = {
                    "insider_buy": insider_buy,
                    "insider_sell": insider_sell,
                    "net_position": insider_net,
                    "signal_type": "buying"
                }
                
            elif insider_net < 0 and insider_sell > insider_buy * 2:
                signal = "sell"
                confidence = min(70.0, 55.0 + (insider_sell / (insider_buy + 1)) * 5)
                numerical_score = 0.5
                reasoning = (
                    f"Strong insider selling (₹{insider_sell:,.0f} vs ₹{insider_buy:,.0f} buying). "
                    f"Insiders are bearish."
                )
                supporting_data = {
                    "insider_buy": insider_buy,
                    "insider_sell": insider_sell,
                    "net_position": insider_net,
                    "signal_type": "selling"
                }
                
            elif insider_buy > 0 or insider_sell > 0:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    f"Moderate insider activity. Buy: ₹{insider_buy:,.0f}, "
                    f"Sell: ₹{insider_sell:,.0f}."
                )
                supporting_data = {
                    "insider_buy": insider_buy,
                    "insider_sell": insider_sell,
                    "signal_type": "moderate"
                }
                
            else:
                signal = "hold"
                confidence = 45.0
                numerical_score = 0.0
                reasoning = "No significant insider activity data available."
                supporting_data = {
                    "signal_type": "no_data"
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
            return self._create_error_signal(f"Insider Trading signal failed: {str(e)}")
