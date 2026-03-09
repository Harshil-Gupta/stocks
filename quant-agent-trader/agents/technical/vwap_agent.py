"""
VWAP Agent - Volume Weighted Average Price analysis.

This agent analyzes VWAP to provide signals:
- Price vs VWAP: intraday trend direction
- VWAP bands: support/resistance levels
- VWAP breakouts: momentum signals
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class VWAPAgent(BaseAgent):
    """
    Agent for VWAP analysis.
    
    Analyzes volume-weighted average price for intraday signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the VWAP agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="VWAP signals for intraday trend and support/resistance",
                required_features=["vwap", "price_vs_vwap", "vwap_upper_band", "vwap_lower_band", "vwap_position"],
                author="Quant Team",
                tags=["technical", "vwap", "volume_weighted_average", "intraday"]
            )
        
        super().__init__(
            agent_name="vwap_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute VWAP based trading signal.
        
        Args:
            features: Dictionary containing VWAP data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            vwap: float = features.get("vwap", 0.0)
            price_vs_vwap: float = features.get("price_vs_vwap", 0.0)
            vwap_position: float = features.get("vwap_position", 0.5)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if price_vs_vwap > 0.01:
                if vwap_position > 0.9:
                    signal = "sell"
                    confidence = 70.0
                    numerical_score = 0.4
                    reasoning = (
                        f"Price well above VWAP at upper band. "
                        f"Potential pullback."
                    )
                else:
                    signal = "buy"
                    confidence = 65.0
                    numerical_score = -0.4
                    reasoning = (
                        f"Price above VWAP (+{price_vs_vwap:.2%}). "
                        f"Intraday bullish."
                    )
                supporting_data = {
                    "vwap": vwap,
                    "price_vs_vwap": price_vs_vwap,
                    "vwap_position": vwap_position,
                    "signal": "above_vwap"
                }
                
            elif price_vs_vwap < -0.01:
                if vwap_position < 0.1:
                    signal = "buy"
                    confidence = 70.0
                    numerical_score = -0.4
                    reasoning = (
                        f"Price well below VWAP at lower band. "
                        f"Potential bounce."
                    )
                else:
                    signal = "sell"
                    confidence = 65.0
                    numerical_score = 0.4
                    reasoning = (
                        f"Price below VWAP ({price_vs_vwap:.2%}). "
                        f"Intraday bearish."
                    )
                supporting_data = {
                    "vwap": vwap,
                    "price_vs_vwap": price_vs_vwap,
                    "vwap_position": vwap_position,
                    "signal": "below_vwap"
                }
                
            else:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.0
                reasoning = (
                    "Price near VWAP. "
                    "No clear intraday direction."
                )
                supporting_data = {
                    "vwap": vwap,
                    "price_vs_vwap": price_vs_vwap,
                    "vwap_position": vwap_position,
                    "signal": "at_vwap"
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
            return self._create_error_signal(f"VWAP signal computation failed: {str(e)}")
