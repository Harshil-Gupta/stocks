"""
Sector Rotation Agent - Economic cycle sector rotation.

This agent analyzes economic cycle position to recommend sector rotation:
- Early recovery: consumer discretionary, financials
- Mid expansion: industrials, materials
- Late expansion: utilities, consumer staples
- Recession: healthcare, utilities, cash
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class SectorRotationAgent(BaseAgent):
    """
    Agent for sector rotation based on economic cycle.
    
    Recommends overweight/underweight sectors based on cycle position.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Sector Rotation agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Sector rotation based on economic cycle positioning",
                required_features=["economic_cycle", "cycle_position", "leading_indicators", "yield_curve"],
                author="Quant Team",
                tags=["macro", "sector_rotation", "economic_cycle", "rotation"]
            )
        
        super().__init__(
            agent_name="sector_rotation_agent",
            agent_category=AgentCategory.MACRO,
            metadata=metadata,
            config=config
        )
        
        self._cycle_phases = {
            "early_recovery": {
                "signal": "buy",
                "confidence": 70.0,
                "numerical_score": -0.5,
                "reasoning": "Early recovery: cyclicals outperform",
                "recommended_sectors": ["discretionary", "financials", "technology", "real_estate"]
            },
            "mid_expansion": {
                "signal": "buy",
                "confidence": 70.0,
                "numerical_score": -0.4,
                "reasoning": "Mid expansion: cyclical strength continues",
                "recommended_sectors": ["industrials", "materials", "energy", "financials"]
            },
            "late_expansion": {
                "signal": "hold",
                "confidence": 60.0,
                "numerical_score": 0.2,
                "reasoning": "Late expansion: defensive rotation begins",
                "recommended_sectors": ["utilities", "staples", "healthcare"]
            },
            "recession": {
                "signal": "sell",
                "confidence": 75.0,
                "numerical_score": 0.5,
                "reasoning": "Recession: defensive positioning only",
                "recommended_sectors": ["utilities", "healthcare", "cash"]
            }
        }
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute sector rotation signal.
        
        Args:
            features: Dictionary containing economic cycle data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            cycle_phase: str = features.get("economic_cycle", "mid_expansion")
            leading_indicators: float = features.get("leading_indicators", 50.0)
            
            phase_data = self._cycle_phases.get(
                cycle_phase, 
                self._cycle_phases["mid_expansion"]
            )
            
            confidence = phase_data["confidence"]
            numerical_score = phase_data["numerical_score"]
            reasoning = phase_data["reasoning"]
            recommended_sectors = phase_data["recommended_sectors"]
            
            if leading_indicators < 40:
                confidence = min(confidence + 10, 90)
                numerical_score = max(numerical_score + 0.2, 0.8)
                reasoning += " (weak leading indicators amplify signal)"
            elif leading_indicators > 60:
                confidence = min(confidence + 5, 90)
                numerical_score = max(numerical_score - 0.1, -0.8)
                reasoning += " (strong leading indicators)"
            
            supporting_data = {
                "cycle_phase": cycle_phase,
                "leading_indicators": leading_indicators,
                "recommended_sectors": recommended_sectors
            }
            
            return AgentSignal(
                agent_name=self._agent_name,
                agent_category=self._agent_category.value,
                signal=phase_data["signal"],
                confidence=confidence,
                numerical_score=numerical_score,
                reasoning=reasoning,
                supporting_data=supporting_data
            )
            
        except Exception as e:
            return self._create_error_signal(f"Sector rotation signal computation failed: {str(e)}")
