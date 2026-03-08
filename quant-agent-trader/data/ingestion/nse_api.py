"""
NSE India API Client - Comprehensive stock data from nseindia.com

Fetches:
- Price data (OHLC, VWAP, etc.)
- PE, PB ratios
- Market cap, sector, industry
- 52-week high/low
- Stock metadata
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
import logging
import os

import aiohttp
import pandas as pd

logger = logging.getLogger(__name__)


class NSEIndiaAPI:
    """
    NSE India API client for fetching comprehensive stock data.
    
    Uses the public NSE India endpoints (no API key required).
    """
    
    BASE_URL = "https://www.nseindia.com"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nseindia.com/',
    }
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._cookies: Dict[str, str] = {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with cookies."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self.HEADERS,
                cookies=self._cookies
            )
            # Initialize cookies by hitting the main page
            try:
                async with self._session.get(self.BASE_URL, timeout=10) as resp:
                    self._cookies = dict(resp.cookies)
            except Exception:
                pass
        return self._session
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive quote data for a stock.
        
        Args:
            symbol: NSE stock symbol (e.g., RELIANCE, TCS)
            
        Returns:
            Dictionary with comprehensive stock data
        """
        try:
            session = await self._get_session()
            
            url = f"{self.BASE_URL}/api/quote-equity?symbol={symbol}"
            
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self._parse_quote_response(data, symbol)
                else:
                    logger.warning(f"NSE API returned status {resp.status} for {symbol}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching NSE data for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error fetching NSE data for {symbol}: {e}")
            return None
    
    def _parse_quote_response(self, data: Dict, symbol: str) -> Dict[str, Any]:
        """Parse NSE API response into structured format."""
        try:
            info = data.get("info", {})
            price_info = data.get("priceInfo", {})
            metadata = data.get("metadata", {})
            industry_info = data.get("industryInfo", {})
            
            # Extract price data
            result = {
                "symbol": symbol.upper(),
                "name": info.get("companyName", ""),
                
                # Price data
                "last_price": price_info.get("lastPrice", 0),
                "open": price_info.get("open", 0),
                "previous_close": price_info.get("previousClose", 0),
                "intra_day_high": price_info.get("intraDayHighLow", {}).get("max", 0),
                "intra_day_low": price_info.get("intraDayHighLow", {}).get("min", 0),
                "vwap": price_info.get("vwap", 0),
                
                # 52-week data
                "52w_high": price_info.get("weekHighLow", {}).get("max", 0),
                "52w_low": price_info.get("weekHighLow", {}).get("min", 0),
                
                # Volume
                "volume": price_info.get("totalVolume", 0),
                "value": price_info.get("totalValue", 0),
                
                # Fundamental ratios
                "pe_ratio": metadata.get("pdSymbolPe"),  # PE ratio
                "pb_ratio": None,  # Not directly available
                "ps_ratio": None,  # Not directly available
                "market_cap": metadata.get("marketCap"),
                "free_float_market_cap": metadata.get("ffmc"),
                
                # Sector info
                "sector": industry_info.get("sector", ""),
                "industry": industry_info.get("industry", ""),
                
                # Additional metadata
                "listing_date": metadata.get("listingDate"),
                "isin": metadata.get("isin"),
                "face_value": metadata.get("faceValue"),
                "book_value": metadata.get("bookValue"),
                "dividend_yield": metadata.get("divYield"),
                "eps": metadata.get("eps"),
                "ceiling": price_info.get("priceband", {}).get("upperCircuit"),
                "floor": price_info.get("priceband", {}).get("lowerCircuit"),
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing NSE response for {symbol}: {e}")
            return {"symbol": symbol.upper()}
    
    async def get_multiple_quotes(
        self,
        symbols: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch quotes for multiple symbols."""
        tasks = [self.get_quote(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: (data if data and not isinstance(data, Exception) else {"symbol": symbol})
            for symbol, data in zip(symbols, results)
        }
    
    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Global instance
nse_api = NSEIndiaAPI()


class NSEDataEngine:
    """
    High-level data engine using NSE India API.
    Provides unified interface for all stock data needs.
    """
    
    def __init__(self):
        self.api = nse_api
    
    async def get_stock_data(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive stock data."""
        return await self.api.get_quote(symbol)
    
    async def get_fundamental_features(self, symbol: str) -> Dict[str, float]:
        """Get fundamental features for agents."""
        data = await self.api.get_quote(symbol)
        
        if not data:
            return {}
        
        # Map to agent-friendly feature names
        return {
            "pe_ratio": data.get("pe_ratio"),
            "pb_ratio": data.get("pb_ratio"),
            "ps_ratio": data.get("ps_ratio"),
            "market_cap": data.get("market_cap"),
            "eps": data.get("eps"),
            "book_value": data.get("book_value"),
            "dividend_yield": data.get("dividend_yield"),
            "sector": data.get("sector"),
            "industry": data.get("industry"),
        }
    
    async def get_price_features(self, symbol: str) -> Dict[str, Any]:
        """Get price features for technical agents."""
        data = await self.api.get_quote(symbol)
        
        if not data:
            return {}
        
        return {
            "last_price": data.get("last_price"),
            "open": data.get("open"),
            "previous_close": data.get("previous_close"),
            "intra_day_high": data.get("intra_day_high"),
            "intra_day_low": data.get("intra_day_low"),
            "vwap": data.get("vwap"),
            "52w_high": data.get("52w_high"),
            "52w_low": data.get("52w_low"),
            "volume": data.get("volume"),
        }


# Global instance
nse_data_engine = NSEDataEngine()
