"""
Industry Comparison Agent - Relative performance analysis.

This agent compares stock metrics to industry averages:
- P/E vs industry average
- ROE vs industry
- Growth vs industry
- Valuation relative to sector
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class IndustryComparisonAgent(BaseAgent):
    """
    Agent for Industry Comparison analysis.
    
    Compares stock metrics to industry averages.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Industry Comparison agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Compare stock metrics to industry averages for relative value",
                required_features=["pe_ratio", "industry_pe", "roe", "industry_roe", "revenue_growth", "industry_growth"],
                author="Quant Team",
                tags=["industry", "comparison", "relative", "fundamental"]
            )
        
        super().__init__(
            agent_name="industry_comparison_agent",
            agent_category=AgentCategory.FUNDAMENTAL,
            metadata=metadata,
            config=config
        )
        
        self._discount_threshold: float = 0.80
        self._premium_threshold: float = 1.20
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Industry Comparison signal.
        
        Args:
            features: Dictionary containing comparison metrics
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            pe_ratio: float = features.get("pe_ratio", 0)
            industry_pe: float = features.get("industry_pe", pe_ratio)
            roe: float = features.get("roe", 0)
            industry_roe: float = features.get("industry_roe", roe)
            revenue_growth: float = features.get("revenue_growth", 0)
            industry_growth: float = features.get("industry_growth", revenue_growth)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            pe_vs_industry = pe_ratio / industry_pe if industry_pe > 0 else 1.0
            roe_vs_industry = roe / industry_roe if industry_roe > 0 else 1.0
            growth_vs_industry = revenue_growth / industry_growth if industry_growth > 0 else 1.0
            
            positive_count = 0
            
            if pe_vs_industry < self._discount_threshold:
                positive_count += 1
            elif pe_vs_industry > self._premium_threshold:
                positive_count -= 1
                
            if roe_vs_industry > 1.2:
                positive_count += 1
            elif roe_vs_industry < 0.8:
                positive_count -= 1
                
            if growth_vs_industry > 1.2:
                positive_count += 1
            elif growth_vs_industry < 0.8:
                positive_count -= 1
            
            if positive_count >= 2:
                signal = "buy"
                confidence = min(75.0, 60.0 + positive_count * 5)
                numerical_score = -0.4
                reasoning = (
                    f"Attractive vs industry: P/E {pe_vs_industry:.0%}, "
                    f"ROE {roe_vs_industry:.0%}, Growth {growth_vs_industry:.0%}."
                )
                supporting_data = {
                    "pe_vs_industry": pe_vs_industry,
                    "roe_vs_industry": roe_vs_industry,
                    "growth_vs_industry": growth_vs_industry,
                    "signal_type": "undervalued"
                }
                
            elif positive_count <= -2:
                signal = "sell"
                confidence = 65.0
                numerical_score = 0.5
                reasoning = (
                    f"Expensive vs industry: P/E {pe_vs_industry:.0%}, "
                    f"ROE {roe_vs_industry:.0%}, Growth {growth_vs_industry:.0%}."
                )
                supporting_data = {
                    "pe_vs_industry": pe_vs_industry,
                    "roe_vs_industry": roe_vs_industry,
                    "growth_vs_industry": growth_vs_industry,
                    "signal_type": "overvalued"
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    f"Trading in-line with industry. "
                    f"P/E: {pe_vs_industry:.0%}, ROE: {roe_vs_industry:.0%}, Growth: {growth_vs_industry:.0%}."
                )
                supporting_data = {
                    "pe_vs_industry": pe_vs_industry,
                    "roe_vs_industry": roe_vs_industry,
                    "growth_vs_industry": growth_vs_industry,
                    "signal_type": "in_line"
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
            return self._create_error_signal(f"Industry Comparison failed: {str(e)}")
