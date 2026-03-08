"""
Put/Call Ratio Agent - Put/call ratio analysis.

This agent analyzes the put/call ratio to provide signals:
- High put/call ratio: bearish sentiment (contrarian bullish)
- Low put/call ratio: bullish sentiment (contrarian bearish)
- Extreme readings: potential reversal signals
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class PutCallRatioAgent(BaseAgent):
    """
    Agent for put/call ratio analysis.
    
    Analyzes market-wide and stock-specific put/call ratios.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Put/Call Ratio agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Put/call ratio for sentiment and reversal signals",
                required_features=["put_call_ratio", "pcr_change", "pcr_ma", "pcr_extreme"],
                author="Quant Team",
                tags=["market_structure", "put_call_ratio", "sentiment", "contrarian"]
            )
        
        super().__init__(
            agent_name="put_call_ratio_agent",
            agent_category=AgentCategory.MARKET_STRUCTURE,
            metadata=metadata,
            config=config
        )
        
        self._fear_threshold: float = 1.5
        self._greed_threshold: float = 0.7
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute put/call ratio based trading signal.
        
        Args:
            features: Dictionary containing put/call ratio data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            put_call_ratio: float = features.get("put_call_ratio", 1.0)
            pcr_change: float = features.get("pcr_change", 0.0)
            pcr_extreme: bool = features.get("pcr_extreme", False)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if put_call_ratio > self._fear_threshold:
                if pcr_extreme:
                    signal = "buy"
                    confidence = 80.0
                    numerical_score = -0.6
                    reasoning = (
                        f"Extreme fear (PCR: {put_call_ratio:.2f}). "
                        f"Contrarian buy signal - capitulation likely."
                    )
                else:
                    signal = "buy"
                    confidence = 65.0
                    numerical_score = -0.4
                    reasoning = (
                        f"High put/call ratio ({put_call_ratio:.2f}). "
                        f"Bearish sentiment - potential bounce."
                    )
                supporting_data = {
                    "put_call_ratio": put_call_ratio,
                    "pcr_change": pcr_change,
                    "sentiment": "fear"
                }
                
            elif put_call_ratio < self._greed_threshold:
                if pcr_extreme:
                    signal = "sell"
                    confidence = 80.0
                    numerical_score = 0.6
                    reasoning = (
                        f"Extreme greed (PCR: {put_call_ratio:.2f}). "
                        f"Contrarian sell signal - euphoria peak."
                    )
                else:
                    signal = "sell"
                    confidence = 65.0
                    numerical_score = 0.4
                    reasoning = (
                        f"Low put/call ratio ({put_call_ratio:.2f}). "
                        f"Bullish sentiment - caution warranted."
                    )
                supporting_data = {
                    "put_call_ratio": put_call_ratio,
                    "pcr_change": pcr_change,
                    "sentiment": "greed"
                }
                
            else:
                if pcr_change > 0.3:
                    signal = "buy"
                    confidence = 60.0
                    numerical_score = -0.3
                    reasoning = (
                        f"PCR rising rapidly ({pcr_change:.2f}). "
                        f"Fear increasing - potential opportunity."
                    )
                    supporting_data = {
                        "put_call_ratio": put_call_ratio,
                        "pcr_change": pcr_change,
                        "sentiment": "rising_fear"
                    }
                elif pcr_change < -0.3:
                    signal = "sell"
                    confidence = 60.0
                    numerical_score = 0.3
                    reasoning = (
                        f"PCR falling rapidly ({pcr_change:.2f}). "
                        f"Greed increasing - caution."
                    )
                    supporting_data = {
                        "put_call_ratio": put_call_ratio,
                        "pcr_change": pcr_change,
                        "sentiment": "rising_greed"
                    }
                else:
                    signal = "hold"
                    confidence = 50.0
                    numerical_score = 0.0
                    reasoning = (
                        f"Neutral put/call ratio ({put_call_ratio:.2f}). "
                        f"No extreme sentiment detected."
                    )
                    supporting_data = {
                        "put_call_ratio": put_call_ratio,
                        "pcr_change": pcr_change,
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
            return self._create_error_signal(f"Put/call ratio signal computation failed: {str(e)}")
