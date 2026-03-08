"""
Ichimoku Cloud Agent - Ichimoku Cloud indicator analysis.

This agent analyzes the Ichimoku Cloud to provide signals:
- Cloud thickness: support/resistance strength
- Price position relative to cloud: trend direction
- Tenkan-sen/Kijun-sen crossover: momentum signals
- Cloud color (future): trend continuation
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class IchimokuAgent(BaseAgent):
    """
    Agent for Ichimoku Cloud analysis.
    
    Analyzes multiple Ichimoku components for trend signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Ichimoku agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Ichimoku Cloud signals for trend and momentum analysis",
                required_features=["tenkan_sen", "kijun_sen", "senkou_span_a", "senkou_span_b", "chikou_span", "price_position_cloud"],
                author="Quant Team",
                tags=["technical", "ichimoku", "cloud", "japanese", "trend"]
            )
        
        super().__init__(
            agent_name="ichimoku_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Ichimoku-based trading signal.
        
        Args:
            features: Dictionary containing Ichimoku indicator data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            tenkan_sen: float = features.get("tenkan_sen", 0.0)
            kijun_sen: float = features.get("kijun_sen", 0.0)
            senkou_span_a: float = features.get("senkou_span_a", 0.0)
            senkou_span_b: float = features.get("senkou_span_b", 0.0)
            price_position_cloud: str = features.get("price_position_cloud", "below")
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if price_position_cloud == "above":
                tk_cross = tenkan_sen > kijun_sen
                
                if tk_cross:
                    signal = "buy"
                    confidence = 75.0
                    numerical_score = -0.5
                    reasoning = (
                        "Price above cloud with bullish TK crossover. "
                        "Strong bullish signal."
                    )
                else:
                    signal = "buy"
                    confidence = 65.0
                    numerical_score = -0.4
                    reasoning = (
                        "Price above cloud. "
                        "Uptrend confirmed."
                    )
                supporting_data = {
                    "tenkan_sen": tenkan_sen,
                    "kijun_sen": kijun_sen,
                    "senkou_span_a": senkou_span_a,
                    "senkou_span_b": senkou_span_b,
                    "price_position_cloud": price_position_cloud,
                    "tk_cross": tk_cross,
                    "trend": "bullish"
                }
                
            elif price_position_cloud == "below":
                tk_cross = tenkan_sen < kijun_sen
                
                if tk_cross:
                    signal = "sell"
                    confidence = 75.0
                    numerical_score = 0.5
                    reasoning = (
                        "Price below cloud with bearish TK crossover. "
                        "Strong bearish signal."
                    )
                else:
                    signal = "sell"
                    confidence = 65.0
                    numerical_score = 0.4
                    reasoning = (
                        "Price below cloud. "
                        "Downtrend confirmed."
                    )
                supporting_data = {
                    "tenkan_sen": tenkan_sen,
                    "kijun_sen": kijun_sen,
                    "senkou_span_a": senkou_span_a,
                    "senkou_span_b": senkou_span_b,
                    "price_position_cloud": price_position_cloud,
                    "tk_cross": tk_cross,
                    "trend": "bearish"
                }
                
            else:
                cloud_thickness = abs(senkou_span_a - senkou_span_b)
                
                if cloud_thickness < abs(tenkan_sen) * 0.02:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = 0.0
                    reasoning = (
                        "Price inside thin cloud. "
                        "Market in consolidation."
                    )
                    supporting_data = {
                        "tenkan_sen": tenkan_sen,
                        "kijun_sen": kijun_sen,
                        "senkou_span_a": senkou_span_a,
                        "senkou_span_b": senkou_span_b,
                        "price_position_cloud": price_position_cloud,
                        "cloud_thickness": cloud_thickness,
                        "trend": "neutral"
                    }
                else:
                    signal = "hold"
                    confidence = 50.0
                    numerical_score = 0.0
                    reasoning = (
                        "Price inside cloud. "
                        "Waiting for breakout."
                    )
                    supporting_data = {
                        "tenkan_sen": tenkan_sen,
                        "kijun_sen": kijun_sen,
                        "senkou_span_a": senkou_span_a,
                        "senkou_span_b": senkou_span_b,
                        "price_position_cloud": price_position_cloud,
                        "trend": "neutral"
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
            return self._create_error_signal(f"Ichimoku signal computation failed: {str(e)}")
