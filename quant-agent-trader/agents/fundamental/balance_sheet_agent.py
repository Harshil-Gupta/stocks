"""
Balance Sheet Agent - Financial health analysis.

This agent analyzes balance sheet metrics:
- Debt-to-equity ratio
- Current ratio
- Quick ratio
- Asset quality metrics
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class BalanceSheetAgent(BaseAgent):
    """
    Agent for Balance Sheet fundamental analysis.
    
    Analyzes financial health metrics from balance sheet.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Balance Sheet agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Balance sheet health analysis including debt, liquidity, and asset metrics",
                required_features=["debt_to_equity", "current_ratio", "quick_ratio", "total_assets", "total_liabilities"],
                author="Quant Team",
                tags=["balance_sheet", "debt", "liquidity", "fundamental"]
            )
        
        super().__init__(
            agent_name="balance_sheet_agent",
            agent_category=AgentCategory.FUNDAMENTAL,
            metadata=metadata,
            config=config
        )
        
        self._max_debt_equity: float = 2.0
        self._min_current_ratio: float = 1.5
        self._min_quick_ratio: float = 1.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Balance Sheet-based trading signal.
        
        Args:
            features: Dictionary containing balance sheet data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            debt_to_equity: float = features.get("debt_to_equity", 0)
            current_ratio: float = features.get("current_ratio", 1)
            quick_ratio: float = features.get("quick_ratio", 1)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            issues = []
            positive_count = 0
            
            if debt_to_equity > self._max_debt_equity:
                issues.append(f"High debt-to-equity ({debt_to_equity:.2f})")
            else:
                positive_count += 1
                
            if current_ratio < self._min_current_ratio:
                issues.append(f"Weak current ratio ({current_ratio:.2f})")
            else:
                positive_count += 1
                
            if quick_ratio < self._min_quick_ratio:
                issues.append(f"Weak quick ratio ({quick_ratio:.2f})")
            else:
                positive_count += 1
            
            if positive_count >= 2:
                signal = "buy"
                confidence = min(75.0, 55.0 + positive_count * 7)
                numerical_score = -0.4
                reasoning = (
                    f"Strong balance sheet. Debt/Equity: {debt_to_equity:.2f}, "
                    f"Current: {current_ratio:.2f}, Quick: {quick_ratio:.2f}."
                )
                supporting_data = {
                    "debt_to_equity": debt_to_equity,
                    "current_ratio": current_ratio,
                    "quick_ratio": quick_ratio,
                    "signal_type": "healthy"
                }
                
            elif len(issues) >= 2:
                signal = "sell"
                confidence = 65.0
                numerical_score = 0.5
                reasoning = (
                    f"Weak balance sheet. {'; '.join(issues)}."
                )
                supporting_data = {
                    "debt_to_equity": debt_to_equity,
                    "current_ratio": current_ratio,
                    "quick_ratio": quick_ratio,
                    "issues": issues,
                    "signal_type": "weak"
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    f"Mixed balance sheet metrics. {'; '.join(issues) if issues else 'All metrics normal.'}"
                )
                supporting_data = {
                    "debt_to_equity": debt_to_equity,
                    "current_ratio": current_ratio,
                    "quick_ratio": quick_ratio,
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
            return self._create_error_signal(f"Balance Sheet signal computation failed: {str(e)}")
