"""
ATR Agent - Average True Range volatility analysis.

This agent analyzes ATR (Average True Range) to identify:
- High volatility conditions (large ATR)
- Low volatility conditions (small ATR)
- Volatility breakouts
- Risk assessment based on volatility
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class ATRAgent(BaseAgent):
    """
    Agent for ATR-based volatility signals.
    
    Analyzes Average True Range for volatility-based
    trading signals and risk assessment.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the ATR agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="ATR-based volatility signals for risk assessment and breakout detection",
                required_features=["atr", "close", "volatility_20", "price_position_20"],
                author="Quant Team",
                tags=["atr", "volatility", "risk", "technical"]
            )
        
        super().__init__(
            agent_name="atr_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._low_volatility_threshold: float = 1.5
        self._high_volatility_threshold: float = 4.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute ATR-based trading signal.
        
        Args:
            features: Dictionary containing ATR and volatility data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            atr: float = features.get("atr", 0)
            close: float = features.get("close", 0)
            volatility: float = features.get("volatility_20", 0)
            price_position: float = features.get("price_position_20", 0.5)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if close > 0:
                atr_percent = (atr / close) * 100
            else:
                atr_percent = 0
            
            if atr_percent < self._low_volatility_threshold:
                signal = "hold"
                confidence = 65.0
                numerical_score = 0.1
                reasoning = (
                    f"Low volatility (ATR: {atr_percent:.2f}% of price). "
                    f"Potential breakout may occur. Standing by."
                )
                supporting_data = {
                    "atr_percent": atr_percent,
                    "volatility_regime": "low",
                    "threshold": self._low_volatility_threshold,
                    "atr": atr
                }
                
            elif atr_percent > self._high_volatility_threshold:
                signal = "sell"
                confidence = 60.0
                numerical_score = 0.4
                reasoning = (
                    f"High volatility (ATR: {atr_percent:.2f}% of price). "
                    f"Increased risk - consider reducing exposure."
                )
                supporting_data = {
                    "atr_percent": atr_percent,
                    "volatility_regime": "high",
                    "threshold": self._high_volatility_threshold,
                    "atr": atr
                }
                
            else:
                if volatility > 0.02:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = 0.2
                    reasoning = (
                        f"Moderate volatility (ATR: {atr_percent:.2f}%). "
                        f"Normal market conditions."
                    )
                    supporting_data = {
                        "atr_percent": atr_percent,
                        "volatility_regime": "normal",
                        "atr": atr
                    }
                else:
                    signal = "buy"
                    confidence = 55.0
                    numerical_score = -0.2
                    reasoning = (
                        f"Very low volatility (ATR: {atr_percent:.2f}%). "
                        f"Quiet market - potential for expansion."
                    )
                    supporting_data = {
                        "atr_percent": atr_percent,
                        "volatility_regime": "very_low",
                        "atr": atr
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
            return self._create_error_signal(f"ATR signal computation failed: {str(e)}")
    
    def set_thresholds(self, low: float, high: float) -> None:
        """Set custom volatility thresholds (as percentage of price)."""
        self._low_volatility_threshold = low
        self._high_volatility_threshold = high
