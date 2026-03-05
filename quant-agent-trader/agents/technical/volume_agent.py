"""
Volume Agent - Volume analysis and anomalies.

This agent analyzes volume patterns to identify:
- Volume spikes indicating institutional activity
- Volume divergences with price
- Low volume consolidation periods
- Volume trend confirmation
- Abnormal volume patterns for potential reversals
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory
from features.indicators import TechnicalFeatures


class VolumeAgent(BaseAgent):
    """
    Agent for volume-based trading signals.
    
    Analyzes volume patterns relative to price movements to generate
    buy/sell/hold signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Volume agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Volume analysis for detecting institutional activity, anomalies, and trend confirmation",
                required_features=["volume", "volume_ratio", "returns", "close", "price_position_20"],
                author="Quant Team",
                tags=["volume", "volume_anomaly", "institutional", "technical"]
            )
        
        super().__init__(
            agent_name="volume_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._high_volume_threshold: float = 2.0
        self._low_volume_threshold: float = 0.5
        self._spike_threshold: float = 3.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute volume-based trading signal.
        
        Args:
            features: Dictionary containing volume and price data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            volume: float = features.get("volume", 0.0)
            volume_ratio: float = features.get("volume_ratio", 1.0)
            returns: float = features.get("returns", 0.0)
            close: float = features.get("close", 0.0)
            price_position: float = features.get("price_position_20", 0.5)
            
            if volume == 0:
                return AgentSignal(
                    agent_name=self._agent_name,
                    agent_category=self._agent_category.value,
                    signal="hold",
                    confidence=50.0,
                    numerical_score=0.0,
                    reasoning="Insufficient volume data available",
                    supporting_data={"error": "no_volume_data"}
                )
            
            price_up = returns > 0
            price_down = returns < 0
            
            high_volume = volume_ratio > self._high_volume_threshold
            low_volume = volume_ratio < self._low_volume_threshold
            volume_spike = volume_ratio > self._spike_threshold
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {
                "volume": volume,
                "volume_ratio": volume_ratio,
                "returns": returns,
                "price_position": price_position,
                "atr": features.get("atr", 0.0)
            }
            
            if high_volume and price_up:
                signal = "buy"
                confidence = min(80.0, 60.0 + volume_ratio * 10)
                numerical_score = min(1.0, volume_ratio * 0.4 + returns * 5)
                reasoning = (
                    f"Bullish volume confirmation: High volume ({volume_ratio:.2f}x average) "
                    f"accompanies price increase ({returns:.2%}). Strong buying conviction. "
                    f"Price position: {price_position:.2f}."
                )
                supporting_data["signal_condition"] = "bullish_volume_confirmation"
                
            elif high_volume and price_down:
                signal = "sell"
                confidence = min(80.0, 60.0 + volume_ratio * 10)
                numerical_score = -min(1.0, volume_ratio * 0.4 + abs(returns) * 5)
                reasoning = (
                    f"Bearish volume confirmation: High volume ({volume_ratio:.2f}x average) "
                    f"accompanies price decrease ({returns:.2%}). Strong selling conviction. "
                    f"Price position: {price_position:.2f}."
                )
                supporting_data["signal_condition"] = "bearish_volume_confirmation"
                
            elif volume_spike and price_up:
                signal = "buy"
                confidence = min(85.0, 65.0 + volume_ratio * 7)
                numerical_score = min(1.0, volume_ratio * 0.3 + returns * 5)
                reasoning = (
                    f"Strong bullish breakout signal: Volume spike ({volume_ratio:.2f}x) "
                    f"with price increase ({returns:.2%}). Likely institutional buying. "
                    f"Price position: {price_position:.2f}."
                )
                supporting_data["signal_condition"] = "bullish_volume_spike"
                
            elif volume_spike and price_down:
                signal = "sell"
                confidence = min(85.0, 65.0 + volume_ratio * 7)
                numerical_score = -min(1.0, volume_ratio * 0.3 + abs(returns) * 5)
                reasoning = (
                    f"Strong bearish breakdown signal: Volume spike ({volume_ratio:.2f}x) "
                    f"with price decrease ({returns:.2%}). Likely institutional selling. "
                    f"Price position: {price_position:.2f}."
                )
                supporting_data["signal_condition"] = "bearish_volume_spike"
                
            elif low_volume and price_up:
                signal = "buy"
                confidence = 55.0
                numerical_score = 0.3
                reasoning = (
                    f"Weak bullish signal: Low volume ({volume_ratio:.2f}x) with price increase. "
                    f"Price movement lacks conviction. Price position: {price_position:.2f}. "
                    f"May indicate accumulation phase."
                )
                supporting_data["signal_condition"] = "low_volume_bullish"
                
            elif low_volume and price_down:
                signal = "sell"
                confidence = 55.0
                numerical_score = -0.3
                reasoning = (
                    f"Weak bearish signal: Low volume ({volume_ratio:.2f}x) with price decrease. "
                    f"Price movement lacks conviction. Price position: {price_position:.2f}. "
                    f"May indicate distribution phase."
                )
                supporting_data["signal_condition"] = "low_volume_bearish"
                
            elif low_volume and 0.3 <= price_position <= 0.7:
                signal = "hold"
                confidence = 60.0
                numerical_score = 0.0
                reasoning = (
                    f"Consolidation detected: Low volume ({volume_ratio:.2f}x) with price "
                    f"in neutral position ({price_position:.2f}). Market in wait-and-see mode. "
                    f"Expected breakout soon."
                )
                supporting_data["signal_condition"] = "consolidation_low_volume"
                
            elif volume_ratio > 1.0:
                signal = "buy" if price_up else "sell"
                confidence = 55.0
                numerical_score = 0.2 if price_up else -0.2
                direction = "upward" if price_up else "downward"
                reasoning = (
                    f"Above-average volume ({volume_ratio:.2f}x) accompanying {direction} move. "
                    f"Moderate conviction. Returns: {returns:.2%}. "
                    f"Price position: {price_position:.2f}."
                )
                supporting_data["signal_condition"] = "moderate_volume"
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    f"Normal volume conditions ({volume_ratio:.2f}x). No significant "
                    f"volume anomalies detected. Returns: {returns:.2%}. "
                    f"Waiting for volume confirmation."
                )
                supporting_data["signal_condition"] = "normal_volume"
            
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
            return self._create_error_signal(f"Volume signal computation failed: {str(e)}")
    
    def set_volume_thresholds(
        self,
        high: float,
        low: float,
        spike: float
    ) -> None:
        """
        Set custom volume threshold values.
        
        Args:
            high: Threshold for high volume
            low: Threshold for low volume
            spike: Threshold for volume spike
        """
        self._high_volume_threshold = high
        self._low_volume_threshold = low
        self._spike_threshold = spike
