"""
Unified Data Services Layer

Provides a single interface to access all data sources:
- NSE India (quotes, corporate announcements, FII/DII)
- Screener.in (financial statements, ratios)
- RBI (macro economic data)
- MF Holdings (mutual fund holdings)
- AMFI (mutual fund NAVs)
- Market data (price history, technical indicators)
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from data.ingestion.nse_api_client import nse_api, get_quote, get_fiidii, get_nifty50
from data.ingestion.screener_data import screener_data, get_financials, get_ratios
from data.ingestion.rbi_macro import rbi_macro, get_macro_snapshot, get_policy_rates, get_regime
from data.ingestion.mf_data import mf_data_engine
from ingestion.mf.sources.amfi_source import amfi_source
from data.ingestion.india_data import india_data_engine

logger = logging.getLogger(__name__)


class DataServiceRegistry:
    """Registry of all available data services."""
    
    NSE_QUOTES = "nse_quotes"
    NSE_CORP_ANNOUNCEMENTS = "nse_corp_announcements"
    NSE_FII_DII = "nse_fii_dii"
    NSE_INDICES = "nse_indices"
    SCREENER_FINANCIALS = "screener_financials"
    SCREENER_RATIOS = "screener_ratios"
    SCREENER_SHAREHOLDING = "screener_shareholding"
    RBI_MACRO = "rbi_macro"
    RBI_POLICY = "rbi_policy"
    RBI_REGIME = "rbi_regime"
    MF_HOLDINGS = "mf_holdings"
    FII_HOLDINGS = "fii_holdings"
    MF_NAV = "mf_nav"
    MARKET_DATA = "market_data"


class UnifiedDataService:
    """
    Unified data service providing single interface to all data sources.
    
    Features:
    - Single point of access for all data
    - Automatic caching and rate limiting
    - Error handling and fallback mechanisms
    - Batch fetching for multiple symbols
    """
    
    def __init__(self, cache_enabled: bool = True):
        """
        Initialize unified data service.
        
        Args:
            cache_enabled: Enable caching for API responses
        """
        self._cache_enabled = cache_enabled
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, datetime] = {}
        self._default_ttl_seconds = 300  # 5 minutes
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """Get cached value if valid."""
        if not self._cache_enabled or key not in self._cache:
            return None
        
        cached_time = self._cache_ttl.get(key)
        if cached_time:
            age = (datetime.now() - cached_time).total_seconds()
            if age < self._default_ttl_seconds:
                return self._cache[key]
        
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Set cache value."""
        if self._cache_enabled:
            self._cache[key] = value
            self._cache_ttl[key] = datetime.now()
    
    def clear_cache(self, key: Optional[str] = None):
        """Clear cache for specific key or all."""
        if key:
            self._cache.pop(key, None)
            self._cache_ttl.pop(key, None)
        else:
            self._cache.clear()
            self._cache_ttl.clear()
    
    async def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get stock quote from NSE.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Dict with quote data
        """
        cache_key = f"quote_{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        quote = get_quote(symbol)
        result = quote if quote else {"symbol": symbol, "error": "Failed to fetch quote"}
        
        self._set_cache(cache_key, result)
        return result
    
    async def get_stock_financials(self, symbol: str) -> Dict[str, Any]:
        """
        Get complete financial data from Screener.in.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Dict with financial statements, ratios, shareholding
        """
        cache_key = f"financials_{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        financials = get_financials(symbol)
        
        self._set_cache(cache_key, financials)
        return financials
    
    async def get_stock_ratios(self, symbol: str) -> Dict[str, Any]:
        """
        Get key ratios from Screener.in.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Dict with ratios
        """
        cache_key = f"ratios_{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        ratios = get_ratios(symbol)
        
        self._set_cache(cache_key, ratios)
        return ratios
    
    async def get_mf_holdings(self, symbol: str) -> Dict[str, Any]:
        """
        Get mutual fund holdings for a stock.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Dict with MF holdings data
        """
        cache_key = f"mf_holdings_{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        mf_data = await mf_data_engine.get_mf_holdings(symbol)
        result = mf_data.to_dict()
        
        self._set_cache(cache_key, result)
        return result
    
    async def get_fii_holdings(self, symbol: str) -> Dict[str, Any]:
        """
        Get FII holdings for a stock.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Dict with FII holdings data
        """
        cache_key = f"fii_holdings_{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        fii_data = await mf_data_engine.get_fii_holdings(symbol)
        
        self._set_cache(cache_key, fii_data)
        return fii_data
    
    async def get_institutional_analysis(self, symbol: str) -> Dict[str, Any]:
        """
        Get combined MF and FII holdings analysis.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Dict with combined analysis
        """
        cache_key = f"institutional_{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        analysis = await mf_data_engine.get_combined_analysis(symbol)
        
        self._set_cache(cache_key, analysis)
        return analysis
    
    def get_macro_data(self) -> Dict[str, Any]:
        """
        Get complete macro economic data from RBI.
        
        Returns:
            Dict with macro data
        """
        cache_key = "macro_data"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        macro = get_macro_snapshot()
        
        self._set_cache(cache_key, macro)
        return macro
    
    def get_rbi_policy_rates(self) -> Dict[str, Any]:
        """
        Get RBI policy rates.
        
        Returns:
            Dict with policy rates
        """
        cache_key = "rbi_policy_rates"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        rates = get_policy_rates()
        
        self._set_cache(cache_key, rates)
        return rates
    
    def get_macro_regime(self) -> str:
        """
        Get current macro regime indicator.
        
        Returns:
            Regime string: 'expansion', 'inflationary', 'neutral', 'tightening'
        """
        cache_key = "macro_regime"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        regime = get_regime()
        
        self._set_cache(cache_key, regime)
        return regime
    
    def get_fii_dii_data(self) -> Dict[str, Any]:
        """
        Get FII/DII trading data from NSE.
        
        Returns:
            Dict with FII/DII buy/sell data
        """
        cache_key = "fii_dii"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        data = get_fiidii()
        result = data if data else {"error": "Failed to fetch FII/DII data"}
        
        self._set_cache(cache_key, result)
        return result
    
    def get_nifty50(self) -> List[Dict[str, Any]]:
        """
        Get Nifty 50 index data.
        
        Returns:
            List of Nifty 50 stocks
        """
        cache_key = "nifty50"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        data = get_nifty50()
        
        self._set_cache(cache_key, data)
        return data
    
    def get_mf_nav(self, scheme_code: str) -> Optional[float]:
        """
        Get mutual fund NAV from AMFI.
        
        Args:
            scheme_code: AMFI scheme code
            
        Returns:
            NAV value or None
        """
        cache_key = f"mf_nav_{scheme_code}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        nav = amfi_source.get_scheme_nav(scheme_code)
        
        self._set_cache(cache_key, nav)
        return nav
    
    def get_stock_mf_holdings(self, symbol: str) -> Dict[str, Any]:
        """
        Get direct AMFI MF holdings for a stock.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Dict with MF holdings data from AMFI
        """
        cache_key = f"amfi_stock_holdings_{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        holdings = amfi_source.get_stock_mf_holdings(symbol)
        
        self._set_cache(cache_key, holdings)
        return holdings
    
    def get_top_mf_holders(self, symbol: str, limit: int = 10) -> List[Dict]:
        """
        Get top mutual funds holding a stock.
        
        Args:
            symbol: NSE stock symbol
            limit: Number of top holders
            
        Returns:
            List of top MF holders
        """
        cache_key = f"amfi_top_holders_{symbol}_{limit}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        top_holders = amfi_source.get_top_mf_holdings_for_stock(symbol, limit)
        
        self._set_cache(cache_key, top_holders)
        return top_holders
    
    def get_sector_holdings(self, sector: str) -> Dict[str, Any]:
        """
        Get sector-wise MF holdings aggregated.
        
        Args:
            sector: Sector name (e.g., "Banking", "IT")
            
        Returns:
            Dict with sector holdings
        """
        cache_key = f"amfi_sector_{sector}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        holdings = amfi_source.get_sector_holdings(sector)
        
        self._set_cache(cache_key, holdings)
        return holdings
    
    async def get_complete_stock_analysis(self, symbol: str) -> Dict[str, Any]:
        """
        Get complete analysis for a stock (quotes + financials + holdings).
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Dict with all available data
        """
        quote_task = self.get_stock_quote(symbol)
        financials_task = self.get_stock_financials(symbol)
        institutional_task = self.get_institutional_analysis(symbol)
        
        quote, financials, institutional = await asyncio.gather(
            quote_task, financials_task, institutional_task
        )
        
        return {
            "symbol": symbol.upper(),
            "quote": quote,
            "financials": financials,
            "institutional": institutional,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_batch_analysis(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get complete analysis for multiple stocks.
        
        Args:
            symbols: List of NSE stock symbols
            
        Returns:
            Dict mapping symbol to analysis data
        """
        tasks = [self.get_complete_stock_analysis(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: (data if not isinstance(data, Exception) else {"error": str(data)})
            for symbol, data in zip(symbols, results)
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get dashboard data (macro + indices + FII/DII).
        
        Returns:
            Dict with dashboard data
        """
        macro = self.get_macro_data()
        nifty = self.get_nifty50()
        fii_dii = self.get_fii_dii_data()
        regime = self.get_macro_regime()
        
        return {
            "macro": macro,
            "nifty50": nifty,
            "fii_dii": fii_dii,
            "macro_regime": regime,
            "timestamp": datetime.now().isoformat()
        }


unified_data_service = UnifiedDataService()


async def get_stock_data(symbol: str) -> Dict[str, Any]:
    """Get complete stock data."""
    return await unified_data_service.get_complete_stock_analysis(symbol)


async def get_market_dashboard() -> Dict[str, Any]:
    """Get market dashboard data."""
    return unified_data_service.get_dashboard_data()


async def get_institutional_holdings(symbol: str) -> Dict[str, Any]:
    """Get MF and FII holdings."""
    return await unified_data_service.get_institutional_analysis(symbol)


def get_macro() -> Dict[str, Any]:
    """Get macro data."""
    return unified_data_service.get_macro_data()


def get_regime() -> str:
    """Get macro regime."""
    return unified_data_service.get_macro_regime()


def get_amfi_stock_holdings(symbol: str) -> Dict[str, Any]:
    """Get AMFI MF holdings for a stock."""
    return unified_data_service.get_stock_mf_holdings(symbol)


def get_amfi_top_holders(symbol: str, limit: int = 10) -> List[Dict]:
    """Get top MF holders for a stock."""
    return unified_data_service.get_top_mf_holders(symbol, limit)


def get_amfi_sector_holdings(sector: str) -> Dict[str, Any]:
    """Get sector-wise MF holdings."""
    return unified_data_service.get_sector_holdings(sector)
