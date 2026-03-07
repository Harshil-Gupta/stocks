"""
MF Holdings Analysis Agent for Indian Stock Market

Analyzes mutual fund holding patterns to detect smart money movement,
generate signals based on MF activity, and compare with FII holdings.

Enhanced with:
- Quarterly holding changes
- Sector-wise MF analysis
- MF concentration risk
- New MF additions/sales tracking
- YOY growth analysis
- MF net flow analysis
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
    - Quarterly changes
    - MF concentration risk
    - New MF additions/sales
    - YOY growth analysis
    """
    
    def __init__(self, config: AgentConfig = None):
        super().__init__(
            agent_name="mf_holdings_agent",
            agent_category=AgentCategory.FUNDAMENTAL,
            metadata=AgentMetadata(
                version="2.0.0",
                description="Enhanced MF holdings analysis agent for Indian stocks",
                required_features=[
                    "mf_num_holders",
                    "mf_holding_pct",
                    "mf_change",
                    "mf_top_holders",
                    "mf_monthly_trend",
                    "mf_quarterly_change",
                    "mf_new_additions",
                    "mf_net_flow",
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
        self.new_mf_addition_weight = 0.15
        self.quarterly_change_weight = 0.20
    
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
    
    def _analyze_quarterly_change(
        self,
        quarterly_change: float
    ) -> tuple[str, float, str]:
        """Analyze quarterly change in MF holdings."""
        
        if quarterly_change is None or quarterly_change == 0:
            return "neutral", 50.0, "No quarterly change data available"
        
        if quarterly_change >= 5.0:
            return "bullish", 85.0, (
                f"Strong quarterly MF accumulation at +{quarterly_change:.2f}% - quality funds adding"
            )
        elif quarterly_change >= 2.0:
            return "bullish", 70.0, (
                f"MF holdings increased by {quarterly_change:.2f}% this quarter - positive flow"
            )
        elif quarterly_change > 0:
            return "bullish", 55.0, (
                f"Modest quarterly increase of {quarterly_change:.2f}%"
            )
        elif quarterly_change <= -5.0:
            return "bearish", 85.0, (
                f"Significant quarterly outflow at {quarterly_change:.2f}% - funds reducing positions"
            )
        elif quarterly_change <= -2.0:
            return "bearish", 70.0, (
                f"MF holdings decreased by {quarterly_change:.2f}% this quarter - selling pressure"
            )
        else:
            return "neutral", 50.0, (
                f"Minor quarterly change of {quarterly_change:.2f}%"
            )
    
    def _analyze_new_additions(
        self,
        new_additions: int,
        total_mfs: int
    ) -> tuple[str, float, str]:
        """Analyze new MF additions to the stock."""
        
        if new_additions is None or new_additions == 0:
            return "neutral", 50.0, "No new MF additions this period"
        
        if total_mfs > 0:
            addition_rate = (new_additions / total_mfs) * 100
        else:
            addition_rate = 0
        
        if new_additions >= 5:
            return "bullish", 85.0, (
                f"{new_additions} new MFs added - strong vote of confidence"
            )
        elif new_additions >= 3:
            return "bullish", 70.0, (
                f"{new_additions} new MFs holding - growing institutional interest"
            )
        elif new_additions >= 1:
            return "bullish", 55.0, (
                f"{new_additions} new MF added - some funds initiating position"
            )
        else:
            return "neutral", 50.0, "No new MF additions"
    
    def _analyze_net_flow(
        self,
        net_flow: float,
        avg_flow: float
    ) -> tuple[str, float, str]:
        """Analyze MF net flow (inflows vs outflows)."""
        
        if net_flow is None:
            return "neutral", 0.0, "Net flow data unavailable"
        
        if net_flow > avg_flow * 1.5 and net_flow > 0:
            return "bullish", 80.0, (
                f"Strong net inflows at ₹{net_flow:.2f}Cr - above average interest"
            )
        elif net_flow > 0:
            return "bullish", 60.0, (
                f"Net inflows of ₹{net_flow:.2f}Cr - positive fund sentiment"
            )
        elif net_flow < avg_flow * 1.5 and net_flow < 0:
            return "bearish", 80.0, (
                f"Net outflows of ₹{abs(net_flow):.2f}Cr - fund sentiment weak"
            )
        elif net_flow < 0:
            return "bearish", 60.0, (
                f"Net outflows of ₹{abs(net_flow):.2f}Cr - some funds exiting"
            )
        else:
            return "neutral", 50.0, "Stable net flow"
    
    def _analyze_concentration_risk(
        self,
        top_holder_pct: float,
        total_mf_pct: float
    ) -> tuple[str, float, str]:
        """Analyze concentration risk - how much top MFs dominate."""
        
        if top_holder_pct is None or total_mf_pct == 0:
            return "neutral", 50.0, "Concentration data unavailable"
        
        concentration = (top_holder_pct / total_mf_pct) * 100 if total_mf_pct > 0 else 0
        
        if concentration >= 70:
            return "neutral", 45.0, (
                f"High concentration - top holder owns {concentration:.1f}% of MF stake"
            )
        elif concentration >= 50:
            return "neutral", 55.0, (
                f"Moderate concentration - top holder owns {concentration:.1f}% of MF stake"
            )
        else:
            return "bullish", 65.0, (
                f"Well distributed - {concentration:.1f}% held by top holder - lower risk"
            )
    
    def _analyze_yoy_growth(
        self,
        yoy_change: float
    ) -> tuple[str, float, str]:
        """Analyze Year-over-Year change in MF holdings."""
        
        if yoy_change is None or yoy_change == 0:
            return "neutral", 50.0, "YOY data unavailable"
        
        if yoy_change >= 20:
            return "bullish", 85.0, (
                f"Strong YOY growth at +{yoy_change:.1f}% - consistent institutional backing"
            )
        elif yoy_change >= 10:
            return "bullish", 70.0, (
                f"Good YOY growth of {yoy_change:.1f}% - sustained interest"
            )
        elif yoy_change > 0:
            return "bullish", 55.0, (
                f"Modest YOY increase of {yoy_change:.1f}%"
            )
        elif yoy_change <= -20:
            return "bearish", 85.0, (
                f"Significant YOY decline of {yoy_change:.1f}% - institutional exit"
            )
        elif yoy_change <= -10:
            return "bearish", 70.0, (
                f"YOY decrease of {yoy_change:.1f}% - fading interest"
            )
        else:
            return "neutral", 50.0, (
                f"YOY change of {yoy_change:.1f}% - stable holdings"
            )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """Compute MF holdings based trading signal."""
        
        symbol = features.get("symbol", "UNKNOWN")
        
        # Basic metrics
        num_mfs = features.get("mf_num_holders", 0)
        mf_pct = features.get("mf_holding_pct", 0.0)
        mf_change = features.get("mf_change", 0.0)
        trend = features.get("mf_monthly_trend", [])
        
        # Enhanced metrics
        quarterly_change = features.get("mf_quarterly_change", 0.0)
        new_additions = features.get("mf_new_additions", 0)
        net_flow = features.get("mf_net_flow", 0.0)
        avg_flow = features.get("mf_avg_flow", 100.0)  # Default avg
        yoy_change = features.get("mf_yoy_change", 0.0)
        
        # Top holder concentration
        top_holder_pct = features.get("mf_top_holder_pct", 0.0)
        
        # FII data
        fii_pct = features.get("fii_holding_pct", 0.0)
        fii_change = features.get("fii_change", 0.0)
        
        # Analyze all components
        count_signal, count_score, count_reason = self._analyze_mf_count(num_mfs)
        pct_signal, pct_score, pct_reason = self._analyze_mf_holding_pct(mf_pct)
        change_signal, change_score, change_reason = self._analyze_change(mf_change)
        trend_signal, trend_score, trend_reason = self._analyze_monthly_trend(trend)
        quarterly_signal, quarterly_score, quarterly_reason = self._analyze_quarterly_change(quarterly_change)
        additions_signal, additions_score, additions_reason = self._analyze_new_additions(new_additions, num_mfs)
        flow_signal, flow_score, flow_reason = self._analyze_net_flow(net_flow, avg_flow)
        yoy_signal, yoy_score, yoy_reason = self._analyze_yoy_growth(yoy_change)
        concentration_signal, concentration_score, concentration_reason = self._analyze_concentration_risk(top_holder_pct, mf_pct)
        smart_signal, smart_score, smart_reason = self._analyze_smart_money(mf_pct, mf_change, fii_pct, fii_change)
        
        # Collect all signals
        signals = [
            (count_signal, count_score, count_reason),
            (pct_signal, pct_score, pct_reason),
            (change_signal, change_score, change_reason),
            (trend_signal, trend_score, trend_reason),
            (quarterly_signal, quarterly_score, quarterly_reason),
            (additions_signal, additions_score, additions_reason),
            (flow_signal, flow_score, flow_reason),
            (yoy_signal, yoy_score, yoy_reason),
            (concentration_signal, concentration_score, concentration_reason),
            (smart_signal, smart_score, smart_reason)
        ]
        
        # Count signals
        bullish_signals = sum(1 for s, c, _ in signals if s == "bullish" and c > 0)
        bearish_signals = sum(1 for s, c, _ in signals if s == "bearish" and c > 0)
        total_confidence = sum(c for _, c, _ in signals if c > 0)
        
        active_signals = sum(1 for _, c, _ in signals if c > 0)
        
        if active_signals > 0:
            final_confidence = total_confidence / active_signals
        else:
            final_confidence = 50.0
        
        # Determine final signal with weighted scoring
        if bullish_signals > bearish_signals + 2:
            final_signal = "buy"
            final_score = 0.35
            confidence = min(90.0, final_confidence + 15)
        elif bearish_signals > bullish_signals + 2:
            final_signal = "sell"
            final_score = -0.35
            confidence = min(90.0, final_confidence + 15)
        elif bullish_signals > bearish_signals:
            final_signal = "buy"
            final_score = 0.20
            confidence = final_confidence + 5
        elif bearish_signals > bullish_signals:
            final_signal = "sell"
            final_score = -0.20
            confidence = final_confidence + 5
        else:
            final_signal = "hold"
            final_score = 0.0
            confidence = final_confidence
        
        # Generate comprehensive reasoning
        reasoning_parts = [
            f"MF Count: {count_reason}",
            f"MF %: {pct_reason}",
            f"Change: {change_reason}",
            f"Trend: {trend_reason}",
            f"Quarterly: {quarterly_reason}",
            f"New Additions: {additions_reason}",
            f"Net Flow: {flow_reason}",
            f"YOY: {yoy_reason}",
            f"Concentration: {concentration_reason}",
            f"Smart Money: {smart_reason}"
        ]
        
        final_reason = " | ".join(reasoning_parts)
        
        return AgentSignal(
            agent_name=self.agent_name,
            agent_category=self.agent_category.value,
            signal=final_signal,
            confidence=confidence,
            numerical_score=final_score,
            reasoning=final_reason,
            supporting_data={
                "mf_count": num_mfs,
                "mf_holding_pct": mf_pct,
                "mf_change": mf_change,
                "mf_quarterly_change": quarterly_change,
                "mf_new_additions": new_additions,
                "mf_net_flow": net_flow,
                "mf_yoy_change": yoy_change,
                "mf_top_holder_pct": top_holder_pct,
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
