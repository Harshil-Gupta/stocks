"""
Valuation Agent - Fundamental valuation analysis.

This agent analyzes key valuation metrics to identify:
- Undervalued stocks (buy signal)
- Overvalued stocks (sell signal)
- Fairly valued stocks (hold signal)

Metrics analyzed:
- P/E ratio (price / earnings per share)
- P/B ratio (price / book value per share)
- P/S ratio (price / sales per share)
- EV/EBITDA (enterprise value / EBITDA)
"""

from typing import Dict, Any, Optional
import numpy as np

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class ValuationAgent(BaseAgent):
    """
    Agent for valuation-based fundamental analysis.
    
    Analyzes valuation multiples to determine if a stock is undervalued,
    overvalued, or fairly valued relative to the market/industry averages.
    """
    
    DEFAULT_INDUSTRY_PE = 20.0
    DEFAULT_INDUSTRY_PB = 3.0
    DEFAULT_INDUSTRY_PS = 2.5
    DEFAULT_INDUSTRY_EV_EBITDA = 12.0
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Valuation agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Valuation analysis using P/E, P/B, P/S, and EV/EBITDA ratios",
                required_features=["pe_ratio", "pb_ratio", "ps_ratio"],
                author="Quant Team",
                tags=["fundamental", "valuation", "multiples"]
            )
        
        super().__init__(
            agent_name="valuation_agent",
            agent_category=AgentCategory.FUNDAMENTAL,
            metadata=metadata,
            config=config
        )
        
        self._industry_pe = self.DEFAULT_INDUSTRY_PE
        self._industry_pb = self.DEFAULT_INDUSTRY_PB
        self._industry_ps = self.DEFAULT_INDUSTRY_PS
        self._industry_ev_ebitda = self.DEFAULT_INDUSTRY_EV_EBITDA
        self._undervalued_threshold = 0.8
        self._overvalued_threshold = 1.2
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute valuation-based trading signal.
        
        Args:
            features: Dictionary containing valuation metrics
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            pe_ratio: float = features.get("pe_ratio", 0.0)
            pb_ratio: float = features.get("pb_ratio", 0.0)
            ps_ratio: float = features.get("ps_ratio", 0.0)
            ev_ebitda: Optional[float] = features.get("ev_ebitda")
            
            supporting_data: Dict[str, Any] = {
                "pe_ratio": pe_ratio,
                "pb_ratio": pb_ratio,
                "ps_ratio": ps_ratio,
                "ev_ebitda": ev_ebitda,
                "industry_pe": self._industry_pe,
                "industry_pb": self._industry_pb,
                "industry_ps": self._industry_ps,
                "industry_ev_ebitda": self._industry_ev_ebitda
            }
            
            valid_ratios = []
            ratio_scores = []
            
            if pe_ratio and pe_ratio > 0:
                pe_score = pe_ratio / self._industry_pe
                valid_ratios.append("pe")
                ratio_scores.append(pe_score)
                supporting_data["pe_score"] = pe_score
                supporting_data["pe_vs_industry"] = pe_ratio / self._industry_pe
            
            if pb_ratio and pb_ratio > 0:
                pb_score = pb_ratio / self._industry_pb
                valid_ratios.append("pb")
                ratio_scores.append(pb_score)
                supporting_data["pb_score"] = pb_score
                supporting_data["pb_vs_industry"] = pb_ratio / self._industry_pb
            
            if ps_ratio and ps_ratio > 0:
                ps_score = ps_ratio / self._industry_ps
                valid_ratios.append("ps")
                ratio_scores.append(ps_score)
                supporting_data["ps_score"] = ps_score
                supporting_data["ps_vs_industry"] = ps_ratio / self._industry_ps
            
            if ev_ebitda and ev_ebitda > 0:
                ev_ebitda_score = ev_ebitda / self._industry_ev_ebitda
                valid_ratios.append("ev_ebitda")
                ratio_scores.append(ev_ebitda_score)
                supporting_data["ev_ebitda_score"] = ev_ebitda_score
                supporting_data["ev_ebitda_vs_industry"] = ev_ebitda / self._industry_ev_ebitda
            
            if not valid_ratios or not ratio_scores:
                return AgentSignal(
                    agent_name=self._agent_name,
                    agent_category=self._agent_category.value,
                    signal="hold",
                    confidence=50.0,
                    numerical_score=0.0,
                    reasoning="Insufficient valuation data available",
                    supporting_data=supporting_data
                )
            
            avg_score = np.mean(ratio_scores)
            signal_count = {"buy": 0, "sell": 0, "hold": 0}
            
            for score in ratio_scores:
                if score >= self._overvalued_threshold:
                    signal_count["sell"] += 1
                elif score <= self._undervalued_threshold:
                    signal_count["buy"] += 1
                else:
                    signal_count["hold"] += 1
            
            if avg_score >= self._overvalued_threshold and signal_count["buy"] == 0:
                signal = "sell"
                confidence = min(85.0, 50.0 + avg_score * 15)
                numerical_score = max(-1.0, -0.5 - (avg_score - 1.0) * 0.5)
                reasoning = (
                    f"Overvalued: P/E: {pe_ratio:.1f}x (industry: {self._industry_pe:.1f}x), "
                    f"P/B: {pb_ratio:.1f}x (industry: {self._industry_pb:.1f}x), "
                    f"P/S: {ps_ratio:.1f}x (industry: {self._industry_ps:.1f}x). "
                    f"Valuation score: {avg_score:.2f} (1.0 = fair value)."
                )
                supporting_data["signal_condition"] = "overvalued"
                
            elif avg_score <= self._undervalued_threshold and signal_count["sell"] == 0:
                signal = "buy"
                confidence = min(85.0, 50.0 + (1.0 - avg_score) * 50)
                numerical_score = min(1.0, 0.5 + (1.0 - avg_score) * 0.5)
                reasoning = (
                    f"Undervalued: P/E: {pe_ratio:.1f}x (industry: {self._industry_pe:.1f}x), "
                    f"P/B: {pb_ratio:.1f}x (industry: {self._industry_pb:.1f}x), "
                    f"P/S: {ps_ratio:.1f}x (industry: {self._industry_ps:.1f}x). "
                    f"Valuation score: {avg_score:.2f} (1.0 = fair value)."
                )
                supporting_data["signal_condition"] = "undervalued"
                
            else:
                signal = "hold"
                confidence = 55.0
                numerical_score = 0.0
                reasoning = (
                    f"Fairly valued: P/E: {pe_ratio:.1f}x, P/B: {pb_ratio:.1f}x, "
                    f"P/S: {ps_ratio:.1f}x. Valuation score: {avg_score:.2f} near industry average."
                )
                supporting_data["signal_condition"] = "fair_value"
            
            if ev_ebitda:
                if ev_ebitda < self._industry_ev_ebitda * 0.8 and signal == "hold":
                    confidence += 5
                    reasoning += f" EV/EBITDA ({ev_ebitda:.1f}x) below industry supports value."
                elif ev_ebitda > self._industry_ev_ebitda * 1.2 and signal == "hold":
                    confidence += 5
                    reasoning += f" EV/EBITDA ({ev_ebitda:.1f}x) above industry suggests caution."
            
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
            return self._create_error_signal(f"Valuation signal computation failed: {str(e)}")
    
    def set_industry_multiples(
        self,
        pe: float,
        pb: float,
        ps: float,
        ev_ebitda: Optional[float] = None
    ) -> None:
        """
        Set custom industry average multiples.
        
        Args:
            pe: Industry average P/E ratio
            pb: Industry average P/B ratio
            ps: Industry average P/S ratio
            ev_ebitda: Industry average EV/EBITDA
        """
        self._industry_pe = pe
        self._industry_pb = pb
        self._industry_ps = ps
        if ev_ebitda:
            self._industry_ev_ebitda = ev_ebitda
    
    def set_valuation_thresholds(
        self,
        undervalued: float,
        overvalued: float
    ) -> None:
        """
        Set custom valuation thresholds.
        
        Args:
            undervalued: Threshold for undervalued (score <= this = buy)
            overvalued: Threshold for overvalued (score >= this = sell)
        """
        self._undervalued_threshold = undervalued
        self._overvalued_threshold = overvalued
