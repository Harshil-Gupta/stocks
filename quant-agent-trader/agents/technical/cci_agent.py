"""
CCI Agent - Commodity Channel Index analysis.

This agent analyzes CCI to provide signals:
- Extreme +100: overbought
- Extreme -100: oversold
- CCI trend: momentum direction
- Zero line crossovers
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class CCIAgent(BaseAgent):
    """
    Agent for Commodity Channel Index analysis.
    
    Analyzes cyclical momentum using CCI.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the CCI agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="CCI signals for cyclical overbought/oversold conditions",
                required_features=["cci", "cci_ma", "cci_trend", "cci_extreme"],
                author="Quant Team",
                tags=["technical", "cci", "commodity_channel_index", "oscillator"]
            )
        
        super().__init__(
            agent_name="cci_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._overbought_threshold: float = 100.0
        self._oversold_threshold: float = -100.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute CCI based trading signal.
        
        Args:
            features: Dictionary containing CCI data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            cci: float = features.get("cci", 0.0)
            cci_ma: float = features.get("cci_ma", 0.0)
            cci_extreme: str = features.get("cci_extreme", "none")
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if cci > self._overbought_threshold:
                signal = "sell"
                confidence = 65.0
                numerical_score = 0.4
                reasoning = (
                    f"CCI extreme overbought ({cci:.1f}). "
                    f"Potential reversal."
                )
                supporting_data = {
                    "cci": cci,
                    "cci_ma": cci_ma,
                    "cci_extreme": cci_extreme,
                    "zone": "overbought"
                }
                
            elif cci < self._oversold_threshold:
                signal = "buy"
                confidence = 65.0
                numerical_score = -0.4
                reasoning = (
                    f"CCI extreme oversold ({cci:.1f}). "
                    f"Potential bounce."
                )
                supporting_data = {
                    "cci": cci,
                    "cci_ma": cci_ma,
                    "cci_extreme": cci_extreme,
                    "zone": "oversold"
                }
                
            else:
                if cci > 0 and cci > cci_ma:
                    signal = "buy"
                    confidence = 60.0
                    numerical_score = -0.3
                    reasoning = (
                        f"CCI positive ({cci:.1f}) and rising. "
                        f"Bullish momentum."
                    )
                    supporting_data = {
                        "cci": cci,
                        "cci_ma": cci_ma,
                        "cci_extreme": cci_extreme,
                        "zone": "bullish"
                    }
                elif cci < 0 and cci < cci_ma:
                    signal = "sell"
                    confidence = 60.0
                    numerical_score = 0.3
                    reasoning = (
                        f"CCI negative ({cci:.1f}) and falling. "
                        f"Bearish momentum."
                    )
                    supporting_data = {
                        "cci": cci,
                        "cci_ma": cci_ma,
                        "cci_extreme": cci_extreme,
                        "zone": "bearish"
                    }
                else:
                    signal = "hold"
                    confidence = 50.0
                    numerical_score = 0.0
                    reasoning = (
                        f"CCI neutral ({cci:.1f}). "
                        f"No clear direction."
                    )
                    supporting_data = {
                        "cci": cci,
                        "cci_ma": cci_ma,
                        "cci_extreme": cci_extreme,
                        "zone": "neutral"
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
            return self._create_error_signal(f"CCI signal computation failed: {str(e)}")
