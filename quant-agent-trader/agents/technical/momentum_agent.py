"""
Momentum Agent - Price momentum across multiple timeframes.

This agent analyzes momentum indicators to identify:
- Strong/weak momentum across short, medium, and long-term periods
- Momentum convergence/divergence between timeframes
- Momentum acceleration/deceleration patterns
- Overextended momentum conditions likely to revert
"""

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory
from features.indicators import TechnicalFeatures


class MomentumAgent(BaseAgent):
    """
    Agent for multi-timeframe momentum analysis.
    
    Analyzes momentum indicators across different timeframes to generate
    buy/sell/hold signals based on momentum strength and direction.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Momentum agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Multi-timeframe momentum analysis for detecting strong/weak momentum and reversals",
                required_features=["momentum_5", "momentum_20", "returns", "volatility_20", "close"],
                author="Quant Team",
                tags=["momentum", "rate_of_change", "multi_timeframe", "technical"]
            )
        
        super().__init__(
            agent_name="momentum_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._strong_momentum_threshold: float = 0.05
        self._weak_momentum_threshold: float = 0.02
        self._oversold_momentum_threshold: float = -0.05
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute momentum-based trading signal.
        
        Args:
            features: Dictionary containing momentum and returns data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            momentum_5: float = features.get("momentum_5", 0.0)
            momentum_20: float = features.get("momentum_20", 0.0)
            returns: float = features.get("returns", 0.0)
            volatility: float = features.get("volatility_20", 0.0)
            close: float = features.get("close", 0.0)
            
            momentum_list: List[float] = [momentum_5, momentum_20]
            momentum_list = [m for m in momentum_list if m is not None and not np.isnan(m)]
            
            if not momentum_list:
                return AgentSignal(
                    agent_name=self._agent_name,
                    agent_category=self._agent_category.value,
                    signal="hold",
                    confidence=50.0,
                    numerical_score=0.0,
                    reasoning="Insufficient momentum data available",
                    supporting_data={"error": "no_data"}
                )
            
            avg_momentum = np.mean(momentum_list)
            momentum_std = np.std(momentum_list) if len(momentum_list) > 1 else 0.0
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {
                "momentum_5": momentum_5,
                "momentum_20": momentum_20,
                "avg_momentum": avg_momentum,
                "volatility": volatility,
                "atr": features.get("atr", 0.0)
            }
            
            strong_momentum = all(m > self._strong_momentum_threshold for m in momentum_list)
            weak_momentum = all(0 < m < self._weak_momentum_threshold for m in momentum_list)
            negative_momentum = all(m < 0 for m in momentum_list)
            oversold_momentum = all(m < self._oversold_momentum_threshold for m in momentum_list)
            
            momentum_accelerating = momentum_5 > momentum_20 > 0 if momentum_20 else False
            momentum_decelerating = momentum_5 < momentum_20 < 0 if momentum_20 else False
            
            if strong_momentum and momentum_accelerating:
                signal = "buy"
                confidence = min(85.0, 70.0 + avg_momentum * 300)
                numerical_score = min(1.0, avg_momentum * 10)
                reasoning = (
                    f"Strong bullish momentum across timeframes: 5-period: {momentum_5:.2%}, "
                    f"20-period: {momentum_20:.2%}. Momentum accelerating. "
                    f"Current volatility: {volatility:.2%}."
                )
                supporting_data["signal_condition"] = "strong_accelerating_bullish"
                
            elif oversold_momentum:
                signal = "buy"
                confidence = min(85.0, 75.0 + abs(avg_momentum) * 300)
                numerical_score = max(-1.0, avg_momentum * 10)
                reasoning = (
                    f"Oversold momentum conditions: 5-period: {momentum_5:.2%}, "
                    f"20-period: {momentum_20:.2%}. High probability of mean reversion bounce. "
                    f"Current volatility: {volatility:.2%}."
                )
                supporting_data["signal_condition"] = "oversold"
                
            elif strong_momentum:
                signal = "buy"
                confidence = 65.0 + avg_momentum * 200
                numerical_score = min(0.8, avg_momentum * 8)
                reasoning = (
                    f"Strong bullish momentum: 5-period: {momentum_5:.2%}, "
                    f"20-period: {momentum_20:.2%}. Uptrend momentum intact. "
                    f"Current volatility: {volatility:.2%}."
                )
                supporting_data["signal_condition"] = "strong_bullish"
                
            elif negative_momentum and momentum_decelerating:
                signal = "sell"
                confidence = min(85.0, 70.0 + abs(avg_momentum) * 300)
                numerical_score = max(-1.0, avg_momentum * 10)
                reasoning = (
                    f"Strong bearish momentum accelerating: 5-period: {momentum_5:.2%}, "
                    f"20-period: {momentum_20:.2%}. Downtrend gaining strength. "
                    f"Current volatility: {volatility:.2%}."
                )
                supporting_data["signal_condition"] = "strong_accelerating_bearish"
                
            elif negative_momentum:
                signal = "sell"
                confidence = 65.0 + abs(avg_momentum) * 200
                numerical_score = max(-0.8, avg_momentum * 8)
                reasoning = (
                    f"Bearish momentum: 5-period: {momentum_5:.2%}, "
                    f"20-period: {momentum_20:.2%}. Downtrend intact. "
                    f"Current volatility: {volatility:.2%}."
                )
                supporting_data["signal_condition"] = "strong_bearish"
                
            elif momentum_accelerating:
                signal = "buy"
                confidence = 60.0
                numerical_score = 0.4
                reasoning = (
                    f"Momentum building: 5-period {momentum_5:.2%} > 20-period {momentum_20:.2%}. "
                    f"Positive momentum acceleration. Current volatility: {volatility:.2%}."
                )
                supporting_data["signal_condition"] = "accelerating_bullish"
                
            elif momentum_decelerating:
                signal = "sell"
                confidence = 60.0
                numerical_score = -0.4
                reasoning = (
                    f"Momentum weakening: 5-period {momentum_5:.2%} < 20-period {momentum_20:.2%}. "
                    f"Negative momentum deceleration. Current volatility: {volatility:.2%}."
                )
                supporting_data["signal_condition"] = "decelerating_bearish"
                
            elif weak_momentum:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.1
                reasoning = (
                    f"Weak momentum across timeframes: 5-period: {momentum_5:.2%}, "
                    f"20-period: {momentum_20:.2%}. No strong directional bias. "
                    f"Current volatility: {volatility:.2%}."
                )
                supporting_data["signal_condition"] = "weak_neutral"
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = avg_momentum * 5
                reasoning = (
                    f"Mixed momentum signals: 5-period: {momentum_5:.2%}, "
                    f"20-period: {momentum_20:.2%}. No clear trend. "
                    f"Current volatility: {volatility:.2%}."
                )
                supporting_data["signal_condition"] = "mixed"
            
            if volatility > 0.05 and confidence > 60:
                confidence *= 0.9
                reasoning += " Reduced confidence due to high volatility."
            
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
            return self._create_error_signal(f"Momentum signal computation failed: {str(e)}")
    
    def set_momentum_thresholds(
        self,
        strong: float,
        weak: float,
        oversold: float
    ) -> None:
        """
        Set custom momentum threshold values.
        
        Args:
            strong: Threshold for strong momentum
            weak: Threshold for weak momentum
            oversold: Threshold for oversold momentum
        """
        self._strong_momentum_threshold = strong
        self._weak_momentum_threshold = weak
        self._oversold_momentum_threshold = oversold
