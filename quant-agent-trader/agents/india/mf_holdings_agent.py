"""
MF Holdings Analysis Agent for Indian Stock Market

Analyzes mutual fund holding patterns to detect smart money movement,
generate signals based on MF activity, and compare with FII holdings.
"""

from typing import Dict, Any, List, Optional
import logging

from signals.signal_schema import AgentSignal, AgentCategory
from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig


logger = logging.getLogger(__name__)


class MFHoldingsAgent(BaseAgent):
    """
    Mutual Fund Holdings Analysis Agent for Indian Market.
    
    Analyzes MF holding patterns including:
    - Number of MFs holding the stock
    - Change in MF holdings (increase/decrease)
    - MF ownership percentage
    - Top MF holders
    - Monthly trend analysis
    - Smart money detection (FII/MF comparison)
    """
    
    def __init__(self, config: AgentConfig = None):
        super().__init__(
            agent_name="mf_holdings_agent",
            agent_category=AgentCategory.FUNDAMENTAL,
            metadata=AgentMetadata(
                version="1.0.0",
                description="MF holdings analysis agent for Indian stocks",
                required_features=[
                    "mf_num_holders",
                    "mf_holding_pct",
                    "mf_change",
                    "mf_top_holders",
                    "mf_monthly_trend",
                    "fii_holding_pct",
                    "fii_change"
                ],
                tags=["mf", "mutual fund", "holdings", "india", "institutional"]
            ),
            config=config
        )
        
        self.bullish_mf_threshold = 3
        self.bearish_mf_threshold = -2
        self.high_mf_concentration = 30.0
        self.significant_change_threshold = 1.0
    
    def _analyze_mf_count(
        self,
        num_mfs: int
    ) -> tuple[str, float, str]:
        """Analyze number of MFs holding the stock."""
        
        if num_mfs is None or num_mfs == 0:
            return "neutral", 0.0, "No MF data available"
        
        if num_mfs >= 20:
            return "bullish", 75.0, (
                f"{num_mfs} MFs holding - high institutional confidence"
            )
        elif num_mfs >= 10:
            return "bullish", 60.0, (
                f"{num_mfs} MFs holding - moderate institutional interest"
            )
        elif num_mfs >= 5:
            return "neutral", 50.0, (
                f"{num_mfs} MFs holding - limited but present interest"
            )
        else:
            return "neutral", 40.0, (
                f"Only {num_mfs} MFs holding - low institutional coverage"
            )
    
    def _analyze_mf_holding_pct(
        self,
        mf_pct: float
    ) -> tuple[str, float, str]:
        """Analyze MF ownership percentage."""
        
        if mf_pct is None or mf_pct == 0:
            return "neutral", 0.0, "No MF ownership detected"
        
        if mf_pct >= self.high_mf_concentration:
            return "bullish", 80.0, (
                f"High MF ownership at {mf_pct:.2f}% - strong institutional backing"
            )
        elif mf_pct >= 15:
            return "bullish", 65.0, (
                f"MF ownership at {mf_pct:.2f}% - significant institutional support"
            )
        elif mf_pct >= 5:
            return "neutral", 50.0, (
                f"MF ownership at {mf_pct:.2f}% - moderate institutional interest"
            )
        else:
            return "neutral", 40.0, (
                f"Low MF ownership at {mf_pct:.2f}% - limited institutional backing"
            )
    
    def _analyze_change(
        self,
        change: float
    ) -> tuple[str, float, str]:
        """Analyze change in MF holdings."""
        
        if change is None or change == 0:
            return "neutral", 50.0, "No significant change in MF holdings"
        
        if change >= self.significant_change_threshold:
            return "bullish", min(80.0, 50.0 + change * 10), (
                f"MF holdings increased by {change:.2f}% - strong buying interest"
            )
        elif change > 0:
            return "bullish", 55.0, (
                f"MF holdings up {change:.2f}% - gradual accumulation"
            )
        elif change <= -self.significant_change_threshold:
            return "bearish", min(80.0, 50.0 + abs(change) * 10), (
                f"MF holdings decreased by {abs(change):.2f}% - selling pressure"
            )
        else:
            return "neutral", 50.0, (
                f"MF holdings down {abs(change):.2f}% - marginal profit taking"
            )
    
    def _analyze_monthly_trend(
        self,
        trend: List[Dict[str, Any]]
    ) -> tuple[str, float, str]:
        """Analyze monthly trend of MF holdings."""
        
        if not trend or len(trend) < 2:
            return "neutral", 0.0, "Insufficient trend data"
        
        try:
            pct_values = [t.get("mf_holding_pct", 0) for t in trend]
            
            if not pct_values or all(p == 0 for p in pct_values):
                return "neutral", 0.0, "No clear trend in MF holdings"
            
            first_pct = pct_values[0]
            last_pct = pct_values[-1]
            
            if last_pct > first_pct:
                change_pct = ((last_pct - first_pct) / first_pct * 100) if first_pct > 0 else 0
                if change_pct >= 10:
                    return "bullish", 75.0, (
                        f"MF holdings trending up over 4 months (+{change_pct:.1f}%)"
                    )
                else:
                    return "bullish", 60.0, (
                        f"Gradual MF accumulation trend (+{change_pct:.1f}%)"
                    )
            elif last_pct < first_pct:
                change_pct = ((first_pct - last_pct) / first_pct * 100) if first_pct > 0 else 0
                if change_pct >= 10:
                    return "bearish", 75.0, (
                        f"MF holdings trending down over 4 months (-{change_pct:.1f}%)"
                    )
                else:
                    return "bearish", 60.0, (
                        f"Gradual MF reduction trend (-{change_pct:.1f}%)"
                    )
            else:
                return "neutral", 50.0, "MF holdings stable over 4 months"
                
        except Exception as e:
            logger.warning(f"Error analyzing trend: {e}")
            return "neutral", 0.0, "Trend analysis unavailable"
    
    def _analyze_smart_money(
        self,
        mf_pct: float,
        mf_change: float,
        fii_pct: float,
        fii_change: float
    ) -> tuple[str, float, str]:
        """Analyze smart money movement (FII vs MF comparison)."""
        
        if mf_pct == 0 and fii_pct == 0:
            return "neutral", 0.0, "No institutional data available"
        
        mf_active = mf_change > 0 if mf_change else False
        fii_active = fii_change > 0 if fii_change else False
        
        if mf_active and fii_active:
            return "bullish", 80.0, "Both MF and FII buying - strong institutional support"
        elif mf_active and not fii_active:
            return "bullish", 70.0, "MF buying while FII selling - domestic institutional strength"
        elif not mf_active and fii_active:
            return "neutral", 55.0, "FII buying but MF selling - mixed signals"
        else:
            return "bearish", 65.0, "Both MF and FII selling - institutional outflows"
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """Compute MF holdings based trading signal."""
        
        symbol = features.get("symbol", "UNKNOWN")
        
        num_mfs = features.get("mf_num_holders", 0)
        mf_pct = features.get("mf_holding_pct", 0.0)
        mf_change = features.get("mf_change", 0.0)
        trend = features.get("mf_monthly_trend", [])
        
        fii_pct = features.get("fii_holding_pct", 0.0)
        fii_change = features.get("fii_change", 0.0)
        
        count_signal, count_score, count_reason = self._analyze_mf_count(num_mfs)
        
        pct_signal, pct_score, pct_reason = self._analyze_mf_holding_pct(mf_pct)
        
        change_signal, change_score, change_reason = self._analyze_change(mf_change)
        
        trend_signal, trend_score, trend_reason = self._analyze_monthly_trend(trend)
        
        smart_signal, smart_score, smart_reason = self._analyze_smart_money(
            mf_pct, mf_change, fii_pct, fii_change
        )
        
        bullish_signals = 0
        bearish_signals = 0
        total_confidence = 0
        
        signals = [
            (count_signal, count_score),
            (pct_signal, pct_score),
            (change_signal, change_score),
            (trend_signal, trend_score),
            (smart_signal, smart_score)
        ]
        
        reasoning_parts = [
            count_reason,
            pct_reason,
            change_reason,
            trend_reason,
            smart_reason
        ]
        
        for sig, conf in signals:
            if conf > 0:
                total_confidence += conf
                if sig == "bullish":
                    bullish_signals += 1
                elif sig == "bearish":
                    bearish_signals += 1
        
        active_signals = sum(1 for _, conf in signals if conf > 0)
        
        if active_signals > 0:
            final_confidence = total_confidence / active_signals
        else:
            final_confidence = 50.0
        
        if bullish_signals > bearish_signals:
            final_signal = "buy"
            final_score = 0.25
            final_reason = f"MF: {bullish_signals} bullish signals. " + " | ".join(reasoning_parts)
        elif bearish_signals > bullish_signals:
            final_signal = "sell"
            final_score = -0.25
            final_reason = f"MF: {bearish_signals} bearish signals. " + " | ".join(reasoning_parts)
        else:
            final_signal = "hold"
            final_score = 0.0
            final_reason = f"MF: Mixed signals. " + " | ".join(reasoning_parts)
        
        return AgentSignal(
            agent_name=self.agent_name,
            agent_category=self.agent_category.value,
            signal=final_signal,
            confidence=final_confidence,
            numerical_score=final_score,
            reasoning=final_reason,
            supporting_data={
                "mf_count": num_mfs,
                "mf_holding_pct": mf_pct,
                "mf_change": mf_change,
                "fii_holding_pct": fii_pct,
                "fii_change": fii_change,
                "smart_money": smart_signal,
                "bullish_count": bullish_signals,
                "bearish_count": bearish_signals,
                "trend": trend
            }
        )


class MFHoldingsAnalyzer:
    """
    Standalone analyzer for MF holdings without agent interface.
    Useful for quick analysis and reporting.
    """
    
    def __init__(self):
        self.agent = MFHoldingsAgent()
    
    def analyze(
        self,
        mf_data: Dict[str, Any],
        fii_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze MF holdings data.
        
        Args:
            mf_data: Dictionary with MF holdings data
            fii_data: Optional dictionary with FII holdings data
            
        Returns:
            Analysis results
        """
        
        features = {
            "symbol": mf_data.get("symbol", "UNKNOWN"),
            "mf_num_holders": mf_data.get("num_mfs_holding", 0),
            "mf_holding_pct": mf_data.get("mf_holding_pct", 0.0),
            "mf_change": mf_data.get("change_in_holding", 0.0),
            "mf_top_holders": mf_data.get("top_mf_holders", []),
            "mf_monthly_trend": mf_data.get("monthly_trend", []),
        }
        
        if fii_data:
            features["fii_holding_pct"] = fii_data.get("fii_holding_pct", 0.0)
            features["fii_change"] = fii_data.get("fii_change", 0.0)
        else:
            features["fii_holding_pct"] = 0.0
            features["fii_change"] = 0.0
        
        signal = self.agent.compute_signal(features)
        
        return {
            "signal": signal.signal,
            "confidence": signal.confidence,
            "numerical_score": signal.numerical_score,
            "reasoning": signal.reasoning,
            "supporting_data": signal.supporting_data,
            "analysis": self._generate_detailed_analysis(features)
        }
    
    def _generate_detailed_analysis(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed analysis report."""
        
        num_mfs = features.get("mf_num_holders", 0)
        mf_pct = features.get("mf_holding_pct", 0.0)
        mf_change = features.get("mf_change", 0.0)
        trend = features.get("mf_monthly_trend", [])
        top_holders = features.get("mf_top_holders", [])
        
        fii_pct = features.get("fii_holding_pct", 0.0)
        fii_change = features.get("fii_change", 0.0)
        
        if mf_pct > fii_pct:
            dominance = "MF Dominant"
        elif fii_pct > mf_pct:
            dominance = "FII Dominant"
        else:
            dominance = "Balanced"
        
        if mf_change > 0.5:
            mf_trend = "Strong Buying"
        elif mf_change > 0:
            mf_trend = "Accumulating"
        elif mf_change < -0.5:
            mf_trend = "Strong Selling"
        elif mf_change < 0:
            mf_trend = "Distributing"
        else:
            mf_trend = "Stable"
        
        total_institutional = mf_pct + fii_pct
        
        return {
            "summary": {
                "num_mfs_holding": num_mfs,
                "mf_ownership_pct": round(mf_pct, 2),
                "mf_change": round(mf_change, 2),
                "fii_ownership_pct": round(fii_pct, 2),
                "fii_change": round(fii_change, 2),
                "total_institutional_pct": round(total_institutional, 2)
            },
            "institutional_dominance": dominance,
            "mf_trend": mf_trend,
            "top_mf_holders": [
                {
                    "name": h.get("holder", "Unknown"),
                    "pct": round(h.get("pct", 0), 2)
                }
                for h in top_holders[:5]
            ],
            "monthly_trend": trend,
            "signals": {
                "mf_signal": "BUY" if mf_change > 0 else "SELL" if mf_change < 0 else "HOLD",
                "smart_money": "MF" if mf_change > fii_change else "FII" if fii_change > mf_change else "Neutral"
            }
        }
