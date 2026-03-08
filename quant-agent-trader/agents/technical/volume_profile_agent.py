"""
Volume Profile Agent - Volume analysis and price-volume relationships.

This agent analyzes volume patterns to identify:
- High volume breakouts
- Low volume consolidations
- Volume-price divergences
- Unusual volume activity
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class VolumeProfileAgent(BaseAgent):
    """
    Agent for Volume Profile-based trading signals.
    
    Analyzes volume patterns and price-volume relationships
    for trading signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Volume Profile agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Volume profile analysis for breakout and trend confirmation",
                required_features=["volume", "volume_ratio", "volume_sma_20", "returns", "close"],
                author="Quant Team",
                tags=["volume", "profile", "breakout", "technical"]
            )
        
        super().__init__(
            agent_name="volume_profile_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._high_volume_threshold: float = 2.0
        self._low_volume_threshold: float = 0.5
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Volume Profile-based trading signal.
        
        Args:
            features: Dictionary containing volume data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            volume: float = features.get("volume", 0)
            volume_ratio: float = features.get("volume_ratio", 1.0)
            volume_sma: float = features.get("volume_sma_20", volume)
            returns: float = features.get("returns", 0)
            close: float = features.get("close", 0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if volume_ratio >= self._high_volume_threshold:
                if returns > 0:
                    signal = "buy"
                    confidence = min(80.0, 65.0 + volume_ratio * 5)
                    numerical_score = -0.5
                    reasoning = (
                        f"High volume ({volume_ratio:.2f}x average) with price increase. "
                        f"Strong bullish breakout signal."
                    )
                elif returns < 0:
                    signal = "sell"
                    confidence = min(80.0, 65.0 + volume_ratio * 5)
                    numerical_score = 0.5
                    reasoning = (
                        f"High volume ({volume_ratio:.2f}x average) with price decrease. "
                        f"Strong bearish breakdown signal."
                    )
                else:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = 0.0
                    reasoning = (
                        f"High volume ({volume_ratio:.2f}x average) but price unchanged. "
                        f"Waiting for directional confirmation."
                    )
                
                supporting_data = {
                    "volume_ratio": volume_ratio,
                    "volume_condition": "high",
                    "returns": returns,
                    "signal_type": "high_volume"
                }
                
            elif volume_ratio <= self._low_volume_threshold:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    f"Low volume ({volume_ratio:.2f}x average). "
                    f"Consolidation phase - waiting for breakout."
                )
                supporting_data = {
                    "volume_ratio": volume_ratio,
                    "volume_condition": "low",
                    "signal_type": "consolidation"
                }
                
            else:
                if returns > 0.02:
                    signal = "buy"
                    confidence = 60.0
                    numerical_score = -0.3
                    reasoning = (
                        f"Moderate volume ({volume_ratio:.2f}x average) with positive returns. "
                        f"Healthy upward momentum."
                    )
                    supporting_data = {
                        "volume_ratio": volume_ratio,
                        "volume_condition": "normal",
                        "returns": returns,
                        "signal_type": "confirming_uptrend"
                    }
                elif returns < -0.02:
                    signal = "sell"
                    confidence = 60.0
                    numerical_score = 0.3
                    reasoning = (
                        f"Moderate volume ({volume_ratio:.2f}x average) with negative returns. "
                        f"Healthy downward momentum."
                    )
                    supporting_data = {
                        "volume_ratio": volume_ratio,
                        "volume_condition": "normal",
                        "returns": returns,
                        "signal_type": "confirming_downtrend"
                    }
                else:
                    signal = "hold"
                    confidence = 50.0
                    numerical_score = 0.0
                    reasoning = (
                        f"Normal volume ({volume_ratio:.2f}x average) with minimal price movement."
                    )
                    supporting_data = {
                        "volume_ratio": volume_ratio,
                        "volume_condition": "normal",
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
            return self._create_error_signal(f"Volume Profile signal computation failed: {str(e)}")
    
    def set_thresholds(self, high: float, low: float) -> None:
        """Set volume threshold multipliers."""
        self._high_volume_threshold = high
        self._low_volume_threshold = low
