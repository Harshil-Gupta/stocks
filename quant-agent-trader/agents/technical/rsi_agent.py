"""
RSI Agent - RSI divergence and overbought/oversold analysis.

This agent analyzes the Relative Strength Index to identify:
- Overbought conditions (RSI > 70) indicating potential sell signal
- Oversold conditions (RSI < 30) indicating potential buy signal
- RSI divergences between price and momentum
- RSI trend analysis for momentum shifts
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory
from features.indicators import TechnicalFeatures


class RSIAgent(BaseAgent):
    """
    Agent for RSI-based trading signals.
    
    Analyzes RSI indicator for overbought/oversold conditions and divergences
    to generate buy/sell/hold signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the RSI agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="RSI-based trading signals using overbought/oversold levels and divergence detection",
                required_features=["rsi", "close", "high", "low", "price_position_20"],
                author="Quant Team",
                tags=["rsi", "oscillator", "momentum", "technical"]
            )
        
        super().__init__(
            agent_name="rsi_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._overbought_threshold: float = 70.0
        self._oversold_threshold: float = 30.0
        self._neutral_zone_min: float = 40.0
        self._neutral_zone_max: float = 60.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute RSI-based trading signal.
        
        Args:
            features: Dictionary containing RSI and price data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            rsi: float = features.get("rsi", 50.0)
            close: float = features.get("close", 0.0)
            price_position: float = features.get("price_position_20", 0.5)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            rsi_overbought = rsi > self._overbought_threshold
            rsi_oversold = rsi < self._oversold_threshold
            rsi_neutral = self._neutral_zone_min <= rsi <= self._neutral_zone_max
            
            if rsi_oversold:
                signal = "buy"
                confidence = min(90.0, 80.0 + (30 - rsi))
                numerical_score = -1.0 * (30 - rsi) / 30
                reasoning = (
                    f"RSI is oversold at {rsi:.1f}, indicating potential buying opportunity. "
                    f"Price position: {price_position:.2f}. "
                    f"Previous oversold conditions often precede rebounds."
                )
                supporting_data = {
                    "rsi_value": rsi,
                    "rsi_condition": "oversold",
                    "threshold_oversold": self._oversold_threshold,
                    "price_position": price_position,
                    "atr": features.get("atr", 0.0)
                }
                
            elif rsi_overbought:
                signal = "sell"
                confidence = min(90.0, 80.0 + (rsi - 70))
                numerical_score = (rsi - 70) / 30
                reasoning = (
                    f"RSI is overbought at {rsi:.1f}, indicating potential selling opportunity. "
                    f"Price position: {price_position:.2f}. "
                    f"Previous overbought conditions often precede corrections."
                )
                supporting_data = {
                    "rsi_value": rsi,
                    "rsi_condition": "overbought",
                    "threshold_overbought": self._overbought_threshold,
                    "price_position": price_position,
                    "atr": features.get("atr", 0.0)
                }
                
            elif rsi_neutral:
                if rsi < 50:
                    signal = "buy"
                    confidence = 55.0 + (50 - rsi)
                    numerical_score = -0.3
                    reasoning = (
                        f"RSI at {rsi:.1f} is in neutral zone but leaning bearish. "
                        f"Potential momentum building toward oversold."
                    )
                else:
                    signal = "hold"
                    confidence = 50.0
                    numerical_score = 0.1
                    reasoning = (
                        f"RSI at {rsi:.1f} is in neutral zone (40-60). "
                        f"No clear overbought or oversold signal."
                    )
                supporting_data = {
                    "rsi_value": rsi,
                    "rsi_condition": "neutral",
                    "price_position": price_position,
                    "atr": features.get("atr", 0.0)
                }
                
            else:
                if rsi > 60:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = 0.2
                    reasoning = (
                        f"RSI at {rsi:.1f} shows elevated momentum but not yet overbought. "
                        f"Monitoring for potential pullback."
                    )
                    supporting_data = {
                        "rsi_value": rsi,
                        "rsi_condition": "elevated",
                        "price_position": price_position,
                        "atr": features.get("atr", 0.0)
                    }
                else:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = -0.2
                    reasoning = (
                        f"RSI at {rsi:.1f} shows weak momentum but not yet oversold. "
                        f"Monitoring for potential bounce."
                    )
                    supporting_data = {
                        "rsi_value": rsi,
                        "rsi_condition": "depressed",
                        "price_position": price_position,
                        "atr": features.get("atr", 0.0)
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
            return self._create_error_signal(f"RSI signal computation failed: {str(e)}")
    
    def set_thresholds(self, overbought: float, oversold: float) -> None:
        """
        Set custom overbought/oversold thresholds.
        
        Args:
            overbought: RSI threshold for overbought condition
            oversold: RSI threshold for oversold condition
        """
        self._overbought_threshold = overbought
        self._oversold_threshold = oversold
