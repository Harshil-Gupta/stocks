"""
Indian Market Data Source - NSE/BSE Support
"""

import asyncio
import aiohttp
import pandas as pd
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import logging
import yfinance as yf

logger = logging.getLogger(__name__)


NSE_INDICES = {
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEB",
    "NIFTY IT": "^CNXIT",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY MEDIA": "^CNXMEDIA",
    "INDIA VIX": "^INDIAVIX",
}

NSE_SYMBOLS = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "INFY": "INFY.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "LT": "LT.NS",
    "HCLTECH": "HCLTECH.NS",
    "ASIANPAINT": "ASIANPAINT.NS",
    "MARUTI": "MARUTI.NS",
    "TITAN": "TITAN.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "WIPRO": "WIPRO.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
    "NTPC": "NTPC.NS",
    "POWERGRID": "POWERGRID.NS",
    "M&M": "M&M.NS",
    "SUNPHARMA": "SUNPHARMA.NS",
    "TATASTEEL": "TATASTEEL.NS",
    "DRREDDY": "DRREDDY.NS",
    "CIPLA": "CIPLA.NS",
    "ADANIPORTS": "ADANIPORTS.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS",
    "GRASIM": "GRASIM.NS",
    "HEROMOTOCO": "HEROMOTOCO.NS",
    "INDUSINDBK": "INDUSINDBK.NS",
    "JSWSTEEL": "JSWSTEEL.NS",
    "SBILIFE": "SBILIFE.NS",
    "SHREECEM": "SHREECEM.NS",
}

BSE_SYMBOLS = {
    "RELIANCE": "RELIANCE.BO",
    "TCS": "TCS.BO",
    "HDFCBANK": "HDFCBANK.BO",
    "INFY": "INFY.BO",
}


class IndiaDataSource:
    """
    Indian market data source using yfinance.
    Supports NSE, BSE, and Indian indices.
    """
    
    def __init__(self):
        self._session_cache: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session_cache is None or self._session_cache.closed:
            self._session_cache = aiohttp.ClientSession()
        return self._session_cache
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Convert Indian symbol to yfinance format."""
        upper_symbol = symbol.upper().strip()
        
        if upper_symbol in NSE_SYMBOLS:
            return NSE_SYMBOLS[upper_symbol]
        
        if upper_symbol in BSE_SYMBOLS:
            return BSE_SYMBOLS[upper_symbol]
        
        if upper_symbol in NSE_INDICES:
            return NSE_INDICES[upper_symbol]
        
        if "." not in symbol:
            return f"{symbol}.NS"
        
        return symbol
    
    def _is_indian_symbol(self, symbol: str) -> bool:
        """Check if symbol is Indian market."""
        upper = symbol.upper()
        return (
            upper in NSE_SYMBOLS or
            upper in BSE_SYMBOLS or
            upper in NSE_INDICES or
            symbol.endswith(".NS") or
            symbol.endswith(".BO")
        )
    
    async def get_price_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 365
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical price data for Indian stocks/indices.
        
        Args:
            symbol: NSE/BSE symbol or name (e.g., RELIANCE, NIFTY 50)
            timeframe: Data timeframe (1d, 1h, 5m, etc.)
            limit: Number of data points
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            
            interval_map = {
                "1d": "1d",
                "1h": "1h",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1wk": "1wk",
                "1mo": "1mo",
            }
            
            interval = interval_map.get(timeframe, "1d")
            
            ticker = yf.Ticker(normalized_symbol)
            
            period_map = {
                7: "7d",
                30: "1mo",
                90: "3mo",
                180: "6mo",
                365: "1y",
                730: "2y",
            }
            period = period_map.get(limit, "1y")
            
            df = ticker.history(period=period, interval=interval, auto_adjust=True)
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            df.index = df.index.tz_localize(None)
            
            if len(df) > limit:
                df = df.tail(limit)
            
            df.columns = [c.lower() for c in df.columns]
            
            logger.info(f"Fetched {len(df)} data points for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get current quote for Indian stock/index.
        
        Args:
            symbol: NSE/BSE symbol
            
        Returns:
            Dictionary with quote data
        """
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            
            ticker = yf.Ticker(normalized_symbol)
            info = ticker.info
            
            if not info or info.get("regularMarketPrice") is None:
                return None
            
            quote = {
                "symbol": symbol.upper(),
                "name": info.get("shortName", info.get("longName", symbol)),
                "price": info.get("regularMarketPrice"),
                "previous_close": info.get("regularMarketPreviousClose"),
                "open": info.get("regularMarketOpen"),
                "high": info.get("regularMarketDayHigh"),
                "low": info.get("regularMarketDayLow"),
                "volume": info.get("regularMarketVolume"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "exchange": info.get("exchange", "NSE"),
                "currency": info.get("currency", "INR"),
            }
            
            return quote
            
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None
    
    async def get_market_depth(self, symbol: str) -> Optional[Dict]:
        """
        Get market depth (order book) for symbol.
        
        Note: yfinance doesn't provide depth data.
        Returns basic quote info as fallback.
        """
        return await self.get_quote(symbol)
    
    async def get_fno_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get F&O specific data (futures, options).
        
        Args:
            symbol: NSE symbol
            
        Returns:
            Dictionary with F&O data
        """
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            ticker = yf.Ticker(normalized_symbol)
            
            info = ticker.info
            
            return {
                "symbol": symbol.upper(),
                "underlying": symbol.upper(),
                "spot_price": info.get("regularMarketPrice"),
                "futures_price": info.get("regularMarketPrice"),
                "open_interest": info.get("averageVolume"),
                "volume": info.get("regularMarketVolume"),
                "implied_volatility": info.get("impliedVolatility"),
                "option_chain": None,
            }
            
        except Exception as e:
            logger.error(f"Error fetching F&O data for {symbol}: {e}")
            return None
    
    async def get_index_constituents(self, index: str = "NIFTY 50") -> List[str]:
        """
        Get list of stocks in an index.
        
        Note: Returns common constituents. For complete list,
        would need a dedicated data source.
        """
        if index.upper() == "NIFTY 50":
            return list(NSE_SYMBOLS.keys())
        elif index.upper() == "NIFTY BANK":
            return ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "SBIN", "INDUSINDBK", 
                    "AXISBANK", "BANKBARODA", "IDBIBANK", "PNB", "FEDERALBNK"]
        return []
    
    async def get_multiple_quotes(
        self,
        symbols: List[str]
    ) -> Dict[str, Dict]:
        """Fetch quotes for multiple symbols."""
        tasks = [self.get_quote(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: data if data else {}
            for symbol, data in zip(symbols, results)
            if not isinstance(data, Exception)
        }


class IndiaVIXSource:
    """Specialized source for India VIX data."""
    
    async def get_india_vix(self, limit: int = 30) -> Optional[pd.DataFrame]:
        """Get India VIX historical data."""
        try:
            ticker = yf.Ticker("^INDIAVIX")
            df = ticker.history(period="3mo", interval="1d", auto_adjust=True)
            
            if df is not None and not df.empty:
                df.index = df.index.tz_localize(None)
                df.columns = [c.lower() for c in df.columns]
                return df.tail(limit)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching India VIX: {e}")
            return None
    
    async def get_current_vix(self) -> Optional[float]:
        """Get current India VIX value."""
        try:
            ticker = yf.Ticker("^INDIAVIX")
            info = ticker.info
            
            return info.get("regularMarketPrice") or info.get("previousClose")
            
        except Exception as e:
            logger.error(f"Error fetching current VIX: {e}")
            return None


class IndiaDataEngine:
    """
    Unified Indian market data engine.
    """
    
    def __init__(self):
        self.source = IndiaDataSource()
        self.vix_source = IndiaVIXSource()
    
    async def get_price_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 365
    ) -> Optional[pd.DataFrame]:
        """Get price data for Indian symbol."""
        return await self.source.get_price_data(symbol, timeframe, limit)
    
    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get quote for Indian symbol."""
        return await self.source.get_quote(symbol)
    
    async def get_india_vix(self, limit: int = 30) -> Optional[pd.DataFrame]:
        """Get India VIX data."""
        return await self.vix_source.get_india_vix(limit)
    
    async def get_current_vix(self) -> Optional[float]:
        """Get current India VIX."""
        return await self.vix_source.get_current_vix()
    
    async def get_multiple_symbols(
        self,
        symbols: List[str],
        **kwargs
    ) -> Dict[str, pd.DataFrame]:
        """Fetch data for multiple Indian symbols."""
        tasks = [
            self.get_price_data(symbol, **kwargs)
            for symbol in symbols
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: data
            for symbol, data in zip(symbols, results)
            if data is not None and not isinstance(data, Exception)
        }


india_data_engine = IndiaDataEngine()
