"""
Earnings Agent - Earnings performance analysis.

This agent analyzes earnings metrics to identify:
- Companies with strong earnings growth (buy signal)
- Companies with declining earnings (sell signal)
- Companies with stable/slightly growing earnings (hold signal)

Metrics analyzed:
- EPS growth (current EPS vs previous EPS)
- Revenue growth
- Earnings beat/miss frequency history
"""

from typing import Dict, Any, Optional
import numpy as np

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class EarningsAgent(BaseAgent):
    """
    Agent for earnings-based fundamental analysis.
    
    Analyzes earnings metrics to determine the strength and trajectory
    of a company's earnings performance.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Earnings agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Earnings analysis using EPS growth, revenue growth, and earnings beat frequency",
                required_features=["eps_growth", "revenue_growth", "eps_beat_frequency"],
                author="Quant Team",
                tags=["fundamental", "earnings", "eps", "revenue"]
            )
        
        super().__init__(
            agent_name="earnings_agent",
            agent_category=AgentCategory.FUNDAMENTAL,
            metadata=metadata,
            config=config
        )
        
        self._strong_growth_threshold = 0.15
        self._moderate_growth_threshold = 0.05
        self._decline_threshold = -0.05
        self._beat_threshold = 0.6
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute earnings-based trading signal.
        
        Args:
            features: Dictionary containing earnings metrics
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            eps_growth: float = features.get("eps_growth", 0.0)
            revenue_growth: float = features.get("revenue_growth", 0.0)
            eps_beat_frequency: float = features.get("eps_beat_frequency", 0.5)
            
            supporting_data: Dict[str, Any] = {
                "eps_growth": eps_growth,
                "revenue_growth": revenue_growth,
                "eps_beat_frequency": eps_beat_frequency
            }
            
            if eps_growth is None or np.isnan(eps_growth):
                eps_growth = 0.0
            if revenue_growth is None or np.isnan(revenue_growth):
                revenue_growth = 0.0
            if eps_beat_frequency is None or np.isnan(eps_beat_frequency):
                eps_beat_frequency = 0.5
            
            signal_indicators = []
            
            if eps_growth >= self._strong_growth_threshold:
                signal_indicators.append("buy")
            elif eps_growth <= self._decline_threshold:
                signal_indicators.append("sell")
            else:
                signal_indicators.append("hold")
            
            if revenue_growth >= self._strong_growth_threshold:
                signal_indicators.append("buy")
            elif revenue_growth <= self._decline_threshold:
                signal_indicators.append("sell")
            else:
                signal_indicators.append("hold")
            
            if eps_beat_frequency >= self._beat_threshold:
                signal_indicators.append("buy")
            elif eps_beat_frequency <= 0.4:
                signal_indicators.append("sell")
            else:
                signal_indicators.append("hold")
            
            buy_count = signal_indicators.count("buy")
            sell_count = signal_indicators.count("sell")
            
            signal = "hold"
            confidence = 50.0
            numerical_score = 0.0
            reasoning = ""
            
            avg_growth = (eps_growth + revenue_growth) / 2
            
            if buy_count >= 2 and sell_count == 0:
                signal = "buy"
                confidence = min(85.0, 60.0 + avg_growth * 100 + eps_beat_frequency * 20)
                numerical_score = min(1.0, avg_growth * 5 + 0.3)
                reasoning = (
                    f"Strong earnings: EPS growth {eps_growth:.1%}, "
                    f"Revenue growth {revenue_growth:.1%}, "
                    f"Beat frequency {eps_beat_frequency:.0%}. "
                    f"Company showing solid earnings momentum."
                )
                supporting_data["signal_condition"] = "strong_earnings"
                
            elif sell_count >= 2 and buy_count == 0:
                signal = "sell"
                confidence = min(85.0, 60.0 + abs(avg_growth) * 100 + (1 - eps_beat_frequency) * 20)
                numerical_score = max(-1.0, avg_growth * 5 - 0.3)
                reasoning = (
                    f"Weak earnings: EPS growth {eps_growth:.1%}, "
                    f"Revenue growth {revenue_growth:.1%}, "
                    f"Beat frequency {eps_beat_frequency:.0%}. "
                    f"Company facing earnings headwinds."
                )
                supporting_data["signal_condition"] = "weak_earnings"
                
            elif buy_count > sell_count:
                signal = "buy"
                confidence = 55.0 + eps_growth * 50
                numerical_score = avg_growth * 3
                reasoning = (
                    f"Moderate earnings: EPS growth {eps_growth:.1%}, "
                    f"Revenue growth {revenue_growth:.1%}. "
                    f"Positive but not exceptional."
                )
                supporting_data["signal_condition"] = "moderate_positive"
                
            elif sell_count > buy_count:
                signal = "sell"
                confidence = 55.0 + abs(avg_growth) * 50
                numerical_score = avg_growth * 3
                reasoning = (
                    f"Declining earnings: EPS growth {eps_growth:.1%}, "
                    f"Revenue growth {revenue_growth:.1%}. "
                    f"Caution warranted."
                )
                supporting_data["signal_condition"] = "moderate_negative"
                
            else:
                signal = "hold"
                confidence = 55.0
                numerical_score = avg_growth * 2
                reasoning = (
                    f"Mixed signals: EPS growth {eps_growth:.1%}, "
                    f"Revenue growth {revenue_growth:.1%}, "
                    f"Beat frequency {eps_beat_frequency:.0%}. "
                    f"Waiting for clearer earnings trend."
                )
                supporting_data["signal_condition"] = "neutral"
            
            if eps_growth > revenue_growth * 1.5 and eps_growth > 0:
                confidence = min(90.0, confidence + 5)
                reasoning += " EPS outpacing revenue indicates operational leverage."
            
            if revenue_growth > eps_growth * 2 and revenue_growth > 0:
                confidence = min(90.0, confidence + 3)
                reasoning += " Revenue growing faster than EPS - margin pressure possible."
            
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
            return self._create_error_signal(f"Earnings signal computation failed: {str(e)}")
    
    def set_growth_thresholds(
        self,
        strong: float,
        moderate: float,
        decline: float
    ) -> None:
        """
        Set custom growth threshold values.
        
        Args:
            strong: Threshold for strong growth (buy signal)
            moderate: Threshold for moderate growth
            decline: Threshold for decline (sell signal)
        """
        self._strong_growth_threshold = strong
        self._moderate_growth_threshold = moderate
        self._decline_threshold = decline
    
    def set_beat_threshold(self, threshold: float) -> None:
        """
        Set threshold for earnings beat frequency.
        
        Args:
            threshold: Minimum beat frequency for buy signal
        """
        self._beat_threshold = threshold
