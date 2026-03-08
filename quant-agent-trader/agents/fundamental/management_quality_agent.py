"""
Management Quality Agent - Management effectiveness analysis.

This agent evaluates management quality:
- Return on capital employed (ROCE)
- Management tenure and experience
- Promoter holding
- Corporate governance metrics
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class ManagementQualityAgent(BaseAgent):
    """
    Agent for Management Quality analysis.
    
    Evaluates management effectiveness and governance.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Management Quality agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Management quality and corporate governance analysis",
                required_features=["roce", "promoter_holding", "pe_ratio", "book_value"],
                author="Quant Team",
                tags=["management", "governance", "quality", "fundamental"]
            )
        
        super().__init__(
            agent_name="management_quality_agent",
            agent_category=AgentCategory.FUNDAMENTAL,
            metadata=metadata,
            config=config
        )
        
        self._min_roce: float = 0.15
        self._min_promoter_holding: float = 0.50
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Management Quality signal.
        
        Args:
            features: Dictionary containing management metrics
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            roce: float = features.get("roce", 0)
            promoter_holding: float = features.get("promoter_holding", 0)
            debt_to_equity: float = features.get("debt_to_equity", 0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            positive_count = 0
            issues = []
            
            if roce >= self._min_roce:
                positive_count += 1
            else:
                issues.append(f"Low ROCE ({roce:.1%})")
                
            if promoter_holding >= self._min_promoter_holding:
                positive_count += 1
            else:
                issues.append(f"Low promoter holding ({promoter_holding:.1%})")
                
            if debt_to_equity < 0.5:
                positive_count += 1
            elif debt_to_equity > 1.5:
                issues.append(f"High leverage ({debt_to_equity:.2f})")
            
            if positive_count >= 2:
                signal = "buy"
                confidence = min(70.0, 55.0 + positive_count * 5)
                numerical_score = -0.3
                reasoning = (
                    f"Quality management. ROCE: {roce:.1%}, "
                    f"Promoter holding: {promoter_holding:.1%}."
                )
                supporting_data = {
                    "roce": roce,
                    "promoter_holding": promoter_holding,
                    "debt_to_equity": debt_to_equity,
                    "signal_type": "high_quality"
                }
                
            elif len(issues) >= 2:
                signal = "sell"
                confidence = 60.0
                numerical_score = 0.4
                reasoning = f"Management concerns. {'; '.join(issues)}."
                supporting_data = {
                    "roce": roce,
                    "promoter_holding": promoter_holding,
                    "debt_to_equity": debt_to_equity,
                    "issues": issues,
                    "signal_type": "concerns"
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = f"Mixed metrics. {'; '.join(issues) if issues else 'Stable.'}"
                supporting_data = {
                    "roce": roce,
                    "promoter_holding": promoter_holding,
                    "debt_to_equity": debt_to_equity,
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
            return self._create_error_signal(f"Management Quality signal failed: {str(e)}")
