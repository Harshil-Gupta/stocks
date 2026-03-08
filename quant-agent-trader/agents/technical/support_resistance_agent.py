"""
Support/Resistance Agent - Price levels analysis.

This agent identifies key support and resistance levels:
- Pivot points analysis
- Price near support (buy signal)
- Price near resistance (sell signal)
- Breakout detection
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class SupportResistanceAgent(BaseAgent):
    """
    Agent for Support/Resistance-based trading signals.
    
    Analyzes pivot points and price position relative to
    support and resistance levels.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Support/Resistance agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Support and Resistance levels with pivot point analysis",
                required_features=["pivot", "support_1", "resistance_1", "close", "high", "low", "atr"],
                author="Quant Team",
                tags=["support", "resistance", "pivot", "technical"]
            )
        
        super().__init__(
            agent_name="support_resistance_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._proximity_threshold: float = 0.02
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Support/Resistance-based trading signal.
        
        Args:
            features: Dictionary containing pivot and price data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            close: float = features.get("close", 0)
            high: float = features.get("high", 0)
            low: float = features.get("low", 0)
            pivot: float = features.get("pivot", close)
            support_1: float = features.get("support_1", low)
            resistance_1: float = features.get("resistance_1", high)
            atr: float = features.get("atr", 0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if close <= 0:
                return self._create_error_signal("Invalid close price")
            
            distance_to_support = (close - support_1) / close
            distance_to_resistance = (resistance_1 - close) / close
            distance_to_pivot = abs(close - pivot) / close
            
            if distance_to_support <= self._proximity_threshold:
                signal = "buy"
                confidence = min(80.0, 70.0 + (self._proximity_threshold - distance_to_support) * 500)
                numerical_score = -0.6
                reasoning = (
                    f"Price near support level ({distance_to_support:.2%} from support). "
                    f"Potential bounce expected."
                )
                supporting_data = {
                    "distance_to_support": distance_to_support,
                    "distance_to_resistance": distance_to_resistance,
                    "support_level": support_1,
                    "resistance_level": resistance_1,
                    "signal_type": "near_support"
                }
                
            elif distance_to_resistance <= self._proximity_threshold:
                signal = "sell"
                confidence = min(80.0, 70.0 + (self._proximity_threshold - distance_to_resistance) * 500)
                numerical_score = 0.6
                reasoning = (
                    f"Price near resistance level ({distance_to_resistance:.2%} from resistance). "
                    f"Potential reversal expected."
                )
                supporting_data = {
                    "distance_to_support": distance_to_support,
                    "distance_to_resistance": distance_to_resistance,
                    "support_level": support_1,
                    "resistance_level": resistance_1,
                    "signal_type": "near_resistance"
                }
                
            elif close > resistance_1:
                signal = "buy"
                confidence = 65.0
                numerical_score = -0.4
                reasoning = (
                    f"Breakout above resistance ({resistance_1}). "
                    f"Bullish momentum."
                )
                supporting_data = {
                    "distance_to_support": distance_to_support,
                    "distance_to_resistance": distance_to_resistance,
                    "signal_type": "breakout_above"
                }
                
            elif close < support_1:
                signal = "sell"
                confidence = 65.0
                numerical_score = 0.4
                reasoning = (
                    f"Breakdown below support ({support_1}). "
                    f"Bearish momentum."
                )
                supporting_data = {
                    "distance_to_support": distance_to_support,
                    "distance_to_resistance": distance_to_resistance,
                    "signal_type": "breakdown_below"
                }
                
            else:
                if close > pivot:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = -0.1
                    reasoning = (
                        f"Price above pivot point. Neutral momentum. "
                        f"Distance to resistance: {distance_to_resistance:.2%}"
                    )
                else:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = 0.1
                    reasoning = (
                        f"Price below pivot point. Neutral momentum. "
                        f"Distance to support: {distance_to_support:.2%}"
                    )
                
                supporting_data = {
                    "distance_to_support": distance_to_support,
                    "distance_to_resistance": distance_to_resistance,
                    "distance_to_pivot": distance_to_pivot,
                    "signal_type": "neutral"
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
            return self._create_error_signal(f"Support/Resistance signal computation failed: {str(e)}")
    
    def set_proximity_threshold(self, threshold: float) -> None:
        """Set proximity threshold for support/resistance detection."""
        self._proximity_threshold = threshold
