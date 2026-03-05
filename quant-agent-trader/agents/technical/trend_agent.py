"""
Trend Agent - Trend detection using moving averages.

This agent analyzes price trends using multiple moving averages to identify:
- Uptrend/downtrend based on price relative to MAs
- Golden cross (bullish) and death cross (bearish) crossovers
- Moving average alignment for trend confirmation
- Trend strength and potential trend changes
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory
from features.indicators import TechnicalFeatures


class TrendAgent(BaseAgent):
    """
    Agent for trend detection using moving averages.
    
    Analyzes price relative to various moving averages and crossover patterns
    to generate buy/sell/hold signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Trend agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Trend detection using moving average crossovers and price alignment",
                required_features=["close", "sma_20", "sma_50", "sma_200", "trend_strength"],
                author="Quant Team",
                tags=["trend", "moving_average", "golden_cross", "death_cross", "technical"]
            )
        
        super().__init__(
            agent_name="trend_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._strong_trend_threshold: float = 0.02
        self._weak_trend_threshold: float = 0.005
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute trend-based trading signal.
        
        Args:
            features: Dictionary containing moving average data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            close: float = features.get("close", 0.0)
            sma_20: float = features.get("sma_20", 0.0)
            sma_50: float = features.get("sma_50", 0.0)
            sma_200: float = features.get("sma_200", 0.0)
            trend_strength: float = features.get("trend_strength", 0.0)
            
            if sma_20 == 0 or sma_50 == 0:
                return AgentSignal(
                    agent_name=self._agent_name,
                    agent_category=self._agent_category.value,
                    signal="hold",
                    confidence=50.0,
                    numerical_score=0.0,
                    reasoning="Insufficient moving average data available",
                    supporting_data={"error": "no_ma_data"}
                )
            
            price_above_sma20 = close > sma_20
            price_above_sma50 = close > sma_50
            price_above_sma200 = close > sma_200
            
            sma20_above_sma50 = sma_20 > sma_50
            sma20_above_sma200 = sma_20 > sma_200
            sma50_above_sma200 = sma_50 > sma_200
            
            golden_cross = sma20_above_sma50 and sma50_above_sma200
            death_cross = sma_20 < sma_50 and sma_50 < sma_200
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {
                "close": close,
                "sma_20": sma_20,
                "sma_50": sma_50,
                "sma_200": sma_200,
                "trend_strength": trend_strength,
                "price_above_sma20": price_above_sma20,
                "price_above_sma50": price_above_sma50,
                "price_above_sma200": price_above_sma200,
                "golden_cross": golden_cross,
                "death_cross": death_cross,
                "atr": features.get("atr", 0.0)
            }
            
            strong_uptrend = (
                price_above_sma20 and price_above_sma50 and price_above_sma200 and
                sma20_above_sma50 and sma50_above_sma200 and
                trend_strength > self._strong_trend_threshold
            )
            
            strong_downtrend = (
                not price_above_sma20 and not price_above_sma50 and not price_above_sma200 and
                not sma20_above_sma50 and not sma50_above_sma200 and
                trend_strength > self._strong_trend_threshold
            )
            
            if strong_uptrend:
                signal = "buy"
                confidence = min(85.0, 75.0 + trend_strength * 500)
                numerical_score = min(1.0, trend_strength * 50)
                reasoning = (
                    f"Strong uptrend confirmed: Price ({close:.2f}) above all MAs. "
                    f"SMA20 ({sma_20:.2f}) > SMA50 ({sma_50:.2f}) > SMA200 ({sma_200:.2f}). "
                    f"Trend strength: {trend_strength:.4f}. Golden cross pattern intact."
                )
                supporting_data["signal_condition"] = "strong_uptrend"
                
            elif strong_downtrend:
                signal = "sell"
                confidence = min(85.0, 75.0 + trend_strength * 500)
                numerical_score = -min(1.0, trend_strength * 50)
                reasoning = (
                    f"Strong downtrend confirmed: Price ({close:.2f}) below all MAs. "
                    f"SMA20 ({sma_20:.2f}) < SMA50 ({sma_50:.2f}) < SMA200 ({sma_200:.2f}). "
                    f"Trend strength: {trend_strength:.4f}. Death cross pattern intact."
                )
                supporting_data["signal_condition"] = "strong_downtrend"
                
            elif golden_cross:
                signal = "buy"
                confidence = 70.0 + trend_strength * 300
                numerical_score = 0.6 + trend_strength * 10
                reasoning = (
                    f"Golden cross forming: SMA20 ({sma_20:.2f}) crossed above SMA50 ({sma_50:.2f}). "
                    f"Price: {close:.2f}. SMA50 > SMA200: {sma50_above_sma200}. "
                    f"Trend strength: {trend_strength:.4f}. Bullish medium-term signal."
                )
                supporting_data["signal_condition"] = "golden_cross"
                
            elif death_cross:
                signal = "sell"
                confidence = 70.0 + trend_strength * 300
                numerical_score = -(0.6 + trend_strength * 10)
                reasoning = (
                    f"Death cross forming: SMA20 ({sma_20:.2f}) crossed below SMA50 ({sma_50:.2f}). "
                    f"Price: {close:.2f}. SMA50 < SMA200: {not sma50_above_sma200}. "
                    f"Trend strength: {trend_strength:.4f}. Bearish medium-term signal."
                )
                supporting_data["signal_condition"] = "death_cross"
                
            elif price_above_sma20 and price_above_sma50:
                signal = "buy"
                confidence = 60.0 + trend_strength * 200
                numerical_score = 0.4 + trend_strength * 10
                reasoning = (
                    f"Bullish trend: Price ({close:.2f}) above short and medium-term MAs. "
                    f"SMA20: {sma_20:.2f}, SMA50: {sma_50:.2f}. "
                    f"Watching for continued strength above SMA200 ({sma_200:.2f})."
                )
                supporting_data["signal_condition"] = "partial_uptrend"
                
            elif not price_above_sma20 and not price_above_sma50:
                signal = "sell"
                confidence = 60.0 + trend_strength * 200
                numerical_score = -(0.4 + trend_strength * 10)
                reasoning = (
                    f"Bearish trend: Price ({close:.2f}) below short and medium-term MAs. "
                    f"SMA20: {sma_20:.2f}, SMA50: {sma_50:.2f}. "
                    f"Watching for continued weakness below SMA200 ({sma_200:.2f})."
                )
                supporting_data["signal_condition"] = "partial_downtrend"
                
            elif trend_strength > self._weak_trend_threshold:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.2 if price_above_sma20 else -0.2
                reasoning = (
                    f"Weak trend detected: Price ({close:.2f}) vs SMA20 ({sma_20:.2f}). "
                    f"Trend strength ({trend_strength:.4f}) below strong threshold. "
                    f"Waiting for clearer trend confirmation."
                )
                supporting_data["signal_condition"] = "weak_trend"
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    f"No clear trend: Price ({close:.2f}), SMA20 ({sma_20:.2f}), "
                    f"SMA50 ({sma_50:.2f}), SMA200 ({sma_200:.2f}). "
                    f"Trend strength: {trend_strength:.4f}. Market likely in consolidation."
                )
                supporting_data["signal_condition"] = "no_trend"
            
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
            return self._create_error_signal(f"Trend signal computation failed: {str(e)}")
    
    def set_trend_thresholds(self, strong: float, weak: float) -> None:
        """
        Set custom trend threshold values.
        
        Args:
            strong: Threshold for strong trend
            weak: Threshold for weak trend
        """
        self._strong_trend_threshold = strong
        self._weak_trend_threshold = weak
