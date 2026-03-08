"""
Pairs Trading Agent - Pairs trading signals.

This agent identifies pairs trading opportunities:
- Highly correlated pairs
- Divergence from historical spread
- Convergence trades
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class PairsTradingAgent(BaseAgent):
    """
    Agent for pairs trading signals.
    
    Identifies divergence/convergence in correlated pairs.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Pairs Trading agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Pairs trading signals for correlated securities",
                required_features=["pair_correlation", "spread_deviation", "spread_percentile", "pair_hedge_ratio"],
                author="Quant Team",
                tags=["quant", "pairs_trading", "correlation", "relative_value"]
            )
        
        super().__init__(
            agent_name="pairs_trading_agent",
            agent_category=AgentCategory.QUANT,
            metadata=metadata,
            config=config
        )
        
        self._correlation_threshold: float = 0.7
        self._divergence_threshold: float = 2.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute pairs trading based trading signal.
        
        Args:
            features: Dictionary containing pairs trading data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            pair_correlation: float = features.get("pair_correlation", 0.0)
            spread_deviation: float = features.get("spread_deviation", 0.0)
            spread_percentile: float = features.get("spread_percentile", 0.5)
            pair_hedge_ratio: float = features.get("pair_hedge_ratio", 1.0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if pair_correlation < self._correlation_threshold:
                signal = "hold"
                confidence = 45.0
                numerical_score = 0.0
                reasoning = (
                    f"Weak pair correlation ({pair_correlation:.2f}). "
                    f"Pair may not be suitable for trading."
                )
                supporting_data = {
                    "pair_correlation": pair_correlation,
                    "spread_deviation": spread_deviation,
                    "spread_percentile": spread_percentile,
                    "pair_hedge_ratio": pair_hedge_ratio,
                    "regime": "weak_correlation"
                }
                
            elif abs(spread_deviation) > self._divergence_threshold:
                if spread_deviation > 0:
                    signal = "sell"
                    confidence = 75.0
                    numerical_score = 0.4
                    reasoning = (
                        f"Spread diverged above mean (z: {spread_deviation:.2f}). "
                        f"Long short pair: long underperformer, short overperformer."
                    )
                else:
                    signal = "buy"
                    confidence = 75.0
                    numerical_score = -0.4
                    reasoning = (
                        f"Spread diverged below mean (z: {spread_deviation:.2f}). "
                        f"Long short pair: long overperformer, short underperformer."
                    )
                supporting_data = {
                    "pair_correlation": pair_correlation,
                    "spread_deviation": spread_deviation,
                    "spread_percentile": spread_percentile,
                    "pair_hedge_ratio": pair_hedge_ratio,
                    "regime": "divergence"
                }
                
            elif spread_percentile < 0.1 or spread_percentile > 0.9:
                if spread_percentile < 0.1:
                    signal = "buy"
                    confidence = 65.0
                    numerical_score = -0.3
                    reasoning = (
                        f"Spread at low percentile ({spread_percentile:.1%}). "
                        f"Convergence play."
                    )
                else:
                    signal = "sell"
                    confidence = 65.0
                    numerical_score = 0.3
                    reasoning = (
                        f"Spread at high percentile ({spread_percentile:.1%}). "
                        f"Convergence play."
                    )
                supporting_data = {
                    "pair_correlation": pair_correlation,
                    "spread_deviation": spread_deviation,
                    "spread_percentile": spread_percentile,
                    "pair_hedge_ratio": pair_hedge_ratio,
                    "regime": "extreme_percentile"
                }
                
            else:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.0
                reasoning = (
                    f"Spread near equilibrium ({spread_percentile:.1%} percentile). "
                    f"No clear pairs opportunity."
                )
                supporting_data = {
                    "pair_correlation": pair_correlation,
                    "spread_deviation": spread_deviation,
                    "spread_percentile": spread_percentile,
                    "pair_hedge_ratio": pair_hedge_ratio,
                    "regime": "neutral"
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
            return self._create_error_signal(f"Pairs trading signal computation failed: {str(e)}")
