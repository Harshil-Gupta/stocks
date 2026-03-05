"""
Breakout Agent - Support/resistance breakout detection.

This agent identifies breakouts from consolidation patterns:
- Price breaking above resistance levels
- Price breaking below support levels
- Consolidation pattern detection
- Volume confirmation for breakouts
- False breakout detection
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory
from features.indicators import TechnicalFeatures


class BreakoutAgent(BaseAgent):
    """
    Agent for breakout detection from support/resistance levels.
    
    Analyzes price movements relative to pivot points and key levels
    to generate buy/sell/hold signals for breakout trades.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Breakout agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Breakout detection from support/resistance levels with volume confirmation",
                required_features=["close", "high", "low", "volume", "volume_ratio", "atr", "bb_position"],
                author="Quant Team",
                tags=["breakout", "support", "resistance", "pivot", "technical"]
            )
        
        super().__init__(
            agent_name="breakout_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._breakout_threshold: float = 0.02
        self._volume_confirmation_threshold: float = 1.5
        self._consolidation_threshold: float = 0.03
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute breakout-based trading signal.
        
        Args:
            features: Dictionary containing price and volume data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            close: float = features.get("close", 0.0)
            high: float = features.get("high", 0.0)
            low: float = features.get("low", 0.0)
            volume: float = features.get("volume", 0.0)
            volume_ratio: float = features.get("volume_ratio", 1.0)
            atr: float = features.get("atr", 0.0)
            bb_position: float = features.get("bb_position", 0.5)
            
            if close == 0 or atr == 0:
                return AgentSignal(
                    agent_name=self._agent_name,
                    agent_category=self._agent_category.value,
                    signal="hold",
                    confidence=50.0,
                    numerical_score=0.0,
                    reasoning="Insufficient price data for breakout analysis",
                    supporting_data={"error": "no_price_data"}
                )
            
            daily_range = high - low
            range_percent = daily_range / close
            
            at_resistance = bb_position > 0.85
            at_support = bb_position < 0.15
            
            strong_volume = volume_ratio > self._volume_confirmation_threshold
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {
                "close": close,
                "high": high,
                "low": low,
                "volume_ratio": volume_ratio,
                "atr": atr,
                "bb_position": bb_position,
                "range_percent": range_percent
            }
            
            breakout_up = range_percent > self._breakout_threshold and at_resistance
            breakout_down = range_percent > self._breakout_threshold and at_support
            
            if breakout_up and strong_volume:
                signal = "buy"
                confidence = min(85.0, 70.0 + volume_ratio * 10)
                numerical_score = min(1.0, range_percent * 20 + volume_ratio * 0.3)
                reasoning = (
                    f"Bullish breakout detected: Price ({close:.2f}) showing strong upward movement "
                    f"with {range_percent:.2%} range. Volume ratio: {volume_ratio:.2f}x confirms breakout. "
                    f"BB position: {bb_position:.2f} at upper band. ATR: {atr:.2f}."
                )
                supporting_data["signal_condition"] = "confirmed_bullish_breakout"
                supporting_data["breakout_direction"] = "up"
                
            elif breakout_up:
                signal = "buy"
                confidence = 65.0
                numerical_score = 0.6 + range_percent * 10
                reasoning = (
                    f"Bullish breakout forming: Price ({close:.2f}) showing upward movement "
                    f"with {range_percent:.2%} range. Volume ({volume_ratio:.2f}x) below confirmation threshold. "
                    f"BB position: {bb_position:.2f}. Waiting for volume confirmation."
                )
                supporting_data["signal_condition"] = "potential_bullish_breakout"
                supporting_data["breakout_direction"] = "up"
                
            elif breakout_down and strong_volume:
                signal = "sell"
                confidence = min(85.0, 70.0 + volume_ratio * 10)
                numerical_score = -min(1.0, range_percent * 20 + volume_ratio * 0.3)
                reasoning = (
                    f"Bearish breakout detected: Price ({close:.2f}) showing strong downward movement "
                    f"with {range_percent:.2%} range. Volume ratio: {volume_ratio:.2f}x confirms breakdown. "
                    f"BB position: {bb_position:.2f} at lower band. ATR: {atr:.2f}."
                )
                supporting_data["signal_condition"] = "confirmed_bearish_breakout"
                supporting_data["breakout_direction"] = "down"
                
            elif breakout_down:
                signal = "sell"
                confidence = 65.0
                numerical_score = -(0.6 + range_percent * 10)
                reasoning = (
                    f"Bearish breakdown forming: Price ({close:.2f}) showing downward movement "
                    f"with {range_percent:.2%} range. Volume ({volume_ratio:.2f}x) below confirmation threshold. "
                    f"BB position: {bb_position:.2f}. Waiting for volume confirmation."
                )
                supporting_data["signal_condition"] = "potential_bearish_breakout"
                supporting_data["breakout_direction"] = "down"
                
            elif at_resistance and strong_volume:
                signal = "buy"
                confidence = 60.0 + volume_ratio * 10
                numerical_score = 0.5 + volume_ratio * 0.2
                reasoning = (
                    f"Testing resistance: Price ({close:.2f}) at BB upper band ({bb_position:.2f}). "
                    f"Strong volume ({volume_ratio:.2f}x) suggests breakout probability. "
                    f"ATR: {atr:.2f}."
                )
                supporting_data["signal_condition"] = "testing_resistance"
                supporting_data["breakout_direction"] = "up"
                
            elif at_support and strong_volume:
                signal = "sell"
                confidence = 60.0 + volume_ratio * 10
                numerical_score = -(0.5 + volume_ratio * 0.2)
                reasoning = (
                    f"Testing support: Price ({close:.2f}) at BB lower band ({bb_position:.2f}). "
                    f"Strong volume ({volume_ratio:.2f}x) suggests breakdown probability. "
                    f"ATR: {atr:.2f}."
                )
                supporting_data["signal_condition"] = "testing_support"
                supporting_data["breakout_direction"] = "down"
                
            elif 0.3 <= bb_position <= 0.7:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.0
                reasoning = (
                    f"Consolidation phase: Price ({close:.2f}) in middle of Bollinger Bands ({bb_position:.2f}). "
                    f"No clear breakout direction. Range: {range_percent:.2%}. Volume: {volume_ratio:.2f}x. "
                    f"Waiting for breakout from consolidation."
                )
                supporting_data["signal_condition"] = "consolidation"
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.1 if bb_position > 0.5 else -0.1
                reasoning = (
                    f"No breakout signal: Price ({close:.2f}), BB position ({bb_position:.2f}). "
                    f"Range: {range_percent:.2%}, Volume: {volume_ratio:.2f}x. "
                    f"Market in normal range-bound state."
                )
                supporting_data["signal_condition"] = "no_signal"
            
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
            return self._create_error_signal(f"Breakout signal computation failed: {str(e)}")
    
    def set_breakout_thresholds(
        self,
        breakout: float,
        volume_confirmation: float,
        consolidation: float
    ) -> None:
        """
        Set custom breakout threshold values.
        
        Args:
            breakout: Minimum range percent for breakout
            volume_confirmation: Volume ratio for confirmation
            consolidation: Range percent for consolidation
        """
        self._breakout_threshold = breakout
        self._volume_confirmation_threshold = volume_confirmation
        self._consolidation_threshold = consolidation
