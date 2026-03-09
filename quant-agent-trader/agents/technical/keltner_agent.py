"""
Keltner Channels Agent - Keltner Channel analysis.

This agent analyzes Keltner Channels to provide signals:
- Price vs channels: trend direction
- Channel breakouts: momentum signals
- Channel squeeze: volatility contraction
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class KeltnerAgent(BaseAgent):
    """
    Agent for Keltner Channel analysis.
    
    Analyzes volatility-based channels for trend signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Keltner Channels agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Keltner Channel signals for volatility and trend analysis",
                required_features=["keltner_upper", "keltner_middle", "keltner_lower", "price_vs_keltner", "keltner_squeeze"],
                author="Quant Team",
                tags=["technical", "keltner", "channels", "volatility", "trend"]
            )
        
        super().__init__(
            agent_name="keltner_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Keltner Channel based trading signal.
        
        Args:
            features: Dictionary containing Keltner Channel data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            keltner_upper: float = features.get("keltner_upper", 0.0)
            keltner_lower: float = features.get("keltner_lower", 0.0)
            price_vs_keltner: str = features.get("price_vs_keltner", "middle")
            keltner_squeeze: bool = features.get("keltner_squeeze", False)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if keltner_squeeze:
                signal = "hold"
                confidence = 40.0
                numerical_score = 0.0
                reasoning = (
                    "Keltner squeeze detected. "
                    "Low volatility - await breakout."
                )
                supporting_data = {
                    "keltner_upper": keltner_upper,
                    "keltner_lower": keltner_lower,
                    "price_vs_keltner": price_vs_keltner,
                    "keltner_squeeze": keltner_squeeze,
                    "regime": "squeeze"
                }
                
            elif price_vs_keltner == "above_upper":
                signal = "buy"
                confidence = 70.0
                numerical_score = -0.4
                reasoning = (
                    "Price above upper Keltner Channel. "
                    "Strong bullish momentum."
                )
                supporting_data = {
                    "keltner_upper": keltner_upper,
                    "keltner_lower": keltner_lower,
                    "price_vs_keltner": price_vs_keltner,
                    "keltner_squeeze": keltner_squeeze,
                    "regime": "bullish_breakout"
                }
                
            elif price_vs_keltner == "below_lower":
                signal = "sell"
                confidence = 70.0
                numerical_score = 0.4
                reasoning = (
                    "Price below lower Keltner Channel. "
                    "Strong bearish momentum."
                )
                supporting_data = {
                    "keltner_upper": keltner_upper,
                    "keltner_lower": keltner_lower,
                    "price_vs_keltner": price_vs_keltner,
                    "keltner_squeeze": keltner_squeeze,
                    "regime": "bearish_breakout"
                }
                
            elif price_vs_keltner == "above_middle":
                signal = "buy"
                confidence = 55.0
                numerical_score = -0.2
                reasoning = (
                    "Price above middle Keltner line. "
                    "Bullish bias."
                )
                supporting_data = {
                    "keltner_upper": keltner_upper,
                    "keltner_lower": keltner_lower,
                    "price_vs_keltner": price_vs_keltner,
                    "keltner_squeeze": keltner_squeeze,
                    "regime": "bullish"
                }
                
            elif price_vs_keltner == "below_middle":
                signal = "sell"
                confidence = 55.0
                numerical_score = 0.2
                reasoning = (
                    "Price below middle Keltner line. "
                    "Bearish bias."
                )
                supporting_data = {
                    "keltner_upper": keltner_upper,
                    "keltner_lower": keltner_lower,
                    "price_vs_keltner": price_vs_keltner,
                    "keltner_squeeze": keltner_squeeze,
                    "regime": "bearish"
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    "Price within Keltner Channels. "
                    "No clear direction."
                )
                supporting_data = {
                    "keltner_upper": keltner_upper,
                    "keltner_lower": keltner_lower,
                    "price_vs_keltner": price_vs_keltner,
                    "keltner_squeeze": keltner_squeeze,
                    "regime": "neutral"
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
            return self._create_error_signal(f"Keltner signal computation failed: {str(e)}")
