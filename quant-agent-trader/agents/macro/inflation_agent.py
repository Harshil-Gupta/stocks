"""
Inflation Agent - Inflation trend analysis.

This agent analyzes inflation data to provide trading signals:
- High inflation: typically bearish for bonds, may support commodities
- Low inflation: favorable for bonds and growth stocks
- Inflation trends: rising vs falling inflation expectations
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class InflationAgent(BaseAgent):
    """
    Agent for inflation trend analysis.
    
    Analyzes CPI, PPI, and inflation expectations.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Inflation agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Inflation trend analysis for asset allocation",
                required_features=["cpi", "ppi", "inflation_change", "inflation_expectation"],
                author="Quant Team",
                tags=["macro", "inflation", "cpi", "ppi", "purchasing_power"]
            )
        
        super().__init__(
            agent_name="inflation_agent",
            agent_category=AgentCategory.MACRO,
            metadata=metadata,
            config=config
        )
        
        self._high_inflation_threshold: float = 5.0
        self._low_inflation_threshold: float = 2.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute inflation based trading signal.
        
        Args:
            features: Dictionary containing inflation data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            cpi: float = features.get("cpi", 0.0)
            inflation_change: float = features.get("inflation_change", 0.0)
            inflation_expectation: float = features.get("inflation_expectation", 0.0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if cpi > self._high_inflation_threshold:
                if inflation_change > 0:
                    signal = "sell"
                    confidence = 70.0
                    numerical_score = 0.5
                    reasoning = (
                        f"High inflation ({cpi:.1f}%) with rising trend. "
                        f"Inflation-fighting mode - defensive positioning."
                    )
                else:
                    signal = "hold"
                    confidence = 60.0
                    numerical_score = 0.2
                    reasoning = (
                        f"High inflation ({cpi:.1f}%) but stable/declining. "
                        f"Monitoring for improvement."
                    )
                supporting_data = {
                    "cpi": cpi,
                    "inflation_change": inflation_change,
                    "inflation_expectation": inflation_expectation,
                    "regime": "high_inflation"
                }
                
            elif cpi < self._low_inflation_threshold:
                signal = "buy"
                confidence = 65.0
                numerical_score = -0.4
                reasoning = (
                    f"Low inflation ({cpi:.1f}%). "
                    f"Favorable for bonds and growth equities."
                )
                supporting_data = {
                    "cpi": cpi,
                    "inflation_change": inflation_change,
                    "inflation_expectation": inflation_expectation,
                    "regime": "low_inflation"
                }
                
            else:
                if inflation_change > 0.5:
                    signal = "sell"
                    confidence = 60.0
                    numerical_score = 0.3
                    reasoning = (
                        f"Inflation rising ({inflation_change:.1f}% change). "
                        f"Watch for accelerating inflation."
                    )
                    supporting_data = {
                        "cpi": cpi,
                        "inflation_change": inflation_change,
                        "inflation_expectation": inflation_expectation,
                        "regime": "rising_moderate"
                    }
                else:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = 0.0
                    reasoning = (
                        f"Moderate, stable inflation ({cpi:.1f}%). "
                        f"Normal economic conditions."
                    )
                    supporting_data = {
                        "cpi": cpi,
                        "inflation_change": inflation_change,
                        "inflation_expectation": inflation_expectation,
                        "regime": "moderate_stable"
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
            return self._create_error_signal(f"Inflation signal computation failed: {str(e)}")
