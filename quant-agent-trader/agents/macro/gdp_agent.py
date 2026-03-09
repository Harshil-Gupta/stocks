"""
GDP Agent - GDP growth analysis.

This agent analyzes GDP data to provide trading signals:
- Strong GDP growth: bullish for equities
- Weak/negative GDP: defensive positioning
- GDP acceleration/deceleration: sector rotation signals
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class GDPAgent(BaseAgent):
    """
    Agent for GDP growth analysis.
    
    Analyzes GDP growth rates and trends.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the GDP agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="GDP growth analysis for economic cycle positioning",
                required_features=["gdp_growth", "gdp_change", "gdp_trend", "gdp_forecast"],
                author="Quant Team",
                tags=["macro", "gdp", "economic_growth", "gdp"]
            )
        
        super().__init__(
            agent_name="gdp_agent",
            agent_category=AgentCategory.MACRO,
            metadata=metadata,
            config=config
        )
        
        self._strong_growth_threshold: float = 3.0
        self._weak_growth_threshold: float = 1.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute GDP based trading signal.
        
        Args:
            features: Dictionary containing GDP data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            gdp_growth: float = features.get("gdp_growth", 0.0)
            gdp_change: float = features.get("gdp_change", 0.0)
            gdp_trend: str = features.get("gdp_trend", "stable")
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if gdp_growth > self._strong_growth_threshold:
                signal = "buy"
                confidence = 70.0
                numerical_score = -0.5
                reasoning = (
                    f"Strong GDP growth ({gdp_growth:.1f}%). "
                    f"Economic expansion favors risk assets."
                )
                supporting_data = {
                    "gdp_growth": gdp_growth,
                    "gdp_change": gdp_change,
                    "gdp_trend": gdp_trend,
                    "regime": "strong_growth"
                }
                
            elif gdp_growth < self._weak_growth_threshold:
                if gdp_growth < 0:
                    signal = "sell"
                    confidence = 75.0
                    numerical_score = 0.6
                    reasoning = (
                        f"Negative GDP growth ({gdp_growth:.1f}%). "
                        f"Recession risk - defensive positioning."
                    )
                else:
                    signal = "sell"
                    confidence = 60.0
                    numerical_score = 0.3
                    reasoning = (
                        f"Weak GDP growth ({gdp_growth:.1f}%). "
                        f"Economic slowdown detected."
                    )
                supporting_data = {
                    "gdp_growth": gdp_growth,
                    "gdp_change": gdp_change,
                    "gdp_trend": gdp_trend,
                    "regime": "weak_growth"
                }
                
            else:
                if gdp_change > 0.5:
                    signal = "buy"
                    confidence = 60.0
                    numerical_score = -0.3
                    reasoning = (
                        f"Moderate GDP growth ({gdp_growth:.1f}%) accelerating. "
                        f"Positive economic momentum."
                    )
                    supporting_data = {
                        "gdp_growth": gdp_growth,
                        "gdp_change": gdp_change,
                        "gdp_trend": gdp_trend,
                        "regime": "accelerating"
                    }
                elif gdp_change < -0.5:
                    signal = "sell"
                    confidence = 60.0
                    numerical_score = 0.3
                    reasoning = (
                        f"Moderate GDP growth ({gdp_growth:.1f}%) decelerating. "
                        f"Economic momentum waning."
                    )
                    supporting_data = {
                        "gdp_growth": gdp_growth,
                        "gdp_change": gdp_change,
                        "gdp_trend": gdp_trend,
                        "regime": "decelerating"
                    }
                else:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = 0.0
                    reasoning = (
                        f"Stable GDP growth ({gdp_growth:.1f}%). "
                        f"Steady-state economy."
                    )
                    supporting_data = {
                        "gdp_growth": gdp_growth,
                        "gdp_change": gdp_change,
                        "gdp_trend": gdp_trend,
                        "regime": "stable"
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
            return self._create_error_signal(f"GDP signal computation failed: {str(e)}")
