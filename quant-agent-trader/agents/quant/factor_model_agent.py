"""
Factor Model Agent - Factor-based trading signals.

This agent uses factor models to generate signals:
- Momentum factor
- Value factor
- Size factor
- Quality factor
- Volatility factor
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class FactorModelAgent(BaseAgent):
    """
    Agent for factor-based trading signals.
    
    Uses multi-factor model for stock selection and signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Factor Model agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Factor-based signals using momentum, value, quality factors",
                required_features=["momentum_factor", "value_factor", "quality_factor", "size_factor", "volatility_factor", "factor_composite"],
                author="Quant Team",
                tags=["quant", "factor", "factor_model", "multi_factor", "smart_beta"]
            )
        
        super().__init__(
            agent_name="factor_model_agent",
            agent_category=AgentCategory.QUANT,
            metadata=metadata,
            config=config
        )
        
        self._strong_factor_threshold: float = 1.0
        self._weak_factor_threshold: float = -1.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute factor model based trading signal.
        
        Args:
            features: Dictionary containing factor data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            factor_composite: float = features.get("factor_composite", 0.0)
            momentum_factor: float = features.get("momentum_factor", 0.0)
            value_factor: float = features.get("value_factor", 0.0)
            quality_factor: float = features.get("quality_factor", 0.0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if factor_composite > self._strong_factor_threshold:
                signal = "buy"
                confidence = 75.0
                numerical_score = -0.5
                reasoning = (
                    f"Strong factor composite ({factor_composite:.2f}). "
                    f"Favorable factor exposure."
                )
                supporting_data = {
                    "factor_composite": factor_composite,
                    "momentum_factor": momentum_factor,
                    "value_factor": value_factor,
                    "quality_factor": quality_factor,
                    "regime": "strong_factors"
                }
                
            elif factor_composite < self._weak_factor_threshold:
                signal = "sell"
                confidence = 75.0
                numerical_score = 0.5
                reasoning = (
                    f"Weak factor composite ({factor_composite:.2f}). "
                    f"Unfavorable factor exposure."
                )
                supporting_data = {
                    "factor_composite": factor_composite,
                    "momentum_factor": momentum_factor,
                    "value_factor": value_factor,
                    "quality_factor": quality_factor,
                    "regime": "weak_factors"
                }
                
            else:
                dominant_factor = max(
                    [("momentum", momentum_factor), ("value", value_factor), ("quality", quality_factor)],
                    key=lambda x: abs(x[1])
                )
                
                if dominant_factor[1] > 0.5:
                    signal = "buy"
                    confidence = 60.0
                    numerical_score = -0.3
                    reasoning = (
                        f"Strong {dominant_factor[0]} factor ({dominant_factor[1]:.2f}). "
                        f"Single-factor opportunity."
                    )
                    supporting_data = {
                        "factor_composite": factor_composite,
                        "momentum_factor": momentum_factor,
                        "value_factor": value_factor,
                        "quality_factor": quality_factor,
                        "dominant_factor": dominant_factor[0],
                        "regime": "single_factor"
                    }
                elif dominant_factor[1] < -0.5:
                    signal = "sell"
                    confidence = 60.0
                    numerical_score = 0.3
                    reasoning = (
                        f"Weak {dominant_factor[0]} factor ({dominant_factor[1]:.2f}). "
                        f"Avoid due to negative factor."
                    )
                    supporting_data = {
                        "factor_composite": factor_composite,
                        "momentum_factor": momentum_factor,
                        "value_factor": value_factor,
                        "quality_factor": quality_factor,
                        "dominant_factor": dominant_factor[0],
                        "regime": "single_factor_negative"
                    }
                else:
                    signal = "hold"
                    confidence = 50.0
                    numerical_score = 0.0
                    reasoning = (
                        f"Mixed factor signals. "
                        f"Neutral composite ({factor_composite:.2f})."
                    )
                    supporting_data = {
                        "factor_composite": factor_composite,
                        "momentum_factor": momentum_factor,
                        "value_factor": value_factor,
                        "quality_factor": quality_factor,
                        "regime": "mixed"
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
            return self._create_error_signal(f"Factor model signal computation failed: {str(e)}")
