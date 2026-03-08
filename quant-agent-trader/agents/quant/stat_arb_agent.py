"""
Statistical Arbitrage Agent - Stat arb trading signals.

This agent identifies statistical arbitrage opportunities:
- Cointegration breakouts
- Spread deviations from historical norms
- Pair convergence opportunities
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class StatArbAgent(BaseAgent):
    """
    Agent for statistical arbitrage signals.
    
    Identifies spread deviations and convergence opportunities.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Stat Arb agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Statistical arbitrage signals for spread deviations",
                required_features=["spread_z_score", "spread_deviation", "half_life", "cointegration_pvalue"],
                author="Quant Team",
                tags=["quant", "stat_arb", "statistical", "arbitrage", "spread"]
            )
        
        super().__init__(
            agent_name="stat_arb_agent",
            agent_category=AgentCategory.QUANT,
            metadata=metadata,
            config=config
        )
        
        self._entry_threshold: float = 2.0
        self._exit_threshold: float = 0.5
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute statistical arbitrage based trading signal.
        
        Args:
            features: Dictionary containing stat arb indicators
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            spread_z_score: float = features.get("spread_z_score", 0.0)
            spread_deviation: float = features.get("spread_deviation", 0.0)
            half_life: float = features.get("half_life", 20.0)
            cointegration_pvalue: float = features.get("cointegration_pvalue", 0.05)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if cointegration_pvalue > 0.05:
                signal = "hold"
                confidence = 40.0
                numerical_score = 0.0
                reasoning = (
                    f"Weak cointegration (p-value: {cointegration_pvalue:.3f}). "
                    f"Stat arb signal unreliable."
                )
                supporting_data = {
                    "spread_z_score": spread_z_score,
                    "spread_deviation": spread_deviation,
                    "half_life": half_life,
                    "cointegration_pvalue": cointegration_pvalue,
                    "regime": "weak_cointegration"
                }
                
            elif abs(spread_z_score) > self._entry_threshold:
                if spread_z_score > 0:
                    signal = "sell"
                    confidence = 75.0
                    numerical_score = 0.4
                    reasoning = (
                        f"Spread significantly above mean (z: {spread_z_score:.2f}). "
                        f"Expect mean reversion."
                    )
                else:
                    signal = "buy"
                    confidence = 75.0
                    numerical_score = -0.4
                    reasoning = (
                        f"Spread significantly below mean (z: {spread_z_score:.2f}). "
                        f"Expect mean reversion."
                    )
                
                if half_life < 20:
                    confidence = min(confidence + 5, 90)
                    reasoning += f" Short half-life ({half_life:.1f} days) supports trade."
                
                supporting_data = {
                    "spread_z_score": spread_z_score,
                    "spread_deviation": spread_deviation,
                    "half_life": half_life,
                    "cointegration_pvalue": cointegration_pvalue,
                    "regime": "entry_signal"
                }
                
            elif abs(spread_z_score) < self._exit_threshold:
                signal = "hold"
                confidence = 60.0
                numerical_score = 0.0
                reasoning = (
                    f"Spread near equilibrium (z: {spread_z_score:.2f}). "
                    f"Close stat arb position."
                )
                supporting_data = {
                    "spread_z_score": spread_z_score,
                    "spread_deviation": spread_deviation,
                    "half_life": half_life,
                    "cointegration_pvalue": cointegration_pvalue,
                    "regime": "exit_signal"
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    f"Spread in reversion zone (z: {spread_z_score:.2f}). "
                    f"Monitoring for entry."
                )
                supporting_data = {
                    "spread_z_score": spread_z_score,
                    "spread_deviation": spread_deviation,
                    "half_life": half_life,
                    "cointegration_pvalue": cointegration_pvalue,
                    "regime": "monitoring"
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
            return self._create_error_signal(f"Stat arb signal computation failed: {str(e)}")
