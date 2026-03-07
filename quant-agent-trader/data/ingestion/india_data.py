"""
Indian Market Data Source - NSE/BSE Support

Optimized using yf.download() for bulk fetching (10-20x faster than yf.Ticker)
"""

import asyncio
import pandas as pd
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import logging
import yfinance as yf

logger = logging.getLogger(__name__)


NSE_INDICES = {
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",  # Fixed: was ^NSEB which is deprecated
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
    "AXISBANK": "AXISBANK.NS",
}

BSE_SYMBOLS = {
    "RELIANCE": "RELIANCE.BO",
    "TCS": "TCS.BO",
    "HDFCBANK": "HDFCBANK.BO",
    "INFY": "INFY.BO",
}


class IndiaDataSource:
    """
    Indian market data source using yfinance with optimized bulk downloads.
    Uses yf.download() instead of yf.Ticker() for 10-20x faster performance.
    """
    
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
    
    def _get_period(self, limit: int) -> str:
        """Map limit to yfinance period."""
        if limit <= 7:
            return "7d"
        elif limit <= 30:
            return "1mo"
        elif limit <= 90:
            return "3mo"
        elif limit <= 180:
            return "6mo"
        elif limit <= 365:
            return "1y"
        else:
            return "2y"
    
    async def get_price_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 365
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical price data using yf.download() - optimized.
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
            period = self._get_period(limit)
            
            # Use yf.download() - much faster than yf.Ticker()
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    normalized_symbol,
                    period=period,
                    interval=interval,
                    auto_adjust=True,
                    progress=False
                )
            )
            
            if data.empty:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Handle single vs multi-index columns
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            data.index = data.index.tz_localize(None)
            data.columns = [c.lower() for c in data.columns]
            
            if len(data) > limit:
                data = data.tail(limit)
            
            logger.info(f"Fetched {len(data)} data points for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    async def get_multiple_prices(
        self,
        symbols: List[str],
        timeframe: str = "1d",
        limit: int = 365
    ) -> Dict[str, pd.DataFrame]:
        """
        Bulk fetch data for multiple symbols in ONE request - 10-20x faster!
        """
        try:
            # Normalize all symbols
            normalized = [self._normalize_symbol(s) for s in symbols]
            
            interval = {"1d": "1d", "1h": "1h", "5m": "5m"}.get(timeframe, "1d")
            period = self._get_period(limit)
            
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    normalized,
                    period=period,
                    interval=interval,
                    auto_adjust=True,
                    progress=False,
                    group_by='ticker'  # Group by ticker for easy extraction
                )
            )
            
            result = {}
            
            # Handle both single and multiple symbol responses
            if isinstance(data.columns, pd.MultiIndex):
                for symbol in symbols:
                    norm_sym = self._normalize_symbol(symbol)
                    try:
                        sym_data = data[norm_sym].dropna()
                        if not sym_data.empty:
                            sym_data.columns = [c.lower() for c in sym_data.columns]
                            if len(sym_data) > limit:
                                sym_data = sym_data.tail(limit)
                            result[symbol] = sym_data
                            logger.info(f"Fetched {len(sym_data)} data points for {symbol}")
                    except KeyError:
                        logger.warning(f"No data for {symbol}")
            else:
                # Single symbol response
                if not data.empty:
                    symbols[0]
                    data.columns = [c.lower() for c in data.columns]
                    result[symbols[0]] = data
            
            return result
            
        except Exception as e:
            logger.error(f"Error bulk fetching data: {e}")
            return {}
    
    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get current quote using yf.download() with recent data.
        """
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    normalized_symbol,
                    period="5d",
                    interval="1d",
                    auto_adjust=True,
                    progress=False
                )
            )
            
            if data.empty:
                return None
            
            # Handle column index
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # Ensure lowercase columns
            data.columns = [c.lower() for c in data.columns]
            
            latest = data.iloc[-1]
            prev = data.iloc[-2] if len(data) > 1 else latest
            
            # Handle missing columns gracefully
            def safe_get(col):
                return float(latest[col]) if col in latest and pd.notna(latest[col]) else 0.0
            
            quote = {
                "symbol": symbol.upper(),
                "price": safe_get('close'),
                "previous_close": safe_get('close') if len(data) == 1 else float(prev['close']) if pd.notna(prev.get('close', 0)) else safe_get('close'),
                "open": safe_get('open'),
                "high": safe_get('high'),
                "low": safe_get('low'),
                "volume": int(latest['volume']) if 'volume' in latest and pd.notna(latest.get('volume')) else 0,
            }
            
            return quote
            
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None
    
    async def get_multiple_quotes(
        self,
        symbols: List[str]
    ) -> Dict[str, Dict]:
        """Fetch quotes for multiple symbols using bulk download."""
        try:
            normalized = [self._normalize_symbol(s) for s in symbols]
            
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    normalized,
                    period="5d",
                    interval="1d",
                    auto_adjust=True,
                    progress=False,
                    group_by='ticker'
                )
            )
            
            result = {}
            
            if isinstance(data.columns, pd.MultiIndex):
                for symbol in symbols:
                    norm_sym = self._normalize_symbol(symbol)
                    try:
                        sym_data = data[norm_sym].dropna()
                        if not sym_data.empty:
                            latest = sym_data.iloc[-1]
                            prev = sym_data.iloc[-2] if len(sym_data) > 1 else latest
                            result[symbol] = {
                                "symbol": symbol.upper(),
                                "price": float(latest['close']),
                                "previous_close": float(prev['close']),
                                "open": float(latest['open']),
                                "high": float(latest['high']),
                                "low": float(latest['low']),
                                "volume": int(latest['volume']) if 'volume' in latest else 0,
                            }
                    except (KeyError, IndexError):
                        pass
            
            return result
            
        except Exception as e:
            logger.error(f"Error bulk fetching quotes: {e}")
            return {}
    
    async def get_index_constituents(self, index: str = "NIFTY 50") -> List[str]:
        """Get list of stocks in an index."""
        if index.upper() == "NIFTY 50":
            return list(NSE_SYMBOLS.keys())
        elif index.upper() == "NIFTY BANK":
            return ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "SBIN", "INDUSINDBK", 
                    "AXISBANK", "BANKBARODA", "IDBIBANK", "PNB", "FEDERALBNK"]
        return []


class IndiaVIXSource:
    """Specialized source for India VIX data using yf.download()."""
    
    async def get_india_vix(self, limit: int = 30) -> Optional[pd.DataFrame]:
        """Get India VIX historical data."""
        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    "^INDIAVIX",
                    period="3mo",
                    interval="1d",
                    auto_adjust=True,
                    progress=False
                )
            )
            
            if data is not None and not data.empty:
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                data.index = data.index.tz_localize(None)
                data.columns = [c.lower() for c in data.columns]
                return data.tail(limit)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching India VIX: {e}")
            return None
    
    async def get_current_vix(self) -> Optional[float]:
        """Get current India VIX value."""
        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    "^INDIAVIX",
                    period="5d",
                    interval="1d",
                    auto_adjust=True,
                    progress=False
                )
            )
            
            if data is not None and not data.empty:
                return float(data.iloc[-1]['close'])
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching current VIX: {e}")
            return None


class IndiaDataEngine:
    """
    Unified Indian market data engine using optimized yf.download().
    """
    
    def __init__(self):
        self.source = IndiaDataSource()
        self.vix_source = IndiaVIXSource()
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Convert Indian symbol to yfinance format."""
        return self.source._normalize_symbol(symbol)
    
    async def get_price_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 365
    ) -> Optional[pd.DataFrame]:
        """Get price data for Indian symbol."""
        return await self.source.get_price_data(symbol, timeframe, limit)
    
    async def get_multiple_prices(
        self,
        symbols: List[str],
        timeframe: str = "1d",
        limit: int = 365
    ) -> Dict[str, pd.DataFrame]:
        """Bulk fetch prices for multiple symbols - optimized!"""
        return await self.source.get_multiple_prices(symbols, timeframe, limit)
    
    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get quote for Indian symbol."""
        return await self.source.get_quote(symbol)
    
    async def get_multiple_quotes(
        self,
        symbols: List[str]
    ) -> Dict[str, Dict]:
        """Get quotes for multiple symbols."""
        return await self.source.get_multiple_quotes(symbols)
    
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
        return await self.get_multiple_prices(symbols, **kwargs)


india_data_engine = IndiaDataEngine()
