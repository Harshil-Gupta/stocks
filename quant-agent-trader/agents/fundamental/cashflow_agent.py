"""
Cashflow Agent - Cash flow analysis.

This agent analyzes cash flow metrics to identify:
- Companies with strong cash generation (buy signal)
- Companies with weakening cash flow (sell signal)
- Companies with stable cash generation (hold signal)

Metrics analyzed:
- Free Cash Flow (FCF)
- Operating Cash Flow (OCF)
- FCF yield
"""

from typing import Dict, Any, Optional
import numpy as np

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class CashflowAgent(BaseAgent):
    """
    Agent for cash flow-based fundamental analysis.
    
    Analyzes cash flow metrics to determine the financial health
    and cash generation capability of a company.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Cashflow agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Cash flow analysis using FCF, OCF, and FCF yield",
                required_features=["fcf", "operating_cashflow", "fcf_yield"],
                author="Quant Team",
                tags=["fundamental", "cashflow", "fcf", "liquidity"]
            )
        
        super().__init__(
            agent_name="cashflow_agent",
            agent_category=AgentCategory.FUNDAMENTAL,
            metadata=metadata,
            config=config
        )
        
        self._positive_fcf_threshold = 0.0
        self._strong_fcf_yield = 0.05
        self._weak_fcf_yield = 0.02
        self._ocf_to_revenue = 0.10
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute cash flow-based trading signal.
        
        Args:
            features: Dictionary containing cash flow metrics
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            fcf: float = features.get("fcf", 0.0)
            operating_cashflow: float = features.get("operating_cashflow", 0.0)
            fcf_yield: float = features.get("fcf_yield", 0.0)
            previous_fcf: Optional[float] = features.get("previous_fcf")
            previous_ocf: Optional[float] = features.get("previous_ocf")
            
            supporting_data: Dict[str, Any] = {
                "fcf": fcf,
                "operating_cashflow": operating_cashflow,
                "fcf_yield": fcf_yield
            }
            
            if fcf is None or np.isnan(fcf):
                fcf = 0.0
            if operating_cashflow is None or np.isnan(operating_cashflow):
                operating_cashflow = 0.0
            if fcf_yield is None or np.isnan(fcf_yield):
                fcf_yield = 0.0
            
            fcf_growth = 0.0
            if previous_fcf and previous_fcf != 0:
                fcf_growth = (fcf - previous_fcf) / abs(previous_fcf)
                supporting_data["fcf_growth"] = fcf_growth
            
            ocf_growth = 0.0
            if previous_ocf and previous_ocf != 0:
                ocf_growth = (operating_cashflow - previous_ocf) / abs(previous_ocf)
                supporting_data["ocf_growth"] = ocf_growth
            
            signal_indicators = []
            
            if fcf > 0 and (fcf_growth > 0.1 or fcf_growth == 0):
                signal_indicators.append("buy")
            elif fcf < 0 or fcf_growth < -0.2:
                signal_indicators.append("sell")
            else:
                signal_indicators.append("hold")
            
            if operating_cashflow > 0 and (ocf_growth > 0.05 or ocf_growth == 0):
                signal_indicators.append("buy")
            elif operating_cashflow < 0 or ocf_growth < -0.15:
                signal_indicators.append("sell")
            else:
                signal_indicators.append("hold")
            
            if fcf_yield >= self._strong_fcf_yield:
                signal_indicators.append("buy")
            elif fcf_yield <= 0 or fcf_yield < self._weak_fcf_yield:
                signal_indicators.append("sell")
            else:
                signal_indicators.append("hold")
            
            buy_count = signal_indicators.count("buy")
            sell_count = signal_indicators.count("sell")
            
            signal = "hold"
            confidence = 50.0
            numerical_score = 0.0
            reasoning = ""
            
            if buy_count >= 2 and sell_count == 0:
                signal = "buy"
                confidence = min(85.0, 60.0 + fcf_yield * 400)
                numerical_score = min(1.0, fcf_yield * 10 + 0.3)
                reasoning = (
                    f"Strong cash generation: FCF ${fcf:,.0f}, "
                    f"Operating Cash Flow ${operating_cashflow:,.0f}, "
                    f"FCF Yield {fcf_yield:.2%}. "
                    f"Company generating healthy cash flows."
                )
                supporting_data["signal_condition"] = "strong_cashflow"
                
            elif sell_count >= 2 and buy_count == 0:
                signal = "sell"
                confidence = min(85.0, 65.0 + abs(min(0, fcf_yield)) * 400)
                numerical_score = max(-1.0, fcf_yield * 10 - 0.3)
                reasoning = (
                    f"Weak cash generation: FCF ${fcf:,.0f}, "
                    f"Operating Cash Flow ${operating_cashflow:,.0f}, "
                    f"FCF Yield {fcf_yield:.2%}. "
                    f"Company facing cash flow challenges."
                )
                supporting_data["signal_condition"] = "weak_cashflow"
                
            elif buy_count > sell_count:
                signal = "buy"
                confidence = 55.0 + fcf_yield * 200
                numerical_score = fcf_yield * 5
                reasoning = (
                    f"Positive cash flow: FCF ${fcf:,.0f}, "
                    f"FCF Yield {fcf_yield:.2%}. "
                    f"Stable cash generation."
                )
                supporting_data["signal_condition"] = "positive_cashflow"
                
            elif sell_count > buy_count:
                signal = "sell"
                confidence = 55.0
                numerical_score = -0.2
                reasoning = (
                    f"Cash flow concerns: FCF ${fcf:,.0f}, "
                    f"FCF Yield {fcf_yield:.2%}. "
                    f"Monitoring cash generation."
                )
                supporting_data["signal_condition"] = "concerning_cashflow"
                
            else:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.0
                reasoning = (
                    f"Stable cash flow: FCF ${fcf:,.0f}, "
                    f"Operating Cash Flow ${operating_cashflow:,.0f}, "
                    f"FCF Yield {fcf_yield:.2%}. "
                    f"No immediate cash flow concerns."
                )
                supporting_data["signal_condition"] = "stable_cashflow"
            
            if fcf > operating_cashflow * 0.7 and fcf > 0:
                confidence = min(90.0, confidence + 5)
                reasoning += " High FCF conversion from OCF."
            
            if fcf < 0 and operating_cashflow > 0:
                confidence = min(90.0, confidence + 5)
                reasoning += " Negative FCF but positive OCF - high capex investment."
            
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
            return self._create_error_signal(f"Cashflow signal computation failed: {str(e)}")
    
    def set_fcf_thresholds(
        self,
        strong_yield: float,
        weak_yield: float
    ) -> None:
        """
        Set custom FCF yield thresholds.
        
        Args:
            strong_yield: Threshold for strong FCF yield (buy signal)
            weak_yield: Threshold for weak FCF yield
        """
        self._strong_fcf_yield = strong_yield
        self._weak_fcf_yield = weak_yield
    
    def set_ocf_threshold(self, threshold: float) -> None:
        """
        Set OCF to revenue threshold.
        
        Args:
            threshold: Minimum OCF/revenue ratio for positive signal
        """
        self._ocf_to_revenue = threshold
