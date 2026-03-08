"""
Mean Reversion Agent - Mean reversion trading signals.

This agent identifies mean reversion opportunities:
- Price deviated significantly from moving average
- Bollinger Band breakout returning to mean
- RSI extreme readings with price reversion
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class MeanReversionAgent(BaseAgent):
    """
    Agent for mean reversion trading signals.
    
    Identifies when price is likely to revert to mean/average.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Mean Reversion agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Mean reversion signals for oversold/overbought conditions",
                required_features=["price_deviation", "ma_distance", "rsi", "bollinger_position", "z_score"],
                author="Quant Team",
                tags=["quant", "mean_reversion", "reversion", "statistical"]
            )
        
        super().__init__(
            agent_name="mean_reversion_agent",
            agent_category=AgentCategory.QUANT,
            metadata=metadata,
            config=config
        )
        
        self._deviation_threshold: float = 2.0
        self._reversion_threshold: float = 0.5
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute mean reversion based trading signal.
        
        Args:
            features: Dictionary containing mean reversion indicators
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            z_score: float = features.get("z_score", 0.0)
            rsi: float = features.get("rsi", 50.0)
            bollinger_position: float = features.get("bollinger_position", 0.5)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if abs(z_score) > self._deviation_threshold:
                if z_score > 0:
                    signal = "sell"
                    confidence = 70.0
                    numerical_score = 0.4
                    reasoning = (
                        f"Price significantly above mean (z-score: {z_score:.2f}). "
                        f"Expect reversion lower."
                    )
                else:
                    signal = "buy"
                    confidence = 70.0
                    numerical_score = -0.4
                    reasoning = (
                        f"Price significantly below mean (z-score: {z_score:.2f}). "
                        f"Expect reversion higher."
                    )
                supporting_data = {
                    "z_score": z_score,
                    "rsi": rsi,
                    "bollinger_position": bollinger_position,
                    "regime": "extreme_deviation"
                }
                
            elif rsi < 30:
                signal = "buy"
                confidence = 65.0
                numerical_score = -0.4
                reasoning = (
                    f"Oversold RSI ({rsi:.1f}). "
                    f"Mean reversion opportunity."
                )
                supporting_data = {
                    "z_score": z_score,
                    "rsi": rsi,
                    "bollinger_position": bollinger_position,
                    "regime": "oversold"
                }
                
            elif rsi > 70:
                signal = "sell"
                confidence = 65.0
                numerical_score = 0.4
                reasoning = (
                    f"Overbought RSI ({rsi:.1f}). "
                    f"Mean reversion opportunity."
                )
                supporting_data = {
                    "z_score": z_score,
                    "rsi": rsi,
                    "bollinger_position": bollinger_position,
                    "regime": "overbought"
                }
                
            else:
                if bollinger_position < 0.1:
                    signal = "buy"
                    confidence = 60.0
                    numerical_score = -0.3
                    reasoning = (
                        f"Near lower Bollinger Band. "
                        f"Potential mean reversion."
                    )
                    supporting_data = {
                        "z_score": z_score,
                        "rsi": rsi,
                        "bollinger_position": bollinger_position,
                        "regime": "lower_band"
                    }
                elif bollinger_position > 0.9:
                    signal = "sell"
                    confidence = 60.0
                    numerical_score = 0.3
                    reasoning = (
                        f"Near upper Bollinger Band. "
                        f"Potential mean reversion."
                    )
                    supporting_data = {
                        "z_score": z_score,
                        "rsi": rsi,
                        "bollinger_position": bollinger_position,
                        "regime": "upper_band"
                    }
                else:
                    signal = "hold"
                    confidence = 50.0
                    numerical_score = 0.0
                    reasoning = (
                        f"No significant mean reversion signal. "
                        f"Price near mean."
                    )
                    supporting_data = {
                        "z_score": z_score,
                        "rsi": rsi,
                        "bollinger_position": bollinger_position,
                        "regime": "near_mean"
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
            return self._create_error_signal(f"Mean reversion signal computation failed: {str(e)}")
