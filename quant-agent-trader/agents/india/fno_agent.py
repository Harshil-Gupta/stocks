from typing import Dict, Any, List, Optional
import logging

from signals.signal_schema import AgentSignal, AgentCategory
from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig


logger = logging.getLogger(__name__)


FNO_INDICES = ["NIFTY 50", "NIFTY BANK", "NIFTY IT", "NIFTY PHARMA"]

FNO_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "KOTAKBANK",
    "LT", "HINDUNILVR", "SBIN", "BHARTIARTL", "BAJFINANCE", "M&M",
    "TATASTEEL", "SUNPHARMA", "WIPRO", "HCLTECH", "ASIANPAINT", "AXISBANK",
]


class FNOAgent(BaseAgent):
    """
    F&O (Futures & Options) Analysis Agent for Indian Market.
    
    Analyzes F&O specific metrics including:
    - Futures premium/discount
    - Open interest changes
    - Put-Call ratio
    - Rollover analysis
    - FII/DII activity in derivatives
    """
    
    def __init__(self, config: AgentConfig = None):
        super().__init__(
            agent_name="fno_agent",
            agent_category=AgentCategory.MARKET_STRUCTURE,
            metadata=AgentMetadata(
                version="1.0.0",
                description="F&O analysis agent for Indian derivatives market",
                required_features=[
                    "price", "futures_price", "open_interest", "volume",
                    "put_call_ratio", "fii_activity", "oi_change"
                ],
                tags=["fno", "derivatives", "options", "futures", "india"]
            ),
            config=config
        )
        self.pcr_bullish_threshold = 1.2
        self.pcr_bearish_threshold = 0.7
        self.premium_discount_threshold = 0.02
    
    def _is_fno_stock(self, symbol: str) -> bool:
        """Check if symbol is in F&O segment."""
        return symbol.upper() in FNO_STOCKS
    
    def _analyze_futures_premium(
        self,
        spot_price: float,
        futures_price: float
    ) -> tuple[str, float, str]:
        """Analyze futures premium/discount to spot."""
        
        if futures_price is None or spot_price is None:
            return "neutral", 0.0, "Futures data unavailable"
        
        premium_pct = ((futures_price - spot_price) / spot_price) * 100
        
        if premium_pct > self.premium_discount_threshold:
            return "bullish", premium_pct, (
                f"Futures trading at {premium_pct:.2f}% premium to spot. "
                f"Indicates bullish sentiment."
            )
        elif premium_pct < -self.premium_discount_threshold:
            return "bearish", abs(premium_pct), (
                f"Futures trading at {abs(premium_pct):.2f}% discount to spot. "
                f"Indicates bearish sentiment or backwardation."
            )
        else:
            return "neutral", abs(premium_pct), (
                f"Futures at {premium_pct:.2f}% premium/discount - neutral."
            )
    
    def _analyze_put_call_ratio(
        self,
        pcr: float
    ) -> tuple[str, float, str]:
        """Analyze Put-Call Ratio for market sentiment."""
        
        if pcr is None:
            return "neutral", 0.0, "PCR data unavailable"
        
        if pcr > self.pcr_bullish_threshold:
            return "bullish", min(pcr / 2.0, 1.0), (
                f"PCR at {pcr:.2f} - highly bullish. "
                f"More puts being written than calls."
            )
        elif pcr < self.pcr_bearish_threshold:
            return "bearish", min((1 - pcr), 1.0), (
                f"PCR at {pcr:.2f} - bearish. "
                f"More call writing indicates bullish sentiment being capped."
            )
        else:
            return "neutral", 50.0, (
                f"PCR at {pcr:.2f} - balanced options activity."
            )
    
    def _analyze_oi_change(
        self,
        oi_change_pct: float
    ) -> tuple[str, float, str]:
        """Analyze open interest changes."""
        
        if oi_change_pct is None:
            return "neutral", 0.0, "OI data unavailable"
        
        if oi_change_pct > 20:
            return "bullish", 70.0, (
                f"OI surged {oi_change_pct:.1f}% - fresh positions building. "
                f"Strong directional move expected."
            )
        elif oi_change_pct > 10:
            return "neutral", 55.0, (
                f"OI up {oi_change_pct:.1f}% - new positions being added."
            )
        elif oi_change_pct < -20:
            return "bearish", 70.0, (
                f"OI down {abs(oi_change_pct):.1f}% - positions being unwound. "
                f"Possible trend reversal."
            )
        elif oi_change_pct < -10:
            return "neutral", 55.0, (
                f"OI down {abs(oi_change_pct):.1f}% - positions being closed."
            )
        else:
            return "neutral", 50.0, (
                f"OI relatively stable ({oi_change_pct:.1f}% change)."
            )
    
    def _analyze_fii_activity(
        self,
        fii_buy: float,
        fii_sell: float
    ) -> tuple[str, float, str]:
        """Analyze FII (Foreign Institutional Investor) activity."""
        
        if fii_buy is None or fii_sell is None:
            return "neutral", 0.0, "FII data unavailable"
        
        net_fii = fii_buy - fii_sell
        
        if net_fii > 1000:
            return "bullish", min(net_fii / 5000, 1.0) * 100, (
                f"FII net buy: ₹{net_fii:.0f}Cr. Foreign investors bullish."
            )
        elif net_fii < -1000:
            return "bearish", min(abs(net_fii) / 5000, 1.0) * 100, (
                f"FII net sell: ₹{abs(net_fii):.0f}Cr. Foreign investors bearish."
            )
        else:
            return "neutral", 50.0, (
                f"FII activity muted (Net: ₹{net_fii:.0f}Cr)."
            )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """Compute F&O based trading signal."""
        
        symbol = features.get("symbol", "UNKNOWN")
        
        if not self._is_fno_stock(symbol):
            return AgentSignal(
                agent_name=self.agent_name,
                agent_category=self.agent_category.value,
                signal="hold",
                confidence=50.0,
                numerical_score=0.0,
                reasoning=f"{symbol} not in F&O segment - skipping F&O analysis",
                supporting_data={"fno_stock": False}
            )
        
        spot_price = features.get("price")
        futures_price = features.get("futures_price")
        pcr = features.get("put_call_ratio")
        oi_change = features.get("oi_change")
        fii_buy = features.get("fii_buy", 0)
        fii_sell = features.get("fii_sell", 0)
        
        premium_signal, premium_score, premium_reason = self._analyze_futures_premium(
            spot_price, futures_price
        )
        
        pcr_signal, pcr_score, pcr_reason = self._analyze_put_call_ratio(pcr)
        
        oi_signal, oi_score, oi_reason = self._analyze_oi_change(oi_change)
        
        fii_signal, fii_score, fii_reason = self._analyze_fii_activity(fii_buy, fii_sell)
        
        bullish_signals = 0
        bearish_signals = 0
        total_confidence = 0
        
        signals = [
            (premium_signal, premium_score),
            (pcr_signal, pcr_score),
            (oi_signal, oi_score),
            (fii_signal, fii_score),
        ]
        
        reasoning_parts = [
            premium_reason,
            pcr_reason,
            oi_reason,
            fii_reason,
        ]
        
        for sig, conf in signals:
            total_confidence += conf
            if sig == "bullish":
                bullish_signals += 1
            elif sig == "bearish":
                bearish_signals += 1
        
        if bullish_signals > bearish_signals:
            final_signal = "buy"
            final_confidence = total_confidence / len(signals)
            final_reason = f"F&O: {bullish_signals} bullish signals. " + " | ".join(reasoning_parts)
            final_score = 0.3
        elif bearish_signals > bullish_signals:
            final_signal = "sell"
            final_confidence = total_confidence / len(signals)
            final_reason = f"F&O: {bearish_signals} bearish signals. " + " | ".join(reasoning_parts)
            final_score = -0.3
        else:
            final_signal = "hold"
            final_confidence = 50.0
            final_reason = f"F&O: Mixed signals. " + " | ".join(reasoning_parts)
            final_score = 0.0
        
        return AgentSignal(
            agent_name=self.agent_name,
            agent_category=self.agent_category.value,
            signal=final_signal,
            confidence=final_confidence,
            numerical_score=final_score,
            reasoning=final_reason,
            supporting_data={
                "fno_stock": True,
                "premium_signal": premium_signal,
                "pcr": pcr,
                "oi_change": oi_change,
                "fii_net": fii_buy - fii_sell,
                "bullish_count": bullish_signals,
                "bearish_count": bearish_signals,
            }
        )
