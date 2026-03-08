"""
Correlation Risk Agent - Portfolio correlation analysis.

This agent analyzes correlation risks:
- Stock correlation with portfolio
- Sector correlation
- Beta analysis
- Diversification assessment
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class CorrelationRiskAgent(BaseAgent):
    """
    Agent for Correlation Risk analysis.
    
    Analyzes correlation with portfolio for risk management.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Correlation Risk agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Portfolio correlation and beta analysis for diversification signals",
                required_features=["correlation", "beta", "sector_correlation", "portfolio_beta"],
                author="Quant Team",
                tags=["correlation", "beta", "risk", "diversification"]
            )
        
        super().__init__(
            agent_name="correlation_risk_agent",
            agent_category=AgentCategory.RISK,
            metadata=metadata,
            config=config
        )
        
        self._high_correlation: float = 0.70
        self._high_beta: float = 1.5
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Correlation Risk signal.
        
        Args:
            features: Dictionary containing correlation metrics
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            correlation: float = features.get("correlation", 0)
            beta: float = features.get("beta", 1.0)
            sector_corr: float = features.get("sector_correlation", 0)
            portfolio_beta: float = features.get("portfolio_beta", 1.0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if correlation > self._high_correlation and beta > self._high_beta:
                signal = "sell"
                confidence = 65.0
                numerical_score = 0.5
                reasoning = (
                    f"High correlation ({correlation:.2f}) with high beta ({beta:.2f}). "
                    f"Adds significant risk to portfolio."
                )
                supporting_data = {
                    "correlation": correlation,
                    "beta": beta,
                    "sector_correlation": sector_corr,
                    "signal_type": "high_risk"
                }
                
            elif correlation > self._high_correlation:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.2
                reasoning = (
                    f"High correlation ({correlation:.2f}) with portfolio. "
                    f"Limited diversification benefit."
                )
                supporting_data = {
                    "correlation": correlation,
                    "beta": beta,
                    "signal_type": "high_correlation"
                }
                
            elif beta > self._high_beta:
                signal = "sell"
                confidence = 60.0
                numerical_score = 0.4
                reasoning = (
                    f"High beta ({beta:.2f}) indicates high volatility vs market. "
                    f"Risk contribution elevated."
                )
                supporting_data = {
                    "beta": beta,
                    "portfolio_beta": portfolio_beta,
                    "signal_type": "high_beta"
                }
                
            elif correlation < 0.2 and beta < 1.0:
                signal = "buy"
                confidence = 65.0
                numerical_score = -0.4
                reasoning = (
                    f"Low correlation ({correlation:.2f}) with good beta ({beta:.2f}). "
                    f"Excellent diversification benefit."
                )
                supporting_data = {
                    "correlation": correlation,
                    "beta": beta,
                    "signal_type": "diversifier"
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    f"Normal correlation ({correlation:.2f}) and beta ({beta:.2f})."
                )
                supporting_data = {
                    "correlation": correlation,
                    "beta": beta,
                    "signal_type": "normal"
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
            return self._create_error_signal(f"Correlation Risk signal failed: {str(e)}")
