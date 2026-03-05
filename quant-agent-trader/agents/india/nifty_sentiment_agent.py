from typing import Dict, Any, List
import logging

from signals.signal_schema import AgentSignal, AgentCategory
from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig


logger = logging.getLogger(__name__)


NIFTY_CONSTITUENTS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "HINDUNILVR", "ICICIBANK",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "HCLTECH", "ASIANPAINT",
    "MARUTI", "TITAN", "BAJFINANCE", "WIPRO", "ULTRACEMCO", "NTPC",
    "POWERGRID", "M&M", "SUNPHARMA", "TATASTEEL", "DRREDDY", "CIPLA",
    "ADANIPORTS", "BAJAJFINSV", "GRASIM", "HEROMOTOCO", "INDUSINDBK",
    "JSWSTEEL", "SBILIFE", "SHREECEM", "AXISBANK", "ADANIENT", "DIVISLAB",
]


class NiftySentimentAgent(BaseAgent):
    """
    NIFTY Market Breadth and Sentiment Analysis Agent.
    
    Analyzes market breadth indicators for NIFTY 50:
    - Advance/Decline ratio
    - Market breadth (% stocks above moving averages)
    - Sector rotation
    - NIFTY vs NIFTY Bank comparison
    - Intraday sentiment indicators
    """
    
    def __init__(self, config: AgentConfig = None):
        super().__init__(
            agent_name="nifty_sentiment_agent",
            agent_category=AgentCategory.SENTIMENT,
            metadata=AgentMetadata(
                version="1.0.0",
                description="NIFTY market breadth and sentiment analysis",
                required_features=[
                    "nifty_price", "nifty_bank_price", "advances", "declines",
                    "nifty_above_sma50", "nifty_above_sma200",
                    "sector_performance"
                ],
                tags=["sentiment", "nifty", "breadth", "india", "market"]
            ),
            config=config
        )
        self.bullish_breadth_threshold = 0.65
        self.bearish_breadth_threshold = 0.35
        self.relative_strength_threshold = 0.03
    
    def _calculate_breadth_signal(
        self,
        advances: int,
        declines: int
    ) -> tuple[str, float, str]:
        """Analyze advance/decline ratio."""
        
        if advances + declines == 0:
            return "neutral", 0.0, "No advance/decline data"
        
        breadth_ratio = advances / (advances + declines)
        
        if breadth_ratio >= self.bullish_breadth_threshold:
            return "bullish", 80.0, (
                f"Strong breadth: {advances} advances vs {declines} declines "
                f"({breadth_ratio*100:.1f}% advances). Market showing strength."
            )
        elif breadth_ratio <= self.bearish_breadth_threshold:
            return "bearish", 80.0, (
                f"Weak breadth: {advances} advances vs {declines} declines "
                f"({breadth_ratio*100:.1f}% advances). Market showing weakness."
            )
        else:
            return "neutral", 50.0, (
                f"Mixed breadth: {advances} advances vs {declines} declines "
                f"({breadth_ratio*100:.1f}% advances)."
            )
    
    def _calculate_ma_breadth_signal(
        self,
        above_sma50: float,
        above_sma200: float
    ) -> tuple[str, float, str]:
        """Analyze how many stocks are above their moving averages."""
        
        avg_above = (above_sma50 + above_sma200) / 2
        
        if avg_above >= 0.70:
            return "bullish", 75.0, (
                f"{above_sma50*100:.0f}% above SMA50, {above_sma200*100:.0f}% above SMA200. "
                f"Strong trend participation."
            )
        elif avg_above <= 0.30:
            return "bearish", 75.0, (
                f"Only {above_sma50*100:.0f}% above SMA50, {above_sma200*100:.0f}% above SMA200. "
                f"Weak trend participation."
            )
        else:
            return "neutral", 50.0, (
                f"{above_sma50*100:.0f}% above SMA50, {above_sma200*100:.0f}% above SMA200."
            )
    
    def _calculate_sector_rotation_signal(
        self,
        sector_performance: Dict[str, float]
    ) -> tuple[str, float, str]:
        """Analyze sector rotation for market direction."""
        
        if not sector_performance:
            return "neutral", 0.0, "No sector data"
        
        leader = max(sector_performance.items(), key=lambda x: x[1])
        laggard = min(sector_performance.items(), key=lambda x: x[1])
        
        defensive_sectors = ["NIFTY FMCG", "NIFTY PHARMA", "NIFTY IT"]
        cyclical_sectors = ["NIFTY AUTO", "NIFTY METAL", "NIFTY REALTY", "NIFTY BANK"]
        
        defensive_perf = sum(
            sector_performance.get(s, 0) for s in defensive_sectors
        ) / len(defensive_sectors)
        
        cyclical_perf = sum(
            sector_performance.get(s, 0) for s in cyclical_sectors
        ) / len(cyclical_sectors)
        
        if cyclical_perf > defensive_perf + self.relative_strength_threshold:
            return "bullish", 70.0, (
                f"Cyclicals leading ({cyclical_perf:.1f}% vs defensive {defensive_perf:.1f}). "
                f"Risk-on environment."
            )
        elif defensive_perf > cyclical_perf + self.relative_strength_threshold:
            return "bearish", 70.0, (
                f"Defensives leading ({defensive_perf:.1f}% vs cyclical {cyclical_perf:.1f}). "
                f"Risk-off environment."
            )
        else:
            return "neutral", 50.0, (
                f"Sector rotation neutral. Leader: {leader[0]} ({leader[1]:.1f}%), "
                f"Laggard: {laggard[0]} ({laggard[1]:.1f}%)."
            )
    
    def _calculate_bank_vs_financials_signal(
        self,
        nifty_price: float,
        nifty_bank_price: float,
        nifty_change: float,
        bank_change: float
    ) -> tuple[str, float, str]:
        """Analyze NIFTY Bank relative performance."""
        
        if nifty_price is None or nifty_bank_price is None:
            return "neutral", 0.0, "NIFTY Bank data unavailable"
        
        relative_change = bank_change - nifty_change
        
        if relative_change > self.relative_strength_threshold:
            return "bullish", 65.0, (
                f"NIFTY Bank outperforming (+{bank_change:.2f}% vs +{nifty_change:.2f}%). "
                f"Financials leading - positive for NIFTY."
            )
        elif relative_change < -self.relative_strength_threshold:
            return "neutral", 60.0, (
                f"NIFTY Bank underperforming (+{bank_change:.2f}% vs +{nifty_change:.2f}%). "
                f"Financials lagging."
            )
        else:
            return "neutral", 50.0, (
                f"NIFTY Bank performing in line (+{bank_change:.2f}% vs +{nifty_change:.2f}%)."
            )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """Compute NIFTY sentiment based trading signal."""
        
        advances = features.get("advances", 0)
        declines = features.get("declines", 0)
        above_sma50 = features.get("nifty_above_sma50", 0.5)
        above_sma200 = features.get("nifty_above_sma200", 0.5)
        sector_perf = features.get("sector_performance", {})
        
        nifty_price = features.get("nifty_price")
        bank_price = features.get("nifty_bank_price")
        nifty_change = features.get("nifty_change", 0)
        bank_change = features.get("nifty_bank_change", 0)
        
        breadth_sig, breadth_conf, breadth_reason = self._calculate_breadth_signal(
            advances, declines
        )
        
        ma_sig, ma_conf, ma_reason = self._calculate_ma_breadth_signal(
            above_sma50, above_sma200
        )
        
        sector_sig, sector_conf, sector_reason = self._calculate_sector_rotation_signal(
            sector_perf
        )
        
        bank_sig, bank_conf, bank_reason = self._calculate_bank_vs_financials_signal(
            nifty_price, bank_price, nifty_change, bank_change
        )
        
        signals = [
            (breadth_sig, breadth_conf),
            (ma_sig, ma_conf),
            (sector_sig, sector_conf),
            (bank_sig, bank_conf),
        ]
        
        bullish_count = sum(1 for s, _ in signals if s == "bullish")
        bearish_count = sum(1 for s, _ in signals if s == "bearish")
        
        total_conf = sum(c for _, c in signals if c > 0)
        valid_signals = sum(1 for _, c in signals if c > 0)
        
        if valid_signals > 0:
            avg_conf = total_conf / valid_signals
        else:
            avg_conf = 50.0
        
        reasoning_parts = [breadth_reason, ma_reason, sector_reason, bank_reason]
        
        if bullish_count > bearish_count:
            final_signal = "buy"
            final_conf = avg_conf
            final_reason = f"NIFTY sentiment bullish ({bullish_count}/{len(signals)}). " + " | ".join(reasoning_parts)
            final_score = 0.25
        elif bearish_count > bullish_count:
            final_signal = "sell"
            final_conf = avg_conf
            final_reason = f"NIFTY sentiment bearish ({bearish_count}/{len(signals)}). " + " | ".join(reasoning_parts)
            final_score = -0.25
        else:
            final_signal = "hold"
            final_conf = 50.0
            final_reason = "NIFTY sentiment mixed. " + " | ".join(reasoning_parts)
            final_score = 0.0
        
        return AgentSignal(
            agent_name=self.agent_name,
            agent_category=self.agent_category.value,
            signal=final_signal,
            confidence=final_conf,
            numerical_score=final_score,
            reasoning=final_reason,
            supporting_data={
                "advances": advances,
                "declines": declines,
                "breadth_ratio": advances / (advances + declines) if advances + declines > 0 else 0.5,
                "above_sma50": above_sma50,
                "above_sma200": above_sma200,
                "sector_leader": max(sector_perf.items(), key=lambda x: x[1])[0] if sector_perf else None,
                "nifty_change": nifty_change,
                "bank_change": bank_change,
            }
        )
