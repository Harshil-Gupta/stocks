"""
Interest Rate Agent - Interest rate environment analysis.

This agent analyzes interest rate environment to provide trading signals:
- Rising rate environment: typically bearish for stocks, bullish for financials
- Falling rate environment: typically bullish for stocks
- Flat rate environment: neutral to market
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class InterestRateAgent(BaseAgent):
    """
    Agent for interest rate environment analysis.
    
    Analyzes interest rate trends and their impact on market sectors.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Interest Rate agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Interest rate environment analysis for sector allocation",
                required_features=["interest_rate", "rate_change", "rate_direction", "yield_curve"],
                author="Quant Team",
                tags=["macro", "interest_rate", "federal_reserve", "policy"]
            )
        
        super().__init__(
            agent_name="interest_rate_agent",
            agent_category=AgentCategory.MACRO,
            metadata=metadata,
            config=config
        )
        
        self._rate_hike_threshold: float = 0.25
        self._rate_cut_threshold: float = -0.25
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute interest rate based trading signal.
        
        Args:
            features: Dictionary containing interest rate data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            rate_change: float = features.get("rate_change", 0.0)
            rate_direction: str = features.get("rate_direction", "neutral")
            yield_curve: str = features.get("yield_curve", "normal")
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if rate_change > self._rate_hike_threshold:
                signal = "sell"
                confidence = 65.0
                numerical_score = 0.4
                reasoning = (
                    f"Rate hike environment detected (+{rate_change:.2f}%). "
                    f"Reduced exposure to rate-sensitive sectors recommended."
                )
                supporting_data = {
                    "rate_change": rate_change,
                    "rate_direction": rate_direction,
                    "yield_curve": yield_curve,
                    "environment": "hiking"
                }
                
            elif rate_change < self._rate_cut_threshold:
                signal = "buy"
                confidence = 70.0
                numerical_score = -0.5
                reasoning = (
                    f"Rate cut environment detected ({rate_change:.2f}%). "
                    f"Favorable conditions for equities."
                )
                supporting_data = {
                    "rate_change": rate_change,
                    "rate_direction": rate_direction,
                    "yield_curve": yield_curve,
                    "environment": "cutting"
                }
                
            else:
                if yield_curve == "inverted":
                    signal = "sell"
                    confidence = 60.0
                    numerical_score = 0.3
                    reasoning = (
                        "Flat rates with inverted yield curve. "
                        "Recession risk elevated - defensive positioning."
                    )
                    supporting_data = {
                        "rate_change": rate_change,
                        "rate_direction": rate_direction,
                        "yield_curve": yield_curve,
                        "environment": "flat_inverted"
                    }
                else:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = 0.0
                    reasoning = (
                        "Stable rate environment. "
                        "No significant directional bias."
                    )
                    supporting_data = {
                        "rate_change": rate_change,
                        "rate_direction": rate_direction,
                        "yield_curve": yield_curve,
                        "environment": "stable"
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
            return self._create_error_signal(f"Interest rate signal computation failed: {str(e)}")
