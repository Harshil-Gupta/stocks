"""
Data Ingestion Layer - Market Data Sources
"""

import asyncio
import aiohttp
import pandas as pd
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MarketDataSource(ABC):
    """Abstract base class for market data sources."""
    
    @abstractmethod
    async def get_price_data(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        pass
    
    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[Dict]:
        pass


class PolygonDataSource(MarketDataSource):
    """Polygon.io API implementation."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io/v2"
    
    async def get_price_data(self, symbol: str, timeframe: str = "day", limit: int = 365) -> Optional[pd.DataFrame]:
        """Fetch historical price data from Polygon."""
        try:
            multiplier = 1
            timespan = "day"
            
            # Map timeframe
            if timeframe == "1min":
                multiplier = 1
                timespan = "minute"
            elif timeframe == "5min":
                multiplier = 5
                timespan = "minute"
            elif timeframe == "1hour":
                multiplier = 1
                timespan = "hour"
            
            url = f"{self.base_url}/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{limit}"
            params = {
                "adjusted": "true",
                "sort": "asc",
                "limit": limit,
                "apiKey": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "results" in data:
                            df = pd.DataFrame(data["results"])
                            df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
                            df.set_index('timestamp', inplace=True)
                            df.rename(columns={
                                'o': 'open', 'h': 'high', 'l': 'low', 
                                'c': 'close', 'v': 'volume', 'vw': 'vwap'
                            }, inplace=True)
                            return df
            return None
        except Exception as e:
            logger.error(f"Error fetching data from Polygon: {e}")
            return None
    
    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get current quote from Polygon."""
        try:
            url = f"{self.base_url}/quotes/{symbol}"
            params = {"apiKey": self.api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("results", {})
            return None
        except Exception as e:
            logger.error(f"Error fetching quote: {e}")
            return None


class AlphaVantageSource(MarketDataSource):
    """Alpha Vantage API implementation."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    async def get_price_data(self, symbol: str, timeframe: str = "daily", limit: int = 100) -> Optional[pd.DataFrame]:
        """Fetch historical price data from Alpha Vantage."""
        try:
            function = "TIME_SERIES_DAILY" if timeframe == "daily" else "TIME_SERIES_INTRADAY"
            params = {
                "function": function,
                "symbol": symbol,
                "outputsize": "compact" if limit <= 100 else "full",
                "apikey": self.api_key
            }
            
            if timeframe != "daily":
                params["interval"] = timeframe
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        time_key = "Time Series (Daily)" if timeframe == "daily" else f"Time Series ({timeframe})"
                        if time_key in data:
                            df = pd.DataFrame.from_dict(data[time_key], orient='index')
                            df.index = pd.to_datetime(df.index)
                            df.sort_index(inplace=True)
                            df = df.head(limit)
                            df.columns = [c.split('. ')[1].lower() for c in df.columns]
                            return df
            return None
        except Exception as e:
            logger.error(f"Error fetching from Alpha Vantage: {e}")
            return None
    
    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get current quote from Alpha Vantage."""
        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("Global Quote", {})
            return None
        except Exception as e:
            logger.error(f"Error fetching quote: {e}")
            return None


class DataIngestionEngine:
    """
    Unified data ingestion engine that handles multiple data sources.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sources: Dict[str, MarketDataSource] = {}
        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize data source connections."""
        if self.config.get("polygon_api_key"):
            self.sources["polygon"] = PolygonDataSource(
                self.config["polygon_api_key"]
            )
        
        if self.config.get("alpha_vantage_key"):
            self.sources["alpha_vantage"] = AlphaVantageSource(
                self.config["alpha_vantage_key"]
            )
    
    async def get_price_data(
        self, 
        symbol: str, 
        source: str = "polygon",
        timeframe: str = "daily",
        limit: int = 365
    ) -> Optional[pd.DataFrame]:
        """Get price data from specified source."""
        if source in self.sources:
            return await self.sources[source].get_price_data(symbol, timeframe, limit)
        
        # Try any available source
        for src in self.sources.values():
            data = await src.get_price_data(symbol, timeframe, limit)
            if data is not None:
                return data
        return None
    
    async def get_multiple_symbols(
        self,
        symbols: List[str],
        source: str = "polygon",
        **kwargs
    ) -> Dict[str, pd.DataFrame]:
        """Fetch data for multiple symbols in parallel."""
        tasks = [
            self.get_price_data(symbol, source, **kwargs)
            for symbol in symbols
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: data 
            for symbol, data in zip(symbols, results)
            if data is not None and not isinstance(data, Exception)
        }


class MockDataSource(MarketDataSource):
    """Mock data source for testing."""
    
    def __init__(self):
        pass
    
    async def get_price_data(self, symbol: str, timeframe: str = "day", limit: int = 365) -> pd.DataFrame:
        """Generate mock price data."""
        import numpy as np
        
        dates = pd.date_range(end=datetime.now(), periods=limit, freq='D')
        
        # Generate random walk with drift
        np.random.seed(hash(symbol) % 2**32)
        returns = np.random.normal(0.0005, 0.02, limit)
        prices = 100 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, limit)),
            'high': prices * (1 + np.random.uniform(0, 0.02, limit)),
            'low': prices * (1 - np.random.uniform(0, 0.02, limit)),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, limit)
        }, index=dates)
        
        return df
    
    async def get_quote(self, symbol: str) -> Dict:
        """Generate mock quote."""
        return {
            "symbol": symbol,
            "price": 100 + hash(symbol) % 100,
            "volume": 1000000
        }
