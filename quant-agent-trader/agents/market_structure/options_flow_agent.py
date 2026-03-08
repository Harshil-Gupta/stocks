"""
Options Flow Agent - Options market flow analysis.

This agent analyzes options trading activity to provide signals:
- Unusual options activity: institutional flow
- Call buying pressure: bullish sentiment
- Put buying pressure: bearish sentiment/protection
- Volatility crush signals
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class OptionsFlowAgent(BaseAgent):
    """
    Agent for options flow analysis.
    
    Analyzes options market activity and institutional flows.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Options Flow agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Options flow analysis for institutional sentiment",
                required_features=["call_volume", "put_volume", "flow_ratio", "unusual_activity", "iv_percentile"],
                author="Quant Team",
                tags=["market_structure", "options", "flow", "institutional"]
            )
        
        super().__init__(
            agent_name="options_flow_agent",
            agent_category=AgentCategory.MARKET_STRUCTURE,
            metadata=metadata,
            config=config
        )
        
        self._bullish_threshold: float = 1.5
        self._bearish_threshold: float = 0.6
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute options flow based trading signal.
        
        Args:
            features: Dictionary containing options flow data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            flow_ratio: float = features.get("flow_ratio", 1.0)
            unusual_activity: float = features.get("unusual_activity", 1.0)
            call_volume: float = features.get("call_volume", 0.0)
            put_volume: float = features.get("put_volume", 0.0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if flow_ratio > self._bullish_threshold:
                if unusual_activity > 2.0:
                    signal = "buy"
                    confidence = 75.0
                    numerical_score = -0.5
                    reasoning = (
                        f"Strong call pressure (ratio: {flow_ratio:.2f}) with unusual activity. "
                        f"Bullish institutional flow detected."
                    )
                else:
                    signal = "buy"
                    confidence = 65.0
                    numerical_score = -0.4
                    reasoning = (
                        f"Call bias detected (ratio: {flow_ratio:.2f}). "
                        f"Bullish options flow."
                    )
                supporting_data = {
                    "flow_ratio": flow_ratio,
                    "unusual_activity": unusual_activity,
                    "call_volume": call_volume,
                    "put_volume": put_volume,
                    "sentiment": "bullish"
                }
                
            elif flow_ratio < self._bearish_threshold:
                if unusual_activity > 2.0:
                    signal = "sell"
                    confidence = 75.0
                    numerical_score = 0.5
                    reasoning = (
                        f"Strong put pressure (ratio: {flow_ratio:.2f}) with unusual activity. "
                        f"Bearish institutional flow detected."
                    )
                else:
                    signal = "sell"
                    confidence = 65.0
                    numerical_score = 0.4
                    reasoning = (
                        f"Put bias detected (ratio: {flow_ratio:.2f}). "
                        f"Bearish options flow."
                    )
                supporting_data = {
                    "flow_ratio": flow_ratio,
                    "unusual_activity": unusual_activity,
                    "call_volume": call_volume,
                    "put_volume": put_volume,
                    "sentiment": "bearish"
                }
                
            else:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.0
                reasoning = (
                    f"Balanced options flow (ratio: {flow_ratio:.2f}). "
                    f"No significant directional bias."
                )
                supporting_data = {
                    "flow_ratio": flow_ratio,
                    "unusual_activity": unusual_activity,
                    "call_volume": call_volume,
                    "put_volume": put_volume,
                    "sentiment": "neutral"
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
            return self._create_error_signal(f"Options flow signal computation failed: {str(e)}")
