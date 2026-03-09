"""
ADX Agent - Average Directional Index analysis.

This agent analyzes ADX to provide signals:
- ADX > 25: strong trend
- ADX < 20: weak trend, ranging market
- +DI and -DI crossover: momentum changes
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class ADXAgent(BaseAgent):
    """
    Agent for Average Directional Index analysis.
    
    Analyzes trend strength and direction.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the ADX agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="ADX signals for trend strength and direction",
                required_features=["adx", "plus_di", "minus_di", "adx_trend"],
                author="Quant Team",
                tags=["technical", "adx", "average_directional_index", "trend_strength"]
            )
        
        super().__init__(
            agent_name="adx_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._strong_trend_threshold: float = 25.0
        self._weak_trend_threshold: float = 20.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute ADX based trading signal.
        
        Args:
            features: Dictionary containing ADX data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            adx: float = features.get("adx", 0.0)
            plus_di: float = features.get("plus_di", 0.0)
            minus_di: float = features.get("minus_di", 0.0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if adx < self._weak_trend_threshold:
                signal = "hold"
                confidence = 45.0
                numerical_score = 0.0
                reasoning = (
                    f"Weak trend (ADX: {adx:.1f}). "
                    f"Ranging market - avoid trend strategies."
                )
                supporting_data = {
                    "adx": adx,
                    "plus_di": plus_di,
                    "minus_di": minus_di,
                    "trend_strength": "weak"
                }
                
            elif adx > self._strong_trend_threshold:
                if plus_di > minus_di:
                    signal = "buy"
                    confidence = 70.0
                    numerical_score = -0.4
                    reasoning = (
                        f"Strong uptrend (ADX: {adx:.1f}). "
                        f"+DI > -DI confirms bullish momentum."
                    )
                    supporting_data = {
                        "adx": adx,
                        "plus_di": plus_di,
                        "minus_di": minus_di,
                        "trend_strength": "strong",
                        "trend_direction": "bullish"
                    }
                else:
                    signal = "sell"
                    confidence = 70.0
                    numerical_score = 0.4
                    reasoning = (
                        f"Strong downtrend (ADX: {adx:.1f}). "
                        f"-DI > +DI confirms bearish momentum."
                    )
                    supporting_data = {
                        "adx": adx,
                        "plus_di": plus_di,
                        "minus_di": minus_di,
                        "trend_strength": "strong",
                        "trend_direction": "bearish"
                    }
                
            else:
                if plus_di > minus_di:
                    signal = "buy"
                    confidence = 55.0
                    numerical_score = -0.2
                    reasoning = (
                        f"Moderate trend (ADX: {adx:.1f}). "
                        f"+DI crossing above -DI."
                    )
                    supporting_data = {
                        "adx": adx,
                        "plus_di": plus_di,
                        "minus_di": minus_di,
                        "trend_strength": "moderate",
                        "trend_direction": "bullish"
                    }
                else:
                    signal = "sell"
                    confidence = 55.0
                    numerical_score = 0.2
                    reasoning = (
                        f"Moderate trend (ADX: {adx:.1f}). "
                        f"-DI crossing above +DI."
                    )
                    supporting_data = {
                        "adx": adx,
                        "plus_di": plus_di,
                        "minus_di": minus_di,
                        "trend_strength": "moderate",
                        "trend_direction": "bearish"
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
            return self._create_error_signal(f"ADX signal computation failed: {str(e)}")
