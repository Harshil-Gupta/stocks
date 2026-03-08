"""
Dark Pool Agent - Dark pool activity analysis.

This agent analyzes dark pool trading to provide signals:
- Dark pool volume: institutional activity
- Dark pool buying/selling: hidden institutional positions
- Dark pool activity spikes: informed trading
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class DarkPoolAgent(BaseAgent):
    """
    Agent for dark pool activity analysis.
    
    Analyzes off-exchange trading volume and patterns.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Dark Pool agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Dark pool activity analysis for hidden institutional flow",
                required_features=["dark_pool_volume", "dark_pool_ratio", "dark_pool_activity", "dark_pool_direction"],
                author="Quant Team",
                tags=["market_structure", "dark_pool", "institutional", "off_exchange"]
            )
        
        super().__init__(
            agent_name="dark_pool_agent",
            agent_category=AgentCategory.MARKET_STRUCTURE,
            metadata=metadata,
            config=config
        )
        
        self._high_volume_threshold: float = 0.4
        self._spike_threshold: float = 2.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute dark pool based trading signal.
        
        Args:
            features: Dictionary containing dark pool data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            dark_pool_ratio: float = features.get("dark_pool_ratio", 0.15)
            dark_pool_activity: float = features.get("dark_pool_activity", 1.0)
            dark_pool_direction: str = features.get("dark_pool_direction", "neutral")
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if dark_pool_activity > self._spike_threshold:
                if dark_pool_direction == "buy":
                    signal = "buy"
                    confidence = 70.0
                    numerical_score = -0.4
                    reasoning = (
                        f"Dark pool activity spike ({dark_pool_activity:.1f}x) with buying. "
                        f"Hidden institutional accumulation detected."
                    )
                elif dark_pool_direction == "sell":
                    signal = "sell"
                    confidence = 70.0
                    numerical_score = 0.4
                    reasoning = (
                        f"Dark pool activity spike ({dark_pool_activity:.1f}x) with selling. "
                        f"Hidden institutional distribution detected."
                    )
                else:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = 0.0
                    reasoning = (
                        f"Dark pool activity spike ({dark_pool_activity:.1f}x). "
                        f"High institutional interest - monitor."
                    )
                supporting_data = {
                    "dark_pool_ratio": dark_pool_ratio,
                    "dark_pool_activity": dark_pool_activity,
                    "dark_pool_direction": dark_pool_direction,
                    "regime": "spike"
                }
                
            elif dark_pool_ratio > self._high_volume_threshold:
                signal = "hold"
                confidence = 60.0
                numerical_score = 0.1
                reasoning = (
                    f"Elevated dark pool volume ({dark_pool_ratio:.1%}). "
                    f"Significant institutional activity present."
                )
                supporting_data = {
                    "dark_pool_ratio": dark_pool_ratio,
                    "dark_pool_activity": dark_pool_activity,
                    "dark_pool_direction": dark_pool_direction,
                    "regime": "high_volume"
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    f"Normal dark pool activity ({dark_pool_ratio:.1%}). "
                    f"No hidden institutional signals."
                )
                supporting_data = {
                    "dark_pool_ratio": dark_pool_ratio,
                    "dark_pool_activity": dark_pool_activity,
                    "dark_pool_direction": dark_pool_direction,
                    "regime": "normal"
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
            return self._create_error_signal(f"Dark pool signal computation failed: {str(e)}")
