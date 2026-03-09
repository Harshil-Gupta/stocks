"""
Donchian Channels Agent - Donchian Channel analysis.

This agent analyzes Donchian Channels to provide signals:
- Channel breakouts: trend entry
- Channel touch: support/resistance
- Channel width: volatility
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class DonchianAgent(BaseAgent):
    """
    Agent for Donchian Channel analysis.
    
    Analyzes price channels for breakout and trend signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Donchian Channels agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Donchian Channel signals for breakout and trend analysis",
                required_features=["donchian_upper", "donchian_middle", "donchian_lower", "price_vs_donchian", "donchian_width"],
                author="Quant Team",
                tags=["technical", "donchian", "channels", "breakout", "trend"]
            )
        
        super().__init__(
            agent_name="donchian_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._narrow_channel_threshold: float = 3.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Donchian Channel based trading signal.
        
        Args:
            features: Dictionary containing Donchian Channel data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            donchian_upper: float = features.get("donchian_upper", 0.0)
            donchian_lower: float = features.get("donchian_lower", 0.0)
            donchian_middle: float = features.get("donchian_middle", 0.0)
            price_vs_donchian: str = features.get("price_vs_donchian", "middle")
            donchian_width: float = features.get("donchian_width", 5.0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if donchian_width < self._narrow_channel_threshold:
                signal = "hold"
                confidence = 45.0
                numerical_score = 0.0
                reasoning = (
                    f"Narrow Donchian Channel ({donchian_width:.1f}%). "
                    f"Compression - await breakout."
                )
                supporting_data = {
                    "donchian_upper": donchian_upper,
                    "donchian_middle": donchian_middle,
                    "donchian_lower": donchian_lower,
                    "price_vs_donchian": price_vs_donchian,
                    "donchian_width": donchian_width,
                    "regime": "compression"
                }
                
            elif price_vs_donchian == "above_upper":
                signal = "buy"
                confidence = 70.0
                numerical_score = -0.4
                reasoning = (
                    "Price breakout above upper Donchian Channel. "
                    "Strong bullish signal."
                )
                supporting_data = {
                    "donchian_upper": donchian_upper,
                    "donchian_middle": donchian_middle,
                    "donchian_lower": donchian_lower,
                    "price_vs_donchian": price_vs_donchian,
                    "donchian_width": donchian_width,
                    "regime": "bullish_breakout"
                }
                
            elif price_vs_donchian == "below_lower":
                signal = "sell"
                confidence = 70.0
                numerical_score = 0.4
                reasoning = (
                    "Price breakout below lower Donchian Channel. "
                    "Strong bearish signal."
                )
                supporting_data = {
                    "donchian_upper": donchian_upper,
                    "donchian_middle": donchian_middle,
                    "donchian_lower": donchian_lower,
                    "price_vs_donchian": price_vs_donchian,
                    "donchian_width": donchian_width,
                    "regime": "bearish_breakout"
                }
                
            elif price_vs_donchian == "above_middle":
                signal = "buy"
                confidence = 55.0
                numerical_score = -0.2
                reasoning = (
                    "Price above middle Donchian line. "
                    "Bullish bias."
                )
                supporting_data = {
                    "donchian_upper": donchian_upper,
                    "donchian_middle": donchian_middle,
                    "donchian_lower": donchian_lower,
                    "price_vs_donchian": price_vs_donchian,
                    "donchian_width": donchian_width,
                    "regime": "bullish"
                }
                
            elif price_vs_donchian == "below_middle":
                signal = "sell"
                confidence = 55.0
                numerical_score = 0.2
                reasoning = (
                    "Price below middle Donchian line. "
                    "Bearish bias."
                )
                supporting_data = {
                    "donchian_upper": donchian_upper,
                    "donchian_middle": donchian_middle,
                    "donchian_lower": donchian_lower,
                    "price_vs_donchian": price_vs_donchian,
                    "donchian_width": donchian_width,
                    "regime": "bearish"
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    "Price within Donchian Channel. "
                    "No clear direction."
                )
                supporting_data = {
                    "donchian_upper": donchian_upper,
                    "donchian_middle": donchian_middle,
                    "donchian_lower": donchian_lower,
                    "price_vs_donchian": price_vs_donchian,
                    "donchian_width": donchian_width,
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
            return self._create_error_signal(f"Donchian signal computation failed: {str(e)}")
