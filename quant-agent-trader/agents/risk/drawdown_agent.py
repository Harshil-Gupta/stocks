"""
Drawdown Agent - Portfolio drawdown analysis.

This agent analyzes drawdown conditions:
- Current drawdown from peak
- Maximum drawdown
- Drawdown recovery potential
- Risk assessment based on drawdown
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class DrawdownAgent(BaseAgent):
    """
    Agent for Drawdown analysis.
    
    Analyzes current and historical drawdown for risk signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Drawdown agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Portfolio drawdown analysis for risk management signals",
                required_features=["current_drawdown", "max_drawdown", "drawdown_recovery", "peak_price"],
                author="Quant Team",
                tags=["drawdown", "risk", "portfolio", "losses"]
            )
        
        super().__init__(
            agent_name="drawdown_agent",
            agent_category=AgentCategory.RISK,
            metadata=metadata,
            config=config
        )
        
        self._severe_drawdown: float = 0.20
        self._moderate_drawdown: float = 0.10
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Drawdown-based trading signal.
        
        Args:
            features: Dictionary containing drawdown metrics
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            current_drawdown: float = features.get("current_drawdown", 0)
            max_drawdown: float = features.get("max_drawdown", 0)
            recovery_potential: float = features.get("drawdown_recovery", 0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if abs(current_drawdown) >= self._severe_drawdown:
                signal = "sell"
                confidence = min(80.0, 65.0 + abs(current_drawdown) * 100)
                numerical_score = 0.6
                reasoning = (
                    f"Severe drawdown ({abs(current_drawdown):.1%}). "
                    f"Risk elevated - consider reducing exposure."
                )
                supporting_data = {
                    "current_drawdown": current_drawdown,
                    "max_drawdown": max_drawdown,
                    "signal_type": "severe"
                }
                
            elif abs(current_drawdown) >= self._moderate_drawdown:
                signal = "hold"
                confidence = 60.0
                numerical_score = 0.3
                reasoning = (
                    f"Moderate drawdown ({abs(current_drawdown):.1%}). "
                    f"Monitoring situation."
                )
                supporting_data = {
                    "current_drawdown": current_drawdown,
                    "max_drawdown": max_drawdown,
                    "signal_type": "moderate"
                }
                
            elif recovery_potential > 0.3:
                signal = "buy"
                confidence = 65.0
                numerical_score = -0.4
                reasoning = (
                    f"Recovering from drawdown ({abs(current_drawdown):.1%}). "
                    f"Recovery potential: {recovery_potential:.0%}."
                )
                supporting_data = {
                    "current_drawdown": current_drawdown,
                    "recovery_potential": recovery_potential,
                    "signal_type": "recovery"
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = f"Normal drawdown ({abs(current_drawdown):.1%})."
                supporting_data = {
                    "current_drawdown": current_drawdown,
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
            return self._create_error_signal(f"Drawdown signal failed: {str(e)}")
