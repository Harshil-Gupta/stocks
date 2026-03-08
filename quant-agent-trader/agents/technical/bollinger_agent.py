"""
Bollinger Bands Agent - Bollinger Bands breakout and mean reversion signals.

This agent analyzes Bollinger Bands to identify:
- Oversold conditions (price near lower band)
- Overbought conditions (price near upper band)
- Breakout signals (price crossing bands)
- Mean reversion opportunities
"""

from typing import Dict, Any, Optional
import numpy as np

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class BollingerAgent(BaseAgent):
    """
    Agent for Bollinger Bands-based trading signals.
    
    Analyzes price position within generate
    buy/sell/hold Bollinger Bands to signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Bollinger Bands agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Bollinger Bands-based trading signals using band position and breakouts",
                required_features=["bb_position", "bb_upper", "bb_lower", "bb_middle", "close", "atr"],
                author="Quant Team",
                tags=["bollinger", "bands", "volatility", "technical"]
            )
        
        super().__init__(
            agent_name="bollinger_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._oversold_threshold: float = 0.1
        self._overbought_threshold: float = 0.9
        self._breakout_threshold: float = 1.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Bollinger Bands-based trading signal.
        
        Args:
            features: Dictionary containing Bollinger Bands data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            bb_position: float = features.get("bb_position", 0.5)
            bb_upper: float = features.get("bb_upper", 0)
            bb_lower: float = features.get("bb_lower", 0)
            close: float = features.get("close", 0)
            atr: float = features.get("atr", 0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if bb_position <= self._oversold_threshold:
                signal = "buy"
                confidence = min(85.0, 75.0 + (0.1 - bb_position) * 100)
                numerical_score = -1.0 * (0.1 - bb_position) / 0.1
                reasoning = (
                    f"Price at lower Bollinger Band ({bb_position:.2%}), "
                    f"indicating oversold conditions. Potential bounce expected."
                )
                supporting_data = {
                    "bb_position": bb_position,
                    "bb_condition": "oversold",
                    "threshold": self._oversold_threshold,
                    "atr": atr
                }
                
            elif bb_position >= self._overbought_threshold:
                signal = "sell"
                confidence = min(85.0, 75.0 + (bb_position - 0.9) * 100)
                numerical_score = (bb_position - 0.9) / 0.1
                reasoning = (
                    f"Price at upper Bollinger Band ({bb_position:.2%}), "
                    f"indicating overbought conditions. Potential pullback expected."
                )
                supporting_data = {
                    "bb_position": bb_position,
                    "bb_condition": "overbought",
                    "threshold": self._overbought_threshold,
                    "atr": atr
                }
                
            elif bb_position < 0.3:
                signal = "buy"
                confidence = 60.0 + (0.3 - bb_position) * 50
                numerical_score = -0.4
                reasoning = (
                    f"Price below 30% of Bollinger Bands range ({bb_position:.2%}), "
                    f"showing weakness but not oversold yet."
                )
                supporting_data = {
                    "bb_position": bb_position,
                    "bb_condition": "depressed",
                    "atr": atr
                }
                
            elif bb_position > 0.7:
                signal = "sell"
                confidence = 60.0 + (bb_position - 0.7) * 50
                numerical_score = 0.4
                reasoning = (
                    f"Price above 70% of Bollinger Bands range ({bb_position:.2%}), "
                    f"showing strength but not overbought yet."
                )
                supporting_data = {
                    "bb_position": bb_position,
                    "bb_condition": "elevated",
                    "atr": atr
                }
                
            else:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.0
                reasoning = (
                    f"Price in middle of Bollinger Bands ({bb_position:.2%}), "
                    f"no clear directional signal."
                )
                supporting_data = {
                    "bb_position": bb_position,
                    "bb_condition": "neutral",
                    "atr": atr
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
            return self._create_error_signal(f"Bollinger signal computation failed: {str(e)}")
    
    def set_thresholds(self, oversold: float, overbought: float) -> None:
        """Set custom overbought/oversold thresholds."""
        self._oversold_threshold = oversold
        self._overbought_threshold = overbought
