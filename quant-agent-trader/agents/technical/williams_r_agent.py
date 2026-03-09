"""
Williams %R Agent - Williams %R indicator analysis.

This agent analyzes Williams %R to provide signals:
- Overbought (-20 to 0): potential reversal lower
- Oversold (-100 to -80): potential reversal higher
- Momentum divergence: reversal signals
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class WilliamsRAgent(BaseAgent):
    """
    Agent for Williams %R analysis.
    
    Analyzes momentum and overbought/oversold conditions.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Williams %R agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Williams %R signals for overbought/oversold conditions",
                required_features=["williams_r", "williams_r_ma", "williams_r_divergence"],
                author="Quant Team",
                tags=["technical", "williams_r", "momentum", "oscillator"]
            )
        
        super().__init__(
            agent_name="williams_r_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._overbought_threshold: float = -20.0
        self._oversold_threshold: float = -80.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Williams %R based trading signal.
        
        Args:
            features: Dictionary containing Williams %R data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            williams_r: float = features.get("williams_r", -50.0)
            williams_r_ma: float = features.get("williams_r_ma", -50.0)
            williams_r_divergence: str = features.get("williams_r_divergence", "none")
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if williams_r > self._overbought_threshold:
                if williams_r_divergence == "bearish":
                    signal = "sell"
                    confidence = 80.0
                    numerical_score = 0.5
                    reasoning = (
                        f"Overbought ({williams_r:.1f}) with bearish divergence. "
                        f"Strong reversal signal."
                    )
                else:
                    signal = "sell"
                    confidence = 65.0
                    numerical_score = 0.4
                    reasoning = (
                        f"Williams %R overbought ({williams_r:.1f}). "
                        f"Potential pullback."
                    )
                supporting_data = {
                    "williams_r": williams_r,
                    "williams_r_ma": williams_r_ma,
                    "williams_r_divergence": williams_r_divergence,
                    "zone": "overbought"
                }
                
            elif williams_r < self._oversold_threshold:
                if williams_r_divergence == "bullish":
                    signal = "buy"
                    confidence = 80.0
                    numerical_score = -0.5
                    reasoning = (
                        f"Oversold ({williams_r:.1f}) with bullish divergence. "
                        f"Strong reversal signal."
                    )
                else:
                    signal = "buy"
                    confidence = 65.0
                    numerical_score = -0.4
                    reasoning = (
                        f"Williams %R oversold ({williams_r:.1f}). "
                        f"Potential bounce."
                    )
                supporting_data = {
                    "williams_r": williams_r,
                    "williams_r_ma": williams_r_ma,
                    "williams_r_divergence": williams_r_divergence,
                    "zone": "oversold"
                }
                
            else:
                if williams_r > williams_r_ma:
                    signal = "buy"
                    confidence = 55.0
                    numerical_score = -0.2
                    reasoning = (
                        f"Williams %R ({williams_r:.1f}) above MA. "
                        f"Momentum turning bullish."
                    )
                    supporting_data = {
                        "williams_r": williams_r,
                        "williams_r_ma": williams_r_ma,
                        "williams_r_divergence": williams_r_divergence,
                        "zone": "middle_bullish"
                    }
                else:
                    signal = "sell"
                    confidence = 55.0
                    numerical_score = 0.2
                    reasoning = (
                        f"Williams %R ({williams_r:.1f}) below MA. "
                        f"Momentum turning bearish."
                    )
                    supporting_data = {
                        "williams_r": williams_r,
                        "williams_r_ma": williams_r_ma,
                        "williams_r_divergence": williams_r_divergence,
                        "zone": "middle_bearish"
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
            return self._create_error_signal(f"Williams %R signal computation failed: {str(e)}")
