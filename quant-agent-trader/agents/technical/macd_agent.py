"""
MACD Agent - MACD crossover and histogram analysis.

This agent analyzes the Moving Average Convergence Divergence indicator to identify:
- MACD crossover signals (MACD crossing above/below signal line)
- MACD histogram expansion/contraction for momentum shifts
- Zero-line crossovers for trend direction changes
- MACD divergence with price for potential reversals
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory
from features.indicators import TechnicalFeatures


class MACDAgent(BaseAgent):
    """
    Agent for MACD-based trading signals.
    
    Analyzes MACD indicator including crossovers, histogram, and zero-line
    crossings to generate buy/sell/hold signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the MACD agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="MACD-based trading signals using crossover, histogram, and zero-line analysis",
                required_features=["macd", "macd_signal", "macd_hist", "close"],
                author="Quant Team",
                tags=["macd", "moving_average", "momentum", "technical"]
            )
        
        super().__init__(
            agent_name="macd_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._histogram_strong_threshold: float = 0.5
        self._histogram_weak_threshold: float = 0.1
        self._zero_line_weight: float = 0.3
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute MACD-based trading signal.
        
        Args:
            features: Dictionary containing MACD indicator data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            macd: float = features.get("macd", 0.0)
            macd_signal: float = features.get("macd_signal", 0.0)
            macd_hist: float = features.get("macd_hist", 0.0)
            close: float = features.get("close", 0.0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            macd_above_signal = macd > macd_signal
            macd_below_signal = macd < macd_signal
            macd_above_zero = macd > 0
            macd_below_zero = macd < 0
            
            strong_bullish = macd_above_signal and macd_above_zero and abs(macd_hist) > self._histogram_strong_threshold
            strong_bearish = macd_below_signal and macd_below_zero and abs(macd_hist) > self._histogram_strong_threshold
            
            if strong_bullish:
                signal = "buy"
                confidence = min(90.0, 75.0 + abs(macd_hist) * 30)
                numerical_score = min(1.0, abs(macd_hist) * 2)
                reasoning = (
                    f"Strong bullish MACD signal: MACD ({macd:.4f}) is above signal line ({macd_signal:.4f}) "
                    f"and both are above zero. Histogram: {macd_hist:.4f} shows strong upward momentum."
                )
                supporting_data = {
                    "macd": macd,
                    "macd_signal": macd_signal,
                    "macd_hist": macd_hist,
                    "signal_condition": "strong_bullish",
                    "macd_above_zero": macd_above_zero,
                    "macd_above_signal": macd_above_signal,
                    "atr": features.get("atr", 0.0)
                }
                
            elif strong_bearish:
                signal = "sell"
                confidence = min(90.0, 75.0 + abs(macd_hist) * 30)
                numerical_score = -min(1.0, abs(macd_hist) * 2)
                reasoning = (
                    f"Strong bearish MACD signal: MACD ({macd:.4f}) is below signal line ({macd_signal:.4f}) "
                    f"and both are below zero. Histogram: {macd_hist:.4f} shows strong downward momentum."
                )
                supporting_data = {
                    "macd": macd,
                    "macd_signal": macd_signal,
                    "macd_hist": macd_hist,
                    "signal_condition": "strong_bearish",
                    "macd_below_zero": macd_below_zero,
                    "macd_below_signal": macd_below_signal,
                    "atr": features.get("atr", 0.0)
                }
                
            elif macd_above_signal and macd_above_zero:
                signal = "buy"
                confidence = 60.0 + abs(macd_hist) * 20
                numerical_score = 0.5 + abs(macd_hist) * 0.5
                reasoning = (
                    f"Bullish MACD: MACD ({macd:.4f}) crossed above signal line ({macd_signal:.4f}). "
                    f"MACD above zero confirms uptrend. Histogram: {macd_hist:.4f}."
                )
                supporting_data = {
                    "macd": macd,
                    "macd_signal": macd_signal,
                    "macd_hist": macd_hist,
                    "signal_condition": "bullish_crossover",
                    "macd_above_zero": macd_above_zero,
                    "atr": features.get("atr", 0.0)
                }
                
            elif macd_below_signal and macd_below_zero:
                signal = "sell"
                confidence = 60.0 + abs(macd_hist) * 20
                numerical_score = -(0.5 + abs(macd_hist) * 0.5)
                reasoning = (
                    f"Bearish MACD: MACD ({macd:.4f}) crossed below signal line ({macd_signal:.4f}). "
                    f"MACD below zero confirms downtrend. Histogram: {macd_hist:.4f}."
                )
                supporting_data = {
                    "macd": macd,
                    "macd_signal": macd_signal,
                    "macd_hist": macd_hist,
                    "signal_condition": "bearish_crossover",
                    "macd_below_zero": macd_below_zero,
                    "atr": features.get("atr", 0.0)
                }
                
            elif macd_above_zero and not macd_above_signal:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.2
                reasoning = (
                    f"MACD momentum weakening: MACD ({macd:.4f}) above zero but approaching signal line ({macd_signal:.4f}). "
                    f"Watch for potential bearish crossover. Histogram: {macd_hist:.4f}."
                )
                supporting_data = {
                    "macd": macd,
                    "macd_signal": macd_signal,
                    "macd_hist": macd_hist,
                    "signal_condition": "weakening_bullish",
                    "atr": features.get("atr", 0.0)
                }
                
            elif macd_below_zero and not macd_below_signal:
                signal = "hold"
                confidence = 55.0
                numerical_score = -0.2
                reasoning = (
                    f"MACD momentum weakening: MACD ({macd:.4f}) below zero but approaching signal line ({macd_signal:.4f}). "
                    f"Watch for potential bullish crossover. Histogram: {macd_hist:.4f}."
                )
                supporting_data = {
                    "macd": macd,
                    "macd_signal": macd_signal,
                    "macd_hist": macd_hist,
                    "signal_condition": "weakening_bearish",
                    "atr": features.get("atr", 0.0)
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    f"MACD in transition: MACD ({macd:.4f}), Signal ({macd_signal:.4f}), "
                    f"Histogram ({macd_hist:.4f}). No clear directional signal."
                )
                supporting_data = {
                    "macd": macd,
                    "macd_signal": macd_signal,
                    "macd_hist": macd_hist,
                    "signal_condition": "neutral",
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
            return self._create_error_signal(f"MACD signal computation failed: {str(e)}")
    
    def set_histogram_thresholds(self, strong: float, weak: float) -> None:
        """
        Set custom histogram threshold values.
        
        Args:
            strong: Threshold for strong momentum signal
            weak: Threshold for weak momentum signal
        """
        self._histogram_strong_threshold = strong
        self._histogram_weak_threshold = weak
