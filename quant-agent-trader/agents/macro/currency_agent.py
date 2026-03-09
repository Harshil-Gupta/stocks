"""
Currency Agent - Currency analysis.

This agent analyzes currency movements to provide trading signals:
- Strong dollar: headwind for international stocks, tailwind for importers
- Weak dollar: tailwind for international stocks, headwind for exporters
- Currency volatility: hedging considerations
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class CurrencyAgent(BaseAgent):
    """
    Agent for currency analysis.
    
    Analyzes USD strength and currency volatility.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Currency agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Currency analysis for international positioning",
                required_features=["dollar_index", "dollar_change", "currency_volatility", "export_exposure"],
                author="Quant Team",
                tags=["macro", "currency", "dollar", "fx", "usd"]
            )
        
        super().__init__(
            agent_name="currency_agent",
            agent_category=AgentCategory.MACRO,
            metadata=metadata,
            config=config
        )
        
        self._strong_dollar_threshold: float = 105.0
        self._weak_dollar_threshold: float = 95.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute currency based trading signal.
        
        Args:
            features: Dictionary containing currency data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            dollar_index: float = features.get("dollar_index", 100.0)
            dollar_change: float = features.get("dollar_change", 0.0)
            currency_volatility: float = features.get("currency_volatility", 10.0)
            export_exposure: float = features.get("export_exposure", 0.3)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if dollar_index > self._strong_dollar_threshold:
                if dollar_change > 2:
                    signal = "sell"
                    confidence = 65.0
                    numerical_score = 0.4
                    reasoning = (
                        f"Strong dollar (index: {dollar_index:.1f}) rising. "
                        f"Headwind for international and export-heavy stocks."
                    )
                else:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = 0.2
                    reasoning = (
                        f"Strong dollar (index: {dollar_index:.1f}). "
                        f"Monitoring for stabilization."
                    )
                supporting_data = {
                    "dollar_index": dollar_index,
                    "dollar_change": dollar_change,
                    "currency_volatility": currency_volatility,
                    "regime": "strong_dollar"
                }
                
            elif dollar_index < self._weak_dollar_threshold:
                signal = "buy"
                confidence = 65.0
                numerical_score = -0.4
                reasoning = (
                    f"Weak dollar (index: {dollar_index:.1f}). "
                    f"Favorable for international and export stocks."
                )
                supporting_data = {
                    "dollar_index": dollar_index,
                    "dollar_change": dollar_change,
                    "currency_volatility": currency_volatility,
                    "regime": "weak_dollar"
                }
                
            else:
                if currency_volatility > 15:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = 0.1
                    reasoning = (
                        f"Elevated currency volatility ({currency_volatility:.1f}%). "
                        f"Hedging recommended."
                    )
                    supporting_data = {
                        "dollar_index": dollar_index,
                        "dollar_change": dollar_change,
                        "currency_volatility": currency_volatility,
                        "regime": "high_volatility"
                    }
                else:
                    signal = "hold"
                    confidence = 50.0
                    numerical_score = 0.0
                    reasoning = (
                        f"Stable dollar (index: {dollar_index:.1f}). "
                        f"No significant currency impact."
                    )
                    supporting_data = {
                        "dollar_index": dollar_index,
                        "dollar_change": dollar_change,
                        "currency_volatility": currency_volatility,
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
            return self._create_error_signal(f"Currency signal computation failed: {str(e)}")
