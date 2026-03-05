"""
Growth Agent - Growth analysis.

This agent analyzes growth metrics to identify:
- High growth companies at reasonable valuations (buy signal)
- Declining growth companies (sell signal)
- Moderate/stable growth companies (hold signal)

Metrics analyzed:
- Revenue growth rate
- Earnings growth rate
- PEG ratio (P/E divided by earnings growth rate)
"""

from typing import Dict, Any, Optional
import numpy as np

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class GrowthAgent(BaseAgent):
    """
    Agent for growth-based fundamental analysis.
    
    Analyzes growth metrics and valuation to identify companies
    with strong growth at reasonable prices.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Growth agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Growth analysis using revenue growth, earnings growth, and PEG ratio",
                required_features=["revenue_growth", "earnings_growth", "peg_ratio"],
                author="Quant Team",
                tags=["fundamental", "growth", "revenue", "earnings", "peg"]
            )
        
        super().__init__(
            agent_name="growth_agent",
            agent_category=AgentCategory.FUNDAMENTAL,
            metadata=metadata,
            config=config
        )
        
        self._high_growth_threshold = 0.20
        self._moderate_growth_threshold = 0.10
        self._decline_threshold = -0.05
        self._buy_peg_threshold = 1.0
        self._sell_peg_threshold = 2.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute growth-based trading signal.
        
        Args:
            features: Dictionary containing growth metrics
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            revenue_growth: float = features.get("revenue_growth", 0.0)
            earnings_growth: float = features.get("earnings_growth", 0.0)
            peg_ratio: Optional[float] = features.get("peg_ratio")
            
            supporting_data: Dict[str, Any] = {
                "revenue_growth": revenue_growth,
                "earnings_growth": earnings_growth,
                "peg_ratio": peg_ratio
            }
            
            if revenue_growth is None or np.isnan(revenue_growth):
                revenue_growth = 0.0
            if earnings_growth is None or np.isnan(earnings_growth):
                earnings_growth = 0.0
            
            avg_growth = (revenue_growth + earnings_growth) / 2
            
            signal_indicators = []
            
            if revenue_growth >= self._high_growth_threshold:
                signal_indicators.append("buy")
            elif revenue_growth <= self._decline_threshold:
                signal_indicators.append("sell")
            else:
                signal_indicators.append("hold")
            
            if earnings_growth >= self._high_growth_threshold:
                signal_indicators.append("buy")
            elif earnings_growth <= self._decline_threshold:
                signal_indicators.append("sell")
            else:
                signal_indicators.append("hold")
            
            if peg_ratio is not None and not np.isnan(peg_ratio) and peg_ratio > 0:
                if peg_ratio <= self._buy_peg_threshold:
                    signal_indicators.append("buy")
                elif peg_ratio >= self._sell_peg_threshold:
                    signal_indicators.append("sell")
                else:
                    signal_indicators.append("hold")
            else:
                if avg_growth >= self._high_growth_threshold:
                    signal_indicators.append("buy")
                elif avg_growth <= self._decline_threshold:
                    signal_indicators.append("sell")
                else:
                    signal_indicators.append("hold")
            
            buy_count = signal_indicators.count("buy")
            sell_count = signal_indicators.count("sell")
            
            signal = "hold"
            confidence = 50.0
            numerical_score = 0.0
            reasoning = ""
            
            if peg_ratio and peg_ratio > 0:
                peg_str = f"PEG: {peg_ratio:.2f}"
            else:
                peg_str = "PEG: N/A"
            
            if buy_count >= 2 and sell_count == 0:
                if peg_ratio and peg_ratio <= self._buy_peg_threshold:
                    signal = "buy"
                    confidence = min(90.0, 70.0 + (self._buy_peg_threshold - peg_ratio) * 30 + avg_growth * 50)
                    numerical_score = min(1.0, avg_growth * 5 + 0.4)
                    reasoning = (
                        f"Strong growth at reasonable valuation: "
                        f"Revenue growth {revenue_growth:.1%}, "
                        f"Earnings growth {earnings_growth:.1%}, "
                        f"{peg_str}. "
                        f"High growth with attractive PEG ratio."
                    )
                    supporting_data["signal_condition"] = "growth_value"
                else:
                    signal = "buy"
                    confidence = min(80.0, 55.0 + avg_growth * 80)
                    numerical_score = min(0.8, avg_growth * 4)
                    reasoning = (
                        f"Strong growth: Revenue growth {revenue_growth:.1%}, "
                        f"Earnings growth {earnings_growth:.1%}, "
                        f"{peg_str}. "
                        f"High growth trajectory."
                    )
                    supporting_data["signal_condition"] = "strong_growth"
                    
            elif sell_count >= 2 and buy_count == 0:
                signal = "sell"
                confidence = min(85.0, 60.0 + abs(avg_growth) * 80)
                numerical_score = max(-1.0, avg_growth * 4 - 0.3)
                reasoning = (
                    f"Declining growth: Revenue growth {revenue_growth:.1%}, "
                    f"Earnings growth {earnings_growth:.1%}, "
                    f"{peg_str}. "
                    f"Growth momentum weakening."
                )
                supporting_data["signal_condition"] = "declining_growth"
                
            elif buy_count > sell_count:
                signal = "buy"
                confidence = 55.0 + avg_growth * 50
                numerical_score = avg_growth * 3
                reasoning = (
                    f"Moderate growth: Revenue growth {revenue_growth:.1%}, "
                    f"Earnings growth {earnings_growth:.1%}, "
                    f"{peg_str}. "
                    f"Positive growth trend."
                )
                supporting_data["signal_condition"] = "moderate_growth"
                
            elif sell_count > buy_count:
                signal = "sell"
                confidence = 55.0 + abs(avg_growth) * 50
                numerical_score = avg_growth * 3
                reasoning = (
                    f"Slowing growth: Revenue growth {revenue_growth:.1%}, "
                    f"Earnings growth {earnings_growth:.1%}, "
                    f"{peg_str}. "
                    f"Growth deceleration."
                )
                supporting_data["signal_condition"] = "slowing_growth"
                
            else:
                signal = "hold"
                confidence = 55.0
                numerical_score = avg_growth * 2
                reasoning = (
                    f"Stable growth: Revenue growth {revenue_growth:.1%}, "
                    f"Earnings growth {earnings_growth:.1%}, "
                    f"{peg_str}. "
                    f"Moderate growth trajectory."
                )
                supporting_data["signal_condition"] = "stable_growth"
            
            if earnings_growth > revenue_growth * 1.2 and earnings_growth > 0:
                confidence = min(90.0, confidence + 5)
                reasoning += " Earnings outpacing revenue - improving margins."
            
            if revenue_growth > earnings_growth * 1.5 and revenue_growth > 0:
                confidence = min(90.0, confidence + 3)
                reasoning += " Revenue outpacing earnings - margin compression risk."
            
            if peg_ratio and peg_ratio < 0.5 and avg_growth > 0:
                confidence = min(95.0, confidence + 10)
                reasoning += " Exceptional value - PEG significantly below 1."
            
            if peg_ratio and peg_ratio > 3.0:
                confidence = min(90.0, confidence + 5)
                reasoning += " High valuation concern - PEG above 3."
            
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
            return self._create_error_signal(f"Growth signal computation failed: {str(e)}")
    
    def set_growth_thresholds(
        self,
        high: float,
        moderate: float,
        decline: float
    ) -> None:
        """
        Set custom growth threshold values.
        
        Args:
            high: Threshold for high growth
            moderate: Threshold for moderate growth
            decline: Threshold for decline
        """
        self._high_growth_threshold = high
        self._moderate_growth_threshold = moderate
        self._decline_threshold = decline
    
    def set_peg_thresholds(
        self,
        buy: float,
        sell: float
    ) -> None:
        """
        Set custom PEG ratio thresholds.
        
        Args:
            buy: Maximum PEG for buy signal
            sell: Minimum PEG for sell signal
        """
        self._buy_peg_threshold = buy
        self._sell_peg_threshold = sell
