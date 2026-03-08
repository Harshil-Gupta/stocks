"""
MF Data Engine - Main orchestrator for mutual fund data

Aggregates data from multiple sources:
- AMFI: Official NAV data
- MFAPI: Historical NAV data
- ValueResearch: Portfolio holdings (may be blocked)

Provides unified interface for fetching MF data.
For demonstration, includes realistic simulated data when sources are blocked.
"""

import logging
import random
from typing import Dict, List, Optional, Any
from datetime import datetime

from ingestion.mf.sources.amfi_source import AMFIDataSource, amfi_source
from ingestion.mf.sources.mfapi_source import MFAPIDataSource, mfapi_source
from ingestion.mf.sources.valueresearch_scraper import ValueResearchScraper, value_research_scraper
from ingestion.mf.models import (
    MFHoldingsData,
    MFFundData,
    MFStockHolding,
    InstitutionalHolding,
    MFBuyingSignal,
)
from ingestion.mf.utils.parser import parse_percentage

logger = logging.getLogger(__name__)


# Top Indian equity MFs for analysis
TOP_INDIAN_MFS = {
    "119551": {"name": "Parag Parikh Flexi Cap", "slug": "parag-parikh-flexi-cap-fund"},
    "101917": {"name": "SBI Blue Chip", "slug": "sbi-blue-chip-fund"},
    "103356": {"name": "HDFC Top 100", "slug": "hdfc-top-100-fund"},
    "100080": {"name": "ICICI Blue Chip", "slug": "icici-blue-chip-fund"},
    "100046": {"name": "UTI Flexi Cap", "slug": "uti-flexi-cap-fund"},
    "102918": {"name": "Mirae Asset Large Cap", "slug": "mirae-asset-large-cap-fund"},
    "103364": {"name": "Axis Blue Chip", "slug": "axis-blue-chip-fund"},
}

# Realistic MF holdings for major Indian stocks (simulated for demonstration)
# In production, this would come from actual data sources
MOCK_STOCK_HOLDINGS = {
    "RELIANCE": {
        "num_mfs": 35,
        "mf_holding_pct": 6.2,
        "change_in_holding": 0.45,
        "top_holders": [
            {"holder": "HDFC Top 100 Fund", "pct": 1.2},
            {"holder": "SBI Blue Chip Fund", "pct": 0.95},
            {"holder": "ICICI Blue Chip Fund", "pct": 0.85},
            {"holder": "UTI Flexi Cap Fund", "pct": 0.65},
            {"holder": "Axis Blue Chip Fund", "pct": 0.55},
        ]
    },
    "TCS": {
        "num_mfs": 42,
        "mf_holding_pct": 7.8,
        "change_in_holding": 0.32,
        "top_holders": [
            {"holder": "HDFC Top 100 Fund", "pct": 1.5},
            {"holder": "SBI Blue Chip Fund", "pct": 1.2},
            {"holder": "ICICI Blue Chip Fund", "pct": 1.1},
            {"holder": "Mirae Asset Large Cap", "pct": 0.85},
            {"holder": "UTI Flexi Cap Fund", "pct": 0.75},
        ]
    },
    "HDFCBANK": {
        "num_mfs": 38,
        "mf_holding_pct": 8.1,
        "change_in_holding": -0.25,
        "top_holders": [
            {"holder": "HDFC Top 100 Fund", "pct": 1.8},
            {"holder": "SBI Blue Chip Fund", "pct": 1.4},
            {"holder": "Axis Blue Chip Fund", "pct": 1.0},
            {"holder": "ICICI Blue Chip Fund", "pct": 0.9},
            {"holder": "UTI Flexi Cap Fund", "pct": 0.7},
        ]
    },
    "INFY": {
        "num_mfs": 40,
        "mf_holding_pct": 5.5,
        "change_in_holding": 0.18,
        "top_holders": [
            {"holder": "HDFC Top 100 Fund", "pct": 1.0},
            {"holder": "SBI Blue Chip Fund", "pct": 0.85},
            {"holder": "Mirae Asset Large Cap", "pct": 0.7},
            {"holder": "ICICI Blue Chip Fund", "pct": 0.65},
            {"holder": "UTI Flexi Cap Fund", "pct": 0.5},
        ]
    },
    "HINDUNILVR": {
        "num_mfs": 32,
        "mf_holding_pct": 4.8,
        "change_in_holding": 0.12,
        "top_holders": [
            {"holder": "HDFC Top 100 Fund", "pct": 0.9},
            {"holder": "SBI Blue Chip Fund", "pct": 0.75},
            {"holder": "ICICI Blue Chip Fund", "pct": 0.6},
            {"holder": "UTI Flexi Cap Fund", "pct": 0.45},
            {"holder": "Mirae Asset Large Cap", "pct": 0.4},
        ]
    },
    "ICICIBANK": {
        "num_mfs": 36,
        "mf_holding_pct": 7.2,
        "change_in_holding": 0.35,
        "top_holders": [
            {"holder": "HDFC Top 100 Fund", "pct": 1.4},
            {"holder": "SBI Blue Chip Fund", "pct": 1.1},
            {"holder": "ICICI Blue Chip Fund", "pct": 1.0},
            {"holder": "Axis Blue Chip Fund", "pct": 0.75},
            {"holder": "UTI Flexi Cap Fund", "pct": 0.6},
        ]
    },
    "SBIN": {
        "num_mfs": 28,
        "mf_holding_pct": 5.1,
        "change_in_holding": 0.55,
        "top_holders": [
            {"holder": "SBI Blue Chip Fund", "pct": 1.3},
            {"holder": "HDFC Top 100 Fund", "pct": 0.9},
            {"holder": "UTI Flexi Cap Fund", "pct": 0.7},
            {"holder": "Mirae Asset Large Cap", "pct": 0.55},
            {"holder": "Axis Blue Chip Fund", "pct": 0.45},
        ]
    },
    "KOTAKBANK": {
        "num_mfs": 30,
        "mf_holding_pct": 5.8,
        "change_in_holding": -0.15,
        "top_holders": [
            {"holder": "HDFC Top 100 Fund", "pct": 1.1},
            {"holder": "SBI Blue Chip Fund", "pct": 0.9},
            {"holder": "Axis Blue Chip Fund", "pct": 0.75},
            {"holder": "ICICI Blue Chip Fund", "pct": 0.6},
            {"holder": "UTI Flexi Cap Fund", "pct": 0.5},
        ]
    },
    "LT": {
        "num_mfs": 33,
        "mf_holding_pct": 4.5,
        "change_in_holding": 0.28,
        "top_holders": [
            {"holder": "HDFC Top 100 Fund", "pct": 0.85},
            {"holder": "SBI Blue Chip Fund", "pct": 0.7},
            {"holder": "UTI Flexi Cap Fund", "pct": 0.55},
            {"holder": "ICICI Blue Chip Fund", "pct": 0.5},
            {"holder": "Mirae Asset Large Cap", "pct": 0.45},
        ]
    },
    "BAJFINANCE": {
        "num_mfs": 25,
        "mf_holding_pct": 3.8,
        "change_in_holding": 0.42,
        "top_holders": [
            {"holder": "HDFC Top 100 Fund", "pct": 0.75},
            {"holder": "SBI Blue Chip Fund", "pct": 0.6},
            {"holder": "ICICI Blue Chip Fund", "pct": 0.5},
            {"holder": "UTI Flexi Cap Fund", "pct": 0.4},
            {"holder": "Mirae Asset Large Cap", "pct": 0.35},
        ]
    },
}

# Default holdings for unknown stocks
DEFAULT_HOLDINGS = {
    "num_mfs": random.randint(5, 20),
    "mf_holding_pct": round(random.uniform(1.0, 5.0), 2),
    "change_in_holding": round(random.uniform(-0.5, 0.8), 2),
    "top_holders": []
}


class MFDataEngine:
    """
    Unified MF data engine - aggregates multiple sources.
    
    Provides:
    - NAV data from AMFI
    - Historical NAV from MFAPI
    - Portfolio holdings from ValueResearch
    - Stock-level MF holdings aggregation
    """
    
    def __init__(self):
        """Initialize all data sources."""
        self.amfi = amfi_source
        self.mfapi = mfapi_source
        self.vro = value_research_scraper
        self._top_mfs = TOP_INDIAN_MFS
    
    # =====================
    # Fund-level queries
    # =====================
    
    def get_fund_nav(self, scheme_code: str) -> Optional[float]:
        """
        Get latest NAV for a fund.
        
        Args:
            scheme_code: AMFI scheme code
            
        Returns:
            Latest NAV or None
        """
        return self.amfi.get_scheme_nav(scheme_code)
    
    def get_fund_history(self, scheme_code: str, days: int = 90) -> List[Dict]:
        """
        Get historical NAV for a fund.
        
        Args:
            scheme_code: AMFI scheme code
            days: Number of days of history
            
        Returns:
            List of date/nav pairs
        """
        return self.mfapi.get_nav_history(scheme_code, days)
    
    def get_fund_holdings(self, scheme_code: str) -> List[Dict]:
        """
        Get portfolio holdings for a fund.
        
        Args:
            scheme_code: AMFI scheme code
            
        Returns:
            List of stock holdings
        """
        if scheme_code not in self._top_mfs:
            return []
        
        slug = self._top_mfs[scheme_code]["slug"]
        return self.vro.get_holdings(slug)
    
    def get_fund_info(self, scheme_code: str) -> Dict:
        """
        Get comprehensive fund info.
        
        Args:
            scheme_code: AMFI scheme code
            
        Returns:
            Dict with NAV, holdings, returns, etc.
        """
        info = {
            "scheme_code": scheme_code,
            "name": self._top_mfs.get(scheme_code, {}).get("name", "Unknown"),
        }
        
        # Get NAV
        nav = self.get_fund_nav(scheme_code)
        if nav:
            info["nav"] = nav
        
        # Get holdings
        holdings = self.get_fund_holdings(scheme_code)
        if holdings:
            info["holdings"] = holdings[:10]  # Top 10
            info["top_holding_pct"] = holdings[0]["weight"] if holdings else 0
        
        # Get returns
        returns = self.mfapi.calculate_returns(scheme_code, 30)
        if returns:
            info["returns_30d"] = returns["return_pct"]
        
        returns_90 = self.mfapi.calculate_returns(scheme_code, 90)
        if returns_90:
            info["returns_90d"] = returns_90["return_pct"]
        
        return info
    
    # =====================
    # Stock-level queries
    # =====================
    
    async def get_stock_mf_holdings(self, symbol: str) -> MFHoldingsData:
        """
        Get MF holdings for a specific stock.
        
        This is the key function for smart money analysis.
        Uses mock data for demonstration when external sources are blocked.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE", "HDFCBANK")
            
        Returns:
            MFHoldingsData with aggregated MF holdings
        """
        symbol_upper = symbol.upper()
        holdings_data = MFHoldingsData(symbol=symbol_upper)
        
        # First, try to get real data from ValueResearch
        # (This often fails due to 403 blocking)
        real_data_found = False
        total_weight = 0.0
        mf_count = 0
        top_holders = []
        
        for scheme_code, fund_info in self._top_mfs.items():
            try:
                holdings = self.get_fund_holdings(scheme_code)
                
                # Find this stock in holdings
                for holding in holdings:
                    stock_name = holding.get("stock", "").upper()
                    
                    # Match by symbol (partial match)
                    if symbol_upper in stock_name or stock_name in symbol_upper:
                        weight = holding.get("weight", 0)
                        if weight > 0:
                            total_weight += weight
                            mf_count += 1
                            
                            top_holders.append({
                                "holder": fund_info["name"],
                                "pct": weight,
                                "scheme_code": scheme_code
                            })
                            real_data_found = True
                        break
                        
            except Exception as e:
                logger.debug(f"Error checking {scheme_code} for {symbol}: {e}")
                continue
        
        # If no real data found, use mock data for demonstration
        if not real_data_found:
            # Use predefined mock data for known stocks
            if symbol_upper in MOCK_STOCK_HOLDINGS:
                mock = MOCK_STOCK_HOLDINGS[symbol_upper]
                mf_count = mock["num_mfs"]
                total_weight = mock["mf_holding_pct"]
                holdings_data.change_in_holding = mock["change_in_holding"]
                top_holders = mock["top_holders"].copy()
                logger.info(f"Using simulated MF data for {symbol_upper}")
            else:
                # Generate random data for unknown stocks
                import random
                mf_count = random.randint(5, 25)
                total_weight = round(random.uniform(1.5, 6.0), 2)
                holdings_data.change_in_holding = round(random.uniform(-0.3, 0.6), 2)
                logger.info(f"Using random MF data for unknown stock {symbol_upper}")
        
        holdings_data.num_mfs = mf_count
        holdings_data.mf_holding_pct = round(total_weight, 2)
        
        # Sort top holders by weight
        top_holders.sort(key=lambda x: x.get("pct", 0), reverse=True)
        holdings_data.top_mf_holders = top_holders[:10]
        
        # Generate monthly trend
        holdings_data.monthly_trend = self._generate_trend(mf_count, holdings_data.mf_holding_pct, holdings_data.change_in_holding)
        
        return holdings_data
    
    def _generate_trend(self, mf_count: int, total_pct: float, change: float = 0.0) -> List[Dict]:
        """Generate monthly trend (simulated for demo)."""
        from datetime import datetime
        
        trend = []
        monthly_change = change / 4  # Distribute change across months
        
        for i in range(4):
            month_date = datetime.now()
            month_date = month_date.replace(month=((month_date.month - i - 1) % 12) + 1)
            month_name = month_date.strftime("%b %Y")
            
            # Calculate gradual change
            pct = max(0, total_pct - (monthly_change * (3 - i)))
            
            trend.append({
                "month": month_name,
                "mf_holding_pct": round(pct, 2),
                "num_mfs": max(0, mf_count - i // 2)
            })
        
        return list(reversed(trend))
    
    # =====================
    # Smart money signals
    # =====================
    
    def analyze_stock_mf_signal(self, symbol: str) -> MFBuyingSignal:
        """
        Analyze MF activity for a stock and generate signal.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            MFBuyingSignal with recommendation
        """
        import asyncio
        holdings = asyncio.run(self.get_stock_mf_holdings(symbol))
        
        # Determine signal based on metrics
        if holdings.num_mfs >= 5 and holdings.mf_holding_pct >= 5:
            signal = "accumulating"
            confidence = min(85, 50 + holdings.mf_holding_pct * 2)
        elif holdings.num_mfs >= 3 and holdings.mf_holding_pct >= 2:
            signal = "stable"
            confidence = 55
        elif holdings.change_in_holding > 0.5:
            signal = "accumulating"
            confidence = 65
        elif holdings.change_in_holding < -0.5:
            signal = "distributing"
            confidence = 65
        else:
            signal = "stable"
            confidence = 50
        
        # Determine trend
        if holdings.monthly_trend:
            first_pct = holdings.monthly_trend[0].get("mf_holding_pct", 0)
            last_pct = holdings.monthly_trend[-1].get("mf_holding_pct", 0)
            
            if last_pct > first_pct * 1.1:
                trend = "increasing"
            elif last_pct < first_pct * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "unknown"
        
        # Top funds
        top_funds = [h["holder"] for h in holdings.top_mf_holders[:3]]
        
        return MFBuyingSignal(
            symbol=symbol.upper(),
            signal=signal,
            confidence=confidence,
            mf_count=holdings.num_mfs,
            total_mf_pct=holdings.mf_holding_pct,
            trend=trend,
            top_funds=top_funds,
            reasoning=f"{holdings.num_mfs} MFs holding {holdings.mf_holding_pct}% - trend: {trend}"
        )
    
    # =====================
    # Batch operations
    # =====================
    
    def get_multiple_funds_info(self, scheme_codes: List[str]) -> Dict[str, Dict]:
        """
        Get info for multiple funds.
        
        Args:
            scheme_codes: List of AMFI scheme codes
            
        Returns:
            Dict mapping scheme code to fund info
        """
        results = {}
        for code in scheme_codes:
            try:
                results[code] = self.get_fund_info(code)
            except Exception as e:
                logger.error(f"Error getting info for {code}: {e}")
                results[code] = {"error": str(e)}
        return results
    
    async def get_multiple_stocks_holdings(
        self, 
        symbols: List[str]
    ) -> Dict[str, MFHoldingsData]:
        """
        Get MF holdings for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to holdings data
        """
        import asyncio
        
        tasks = [self.get_stock_mf_holdings(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: (data if not isinstance(data, Exception) else MFHoldingsData(symbol=symbol))
            for symbol, data in zip(symbols, results)
        }


# Global instance
mf_data_engine = MFDataEngine()
