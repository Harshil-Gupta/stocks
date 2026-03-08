"""
Dividend Agent - Dividend yield and payout analysis.

This agent analyzes dividend metrics:
- Dividend yield comparison
- Payout ratio health
- Dividend growth potential
- Ex-dividend date awareness
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class DividendAgent(BaseAgent):
    """
    Agent for Dividend-based fundamental signals.
    
    Analyzes dividend yield, payout ratio, and dividend health.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Dividend agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Dividend yield and payout analysis for income-focused investing",
                required_features=["dividend_yield", "payout_ratio", "eps", "dividend_per_share"],
                author="Quant Team",
                tags=["dividend", "yield", "fundamental", "income"]
            )
        
        super().__init__(
            agent_name="dividend_agent",
            agent_category=AgentCategory.FUNDAMENTAL,
            metadata=metadata,
            config=config
        )
        
        self._min_yield_threshold: float = 1.5
        self._max_payout_ratio: float = 0.80
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Dividend-based trading signal.
        
        Args:
            features: Dictionary containing dividend data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            dividend_yield: float = features.get("dividend_yield", 0)
            payout_ratio: float = features.get("payout_ratio", 0)
            dividend_growth: float = features.get("dividend_growth", 0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if dividend_yield >= self._min_yield_threshold:
                if payout_ratio <= self._max_payout_ratio:
                    signal = "buy"
                    confidence = min(75.0, 60.0 + dividend_yield * 2)
                    numerical_score = -0.5
                    reasoning = (
                        f"Attractive dividend yield ({dividend_yield:.2f}%) with sustainable "
                        f"payout ratio ({payout_ratio:.1%}). Good income potential."
                    )
                    supporting_data = {
                        "dividend_yield": dividend_yield,
                        "payout_ratio": payout_ratio,
                        "dividend_growth": dividend_growth,
                        "signal_type": "attractive_yield"
                    }
                else:
                    signal = "hold"
                    confidence = 50.0
                    numerical_score = 0.0
                    reasoning = (
                        f"High yield ({dividend_yield:.2f}%) but high payout ratio "
                        f"({payout_ratio:.1%}). Sustainability concerns."
                    )
                    supporting_data = {
                        "dividend_yield": dividend_yield,
                        "payout_ratio": payout_ratio,
                        "signal_type": "high_yield_risky"
                    }
                    
            elif payout_ratio > 1.0:
                signal = "sell"
                confidence = 70.0
                numerical_score = 0.6
                reasoning = (
                    f"Payout ratio exceeds 100% ({payout_ratio:.1%}). "
                    f"Dividend is unsustainable."
                )
                supporting_data = {
                    "payout_ratio": payout_ratio,
                    "signal_type": "unsustainable"
                }
                
            elif dividend_yield < 0.5 and payout_ratio < 0.3:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.1
                reasoning = (
                    f"Low dividend yield ({dividend_yield:.2f}%) with low payout. "
                    f"Company may be reinvesting earnings."
                )
                supporting_data = {
                    "dividend_yield": dividend_yield,
                    "payout_ratio": payout_ratio,
                    "signal_type": "reinvestment_mode"
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    f"Moderate dividend metrics. Yield: {dividend_yield:.2f}%, "
                    f"Payout: {payout_ratio:.1%}."
                )
                supporting_data = {
                    "dividend_yield": dividend_yield,
                    "payout_ratio": payout_ratio,
                    "signal_type": "neutral"
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
            return self._create_error_signal(f"Dividend signal computation failed: {str(e)}")
