"""
Commodity Agent - Commodity price analysis.

This agent analyzes commodity prices to provide trading signals:
- Rising commodities: inflation hedge, favorable for commodity producers
- Falling commodities: disinflation signal, favorable for consumers
- Commodity volatility: leading indicator for inflation
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class CommodityAgent(BaseAgent):
    """
    Agent for commodity price analysis.
    
    Analyzes commodity indices and key commodity prices.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Commodity agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Commodity analysis for inflation and sector signals",
                required_features=["commodity_index", "commodity_change", "oil_price", "gold_price"],
                author="Quant Team",
                tags=["macro", "commodity", "oil", "gold", "inflation"]
            )
        
        super().__init__(
            agent_name="commodity_agent",
            agent_category=AgentCategory.MACRO,
            metadata=metadata,
            config=config
        )
        
        self._high_commodity_threshold: float = 10.0
        self._low_commodity_threshold: float = -5.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute commodity based trading signal.
        
        Args:
            features: Dictionary containing commodity data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            commodity_change: float = features.get("commodity_change", 0.0)
            oil_price: float = features.get("oil_price", 0.0)
            gold_price: float = features.get("gold_price", 0.0)
            commodity_volatility: float = features.get("commodity_volatility", 20.0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if commodity_change > self._high_commodity_threshold:
                signal = "sell"
                confidence = 60.0
                numerical_score = 0.3
                reasoning = (
                    f"Rising commodities ({commodity_change:.1f}% change). "
                    f"Inflation risk elevated - defensive positioning."
                )
                supporting_data = {
                    "commodity_change": commodity_change,
                    "oil_price": oil_price,
                    "gold_price": gold_price,
                    "commodity_volatility": commodity_volatility,
                    "regime": "rising_commodities"
                }
                
            elif commodity_change < self._low_commodity_threshold:
                signal = "buy"
                confidence = 60.0
                numerical_score = -0.3
                reasoning = (
                    f"Falling commodities ({commodity_change:.1f}%). "
                    f"Disinflation signal - favorable for equities."
                )
                supporting_data = {
                    "commodity_change": commodity_change,
                    "oil_price": oil_price,
                    "gold_price": gold_price,
                    "commodity_volatility": commodity_volatility,
                    "regime": "falling_commodities"
                }
                
            else:
                if gold_price > 0 and oil_price > 80:
                    signal = "hold"
                    confidence = 55.0
                    numerical_score = 0.1
                    reasoning = (
                        f"High oil (${oil_price:.0f}) with stable commodities. "
                        f"Monitor energy costs."
                    )
                    supporting_data = {
                        "commodity_change": commodity_change,
                        "oil_price": oil_price,
                        "gold_price": gold_price,
                        "commodity_volatility": commodity_volatility,
                        "regime": "high_energy"
                    }
                else:
                    signal = "hold"
                    confidence = 50.0
                    numerical_score = 0.0
                    reasoning = (
                        f"Stable commodity environment ({commodity_change:.1f}%). "
                        f"No significant commodity impact."
                    )
                    supporting_data = {
                        "commodity_change": commodity_change,
                        "oil_price": oil_price,
                        "gold_price": gold_price,
                        "commodity_volatility": commodity_volatility,
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
            return self._create_error_signal(f"Commodity signal computation failed: {str(e)}")
