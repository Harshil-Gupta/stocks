"""
Upstox Market Data Source

Uses Upstox API to fetch real-time stock prices and market data.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging
import pandas as pd
import requests

logger = logging.getLogger(__name__)


class UpstoxDataSource:
    """
    Upstox API data source for Indian market data.
    
    Supports:
    - LTP (Last Traded Price)
    - OHLC data
    - Market depth
    - Historical data
    """
    
    BASE_URL = "https://api.upstox.com/v2"
    
    # Instrument master mapping (NSE)
    NSE_INSTRUMENTS = {
        "RELIANCE": "RELIANCE",
        "TCS": "TCS",
        "HDFCBANK": "HDFCBANK",
        "INFY": "INFY",
        "HINDUNILVR": "HINDUNILVR",
        "ICICIBANK": "ICICIBANK",
        "SBIN": "SBIN",
        "BHARTIARTL": "BHARTIARTL",
        "KOTAKBANK": "KOTAKBANK",
        "LT": "LT",
        "HCLTECH": "HCLTECH",
        "ASIANPAINT": "ASIANPAINT",
        "MARUTI": "MARUTI",
        "TITAN": "TITAN",
        "BAJFINANCE": "BAJFINANCE",
        "WIPRO": "WIPRO",
        "ULTRACEMCO": "ULTRACEMCO",
        "NTPC": "NTPC",
        "POWERGRID": "POWERGRID",
        "M&M": "M&M",
        "SUNPHARMA": "SUNPHARMA",
        "TATASTEEL": "TATASTEEL",
        "DRREDDY": "DRREDDY",
        "CIPLA": "CIPLA",
        "ADANIPORTS": "ADANIPORTS",
        "BAJAJFINSV": "BAJAJFINSV",
        "GRASIM": "GRASIM",
        "HEROMOTOCO": "HEROMOTOCO",
        "INDUSINDBK": "INDUSINDBK",
        "JSWSTEEL": "JSWSTEEL",
        "SBILIFE": "SBILIFE",
        "SHREECEM": "SHREECEM",
        "AXISBANK": "AXISBANK",
    }
    
    def __init__(self, api_key: str, api_secret: str, access_token: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"
    
    def generate_signature(self, url: str) -> str:
        """Generate HMAC-SHA256 signature for Upstox API."""
        message = url + self.api_secret
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode()
    
    def get_access_token(self, code: str) -> Dict[str, Any]:
        """
        Get access token from authorization code.
        Note: This requires user to complete OAuth flow first.
        """
        url = f"{self.BASE_URL}/login/authorization/token"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        data = {
            "code": code,
            "client_id": self.api_key,
            "client_secret": self.api_secret,
            "grant_type": "authorization_code",
            "redirect_uri": "http://localhost:8501"
        }
        
        response = requests.post(url, data=data, headers=headers)
        return response.json()
    
    def get_profile(self) -> Dict[str, Any]:
        """Get user profile."""
        url = f"{self.BASE_URL}/user/profile"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_ltp(self, instrument: str) -> Optional[Dict[str, Any]]:
        """
        Get Last Traded Price for an instrument.
        
        Args:
            instrument: Stock symbol (e.g., "RELIANCE", "NSE_EQ|RELIANCE")
        
        Returns:
            Dict with price data or None on error
        """
        # Format instrument for Upstox
        if "|" not in instrument:
            instrument = f"NSE_EQ|{instrument}"
        
        url = f"{self.BASE_URL}/market/ltp"
        params = {"instrument": instrument}
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get(instrument, {})
            else:
                logger.warning(f"Upstox LTP error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Upstox LTP exception: {e}")
            return None
    
    def get_quote(self, instrument: str) -> Optional[Dict[str, Any]]:
        """
        Get full quote for an instrument (OHLC, volume, etc).
        
        Args:
            instrument: Stock symbol (e.g., "RELIANCE")
        
        Returns:
            Dict with quote data or None on error
        """
        # Format instrument for Upstox
        if "|" not in instrument:
            instrument = f"NSE_EQ|{instrument}"
        
        url = f"{self.BASE_URL}/market/quote"
        params = {"instrument": instrument}
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get(instrument, {})
            else:
                logger.warning(f"Upstox quote error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Upstox quote exception: {e}")
            return None
    
    def get_historical_data(
        self, 
        instrument: str, 
        interval: str = "1day", 
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLC data.
        
        Args:
            instrument: Stock symbol (e.g., "RELIANCE")
            interval: "1day", "1hour", "30minute", etc.
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
        
        Returns:
            DataFrame with OHLC data or None on error
        """
        # Format instrument for Upstox
        if "|" not in instrument:
            instrument = f"NSE_EQ|{instrument}"
        
        # Default dates
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")
        if not from_date:
            from_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        url = f"{self.BASE_URL}/historical"
        params = {
            "instrument": instrument,
            "interval": interval,
            "from_date": from_date,
            "to_date": to_date
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                candles = data.get("data", {}).get("candles", [])
                
                if not candles:
                    return None
                
                # Convert to DataFrame
                df = pd.DataFrame(candles, columns=[
                    "date", "open", "high", "low", "close", "volume"
                ])
                df["date"] = pd.to_datetime(df["date"])
                return df
            else:
                logger.warning(f"Upstox historical error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Upstox historical exception: {e}")
            return None
    
    def get_market_depth(self, instrument: str) -> Optional[Dict[str, Any]]:
        """
        Get market depth (order book) for an instrument.
        
        Args:
            instrument: Stock symbol (e.g., "RELIANCE")
        
        Returns:
            Dict with buy/sell orders or None on error
        """
        if "|" not in instrument:
            instrument = f"NSE_EQ|{instrument}"
        
        url = f"{self.BASE_URL}/market/depth"
        params = {"instrument": instrument}
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                logger.warning(f"Upstox depth error: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Upstox depth exception: {e}")
            return None
    
    def get_portfolio_holdings(self) -> Optional[List[Dict[str, Any]]]:
        """Get portfolio holdings."""
        url = f"{self.BASE_URL}/portfolio/holdings"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", []), 
            else:
                logger.warning(f"Upstox holdings error: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Upstox holdings exception: {e}")
            return None


class UpstoxDataEngine:
    """
    Data engine that uses Upstox API for Indian stocks.
    Falls back to yfinance if Upstox is not available.
    """
    
    def __init__(self, api_key: str, api_secret: str, access_token: Optional[str] = None):
        self.upstox = UpstoxDataSource(api_key, api_secret, access_token)
        
        # Fallback to yfinance for historical data
        self.use_upstox = bool(access_token and api_key)
        
        if self.use_upstox:
            logger.info("Upstox data engine initialized with live data")
        else:
            logger.warning("Upstox access token not configured, using yfinance fallback")
    
    async def get_price_data(
        self, 
        symbol: str, 
        days: int = 365
    ) -> Optional[pd.DataFrame]:
        """
        Get historical price data for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            days: Number of days of historical data
        
        Returns:
            DataFrame with OHLCV data or None
        """
        # First try Upstox if configured
        if self.use_upstox:
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            to_date = datetime.now().strftime("%Y-%m-%d")
            
            df = self.upstox.get_historical_data(
                symbol, 
                interval="1day",
                from_date=from_date,
                to_date=to_date
            )
            
            if df is not None:
                logger.info(f"Fetched {len(df)} days of data for {symbol} from Upstox")
                return df
        
        # Fallback to yfinance
        return await self._get_yfinance_data(symbol, days)
    
    async def _get_yfinance_data(self, symbol: str, days: int) -> pd.DataFrame:
        """Fallback to yfinance."""
        import yfinance as yf
        
        # Map to Yahoo Finance symbol
        yf_symbol = f"{symbol}.NS"
        
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=f"{days}d")
        
        if df.empty:
            logger.warning(f"No data from yfinance for {symbol}")
            return None
        
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        
        return df
    
    def get_live_price(self, symbol: str) -> Optional[float]:
        """Get live price for a symbol."""
        if self.use_upstox:
            quote = self.upstox.get_quote(symbol)
            if quote:
                return quote.get("last_price")
        
        return None
    
    def get_ohlc(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get OHLC for a symbol."""
        if self.use_upstox:
            quote = self.upstox.get_quote(symbol)
            if quote:
                return {
                    "open": quote.get("ohlc", {}).get("open"),
                    "high": quote.get("ohlc", {}).get("high"),
                    "low": quote.get("ohlc", {}).get("low"),
                    "close": quote.get("last_price")
                }
        
        return None


def get_upstox_engine() -> Optional[UpstoxDataEngine]:
    """Create Upstox data engine from config."""
    from config.settings import DataConfig
    
    config = DataConfig()
    
    if config.upstox_api_key and config.upstox_api_secret:
        # Note: Access token requires OAuth flow
        # For now, return engine without access token (will use yfinance)
        return UpstoxDataEngine(config.upstox_api_key, config.upstox_api_secret)
    
    return None
