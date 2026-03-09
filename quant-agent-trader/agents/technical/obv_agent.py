"""
OBV Agent - On-Balance Volume analysis.

This agent analyzes OBV to provide signals:
- OBV trend: confirms price trend
- OBV divergence: potential reversal
- OBV breakouts: leading signals
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class OBVAgent(BaseAgent):
    """
    Agent for On-Balance Volume analysis.
    
    Analyzes volume flow to confirm or predict price moves.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the OBV agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="OBV signals for volume-based trend confirmation",
                required_features=["obv", "obv_ma", "obv_trend", "obv_divergence"],
                author="Quant Team",
                tags=["technical", "obv", "on_balance_volume", "volume"]
            )
        
        super().__init__(
            agent_name="obv_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute OBV based trading signal.
        
        Args:
            features: Dictionary containing OBV data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            obv: float = features.get("obv", 0.0)
            obv_ma: float = features.get("obv_ma", 0.0)
            obv_trend: str = features.get("obv_trend", "flat")
            obv_divergence: str = features.get("obv_divergence", "none")
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if obv_divergence == "bullish":
                signal = "buy"
                confidence = 75.0
                numerical_score = -0.5
                reasoning = (
                    "Bullish OBV divergence. "
                    "Volume confirms upward move coming."
                )
                supporting_data = {
                    "obv": obv,
                    "obv_ma": obv_ma,
                    "obv_trend": obv_trend,
                    "obv_divergence": obv_divergence,
                    "signal": "bullish_divergence"
                }
                
            elif obv_divergence == "bearish":
                signal = "sell"
                confidence = 75.0
                numerical_score = 0.5
                reasoning = (
                    "Bearish OBV divergence. "
                    "Volume warns of downward move."
                )
                supporting_data = {
                    "obv": obv,
                    "obv_ma": obv_ma,
                    "obv_trend": obv_trend,
                    "obv_divergence": obv_divergence,
                    "signal": "bearish_divergence"
                }
                
            elif obv_trend == "up" and obv > obv_ma:
                signal = "buy"
                confidence = 65.0
                numerical_score = -0.4
                reasoning = (
                    "OBV in uptrend above MA. "
                    "Volume confirms bullish move."
                )
                supporting_data = {
                    "obv": obv,
                    "obv_ma": obv_ma,
                    "obv_trend": obv_trend,
                    "obv_divergence": obv_divergence,
                    "signal": "confirmed_uptrend"
                }
                
            elif obv_trend == "down" and obv < obv_ma:
                signal = "sell"
                confidence = 65.0
                numerical_score = 0.4
                reasoning = (
                    "OBV in downtrend below MA. "
                    "Volume confirms bearish move."
                )
                supporting_data = {
                    "obv": obv,
                    "obv_ma": obv_ma,
                    "obv_trend": obv_trend,
                    "obv_divergence": obv_divergence,
                    "signal": "confirmed_downtrend"
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    "OBV flat or neutral. "
                    "No volume confirmation."
                )
                supporting_data = {
                    "obv": obv,
                    "obv_ma": obv_ma,
                    "obv_trend": obv_trend,
                    "obv_divergence": obv_divergence,
                    "signal": "neutral"
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
            return self._create_error_signal(f"OBV signal computation failed: {str(e)}")
