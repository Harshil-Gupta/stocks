"""
MF Data Models - Data structures for mutual fund data
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class MFStockHolding:
    """Represents a single stock holding in a mutual fund."""
    symbol: str
    weight: float  # Percentage of portfolio
    shares: float = 0.0
    value: float = 0.0
    change: float = 0.0  # Change in weight from previous period


@dataclass
class MFFundData:
    """Represents a mutual fund's data."""
    scheme_code: str
    name: str
    nav: float = 0.0
    nav_date: Optional[str] = None
    category: str = ""
    holdings: List[MFStockHolding] = field(default_factory=list)
    
    def get_top_holdings(self, n: int = 10) -> List[MFStockHolding]:
        """Get top N holdings by weight."""
        return sorted(self.holdings, key=lambda x: x.weight, reverse=True)[:n]


@dataclass
class MFHoldingsData:
    """Represents aggregated MF holdings for a stock."""
    symbol: str
    num_mfs: int = 0
    mf_holding_pct: float = 0.0  # Total % held by MFs
    change_in_holding: float = 0.0  # Change from previous period
    top_mf_holders: List[Dict[str, Any]] = field(default_factory=list)
    monthly_trend: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "num_mfs_holding": self.num_mfs,
            "mf_holding_pct": self.mf_holding_pct,
            "change_in_holding": self.change_in_holding,
            "top_mf_holders": self.top_mf_holders,
            "monthly_trend": self.monthly_trend,
            "last_updated": self.last_updated
        }


@dataclass
class InstitutionalHolding:
    """Represents institutional holdings (MF + FII + DII)."""
    symbol: str
    mf_holding_pct: float = 0.0
    fii_holding_pct: float = 0.0
    dii_holding_pct: float = 0.0
    mf_change: float = 0.0
    fii_change: float = 0.0
    dii_change: float = 0.0
    
    @property
    def total_institutional(self) -> float:
        """Total institutional ownership."""
        return self.mf_holding_pct + self.fii_holding_pct + self.dii_holding_pct
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "mf_holding_pct": self.mf_holding_pct,
            "fii_holding_pct": self.fii_holding_pct,
            "dii_holding_pct": self.dii_holding_pct,
            "mf_change": self.mf_change,
            "fii_change": self.fii_change,
            "dii_change": self.dii_change,
            "total_institutional": self.total_institutional
        }


@dataclass
class MFBuyingSignal:
    """Signal generated from MF analysis."""
    symbol: str
    signal: str  # "accumulating", "distributing", "stable"
    confidence: float
    mf_count: int
    total_mf_pct: float
    trend: str  # "increasing", "decreasing", "stable"
    top_funds: List[str] = field(default_factory=list)
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "signal": self.signal,
            "confidence": self.confidence,
            "mf_count": self.mf_count,
            "total_mf_pct": self.total_mf_pct,
            "trend": self.trend,
            "top_funds": self.top_funds,
            "reasoning": self.reasoning
        }
