"""
MF Data Engine - Main orchestrator for mutual fund data

Aggregates data from multiple sources:
- AMFI: Official NAV data
- MFAPI: Historical NAV data
- ValueResearch: Portfolio holdings

Provides unified interface for fetching MF data.
"""

import logging
from typing import Dict, List, Optional, Any

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
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE", "HDFCBANK")
            
        Returns:
            MFHoldingsData with aggregated MF holdings
        """
        holdings_data = MFHoldingsData(symbol=symbol.upper())
        
        # Aggregate holdings from top MFs
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
                    if symbol.upper() in stock_name or stock_name in symbol.upper():
                        weight = holding.get("weight", 0)
                        total_weight += weight
                        mf_count += 1
                        
                        top_holders.append({
                            "holder": fund_info["name"],
                            "pct": weight,
                            "scheme_code": scheme_code
                        })
                        break
                        
            except Exception as e:
                logger.debug(f"Error checking {scheme_code} for {symbol}: {e}")
                continue
        
        holdings_data.num_mfs = mf_count
        holdings_data.mf_holding_pct = round(total_weight, 2)
        
        # Sort top holders by weight
        top_holders.sort(key=lambda x: x["pct"], reverse=True)
        holdings_data.top_mf_holders = top_holders[:10]
        
        # Generate simulated trend (in production, store historical)
        holdings_data.monthly_trend = self._generate_trend(mf_count, total_weight)
        
        # Estimate change (in production, compare with historical)
        if total_weight > 0:
            holdings_data.change_in_holding = round(total_weight * 0.05, 2)  # ~5% change
        
        return holdings_data
    
    def _generate_trend(self, mf_count: int, total_pct: float) -> List[Dict]:
        """Generate monthly trend (simulated for demo)."""
        from datetime import datetime
        
        trend = []
        for i in range(4):
            month_date = datetime.now()
            month_date = month_date.replace(month=((month_date.month - i - 1) % 12) + 1)
            month_name = month_date.strftime("%b %Y")
            
            # Simulate slight variations
            variation = (i * 0.1) if total_pct > 0 else 0
            pct = max(0, total_pct - variation)
            
            trend.append({
                "month": month_name,
                "mf_holding_pct": round(pct, 2),
                "num_mfs": max(0, mf_count - i)
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
