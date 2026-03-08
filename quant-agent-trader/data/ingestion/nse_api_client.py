"""
NSE India API Client - Unofficial API endpoints for NSE data.

This module provides access to various NSE India APIs including:
- Stock quotes
- Corporate announcements
- FII/DII trading data
- Market status
- Derivatives data
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class NSEIndiaAPI:
    """
    NSE India API client for fetching market data.
    
    Uses unofficial endpoints exposed by NSE's frontend.
    """
    
    BASE_URL = "https://www.nseindia.com"
    
    ENDPOINTS = {
        "quote": "/api/quote-equity?symbol={symbol}",
        "quote_derivative": "/api/quote-derivative?symbol={symbol}",
        "corporate_announcements": "/api/corporate-announcements?symbol={symbol}",
        "fiidii": "/api/fiidiiTradeReact",
        "market_status": "/api/marketStatus",
        "indices": "/api/indices?index=true",
        "nifty50": "/api/nifty50",
        "niftybank": "/api/niftybank",
        "gainers": "/api/market-data/pre-open?segment=equity&type=gainers",
        "losers": "/api/market-data/pre-open?segment=equity&type=losers",
        "volume": "/api/market-data/pre-open?segment=equity&type=volume",
        "stock_expiry": "/api/stock-expiry?symbol={symbol}",
        "stock_history": "/api/historical/cm/equity?symbol={symbol}&fromDate={from_date}&toDate={to_date}",
    }
    
    def __init__(self, timeout: int = 15):
        """
        Initialize NSE API client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self._session = self._create_session(timeout)
        self._cookies = self._init_cookies()
    
    def _create_session(self, timeout: int) -> requests.Session:
        """Create a retry-enabled session."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })
        
        return session
    
    def _init_cookies(self) -> Dict[str, str]:
        """Initialize cookies by visiting base URL."""
        try:
            self._session.get(self.BASE_URL, timeout=10)
            return dict(self._session.cookies)
        except Exception as e:
            logger.warning(f"Failed to init cookies: {e}")
            return {}
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make GET request to NSE API."""
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = self._session.get(
                url,
                params=params,
                cookies=self._cookies,
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                logger.warning(f"NSE API access forbidden: {endpoint}")
            else:
                logger.warning(f"NSE API returned {response.status_code}: {endpoint}")
                
        except requests.exceptions.Timeout:
            logger.error(f"NSE API timeout: {endpoint}")
        except requests.exceptions.RequestException as e:
            logger.error(f"NSE API error: {e}")
        
        return None
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get stock quote with full market data.
        
        Args:
            symbol: NSE stock symbol (e.g., RELIANCE)
            
        Returns:
            Dict with quote data or None
        """
        endpoint = self.ENDPOINTS["quote"].format(symbol=symbol)
        return self._get(endpoint)
    
    def get_corporate_announcements(self, symbol: str, limit: int = 50) -> List[Dict]:
        """
        Get corporate announcements for a stock.
        
        Args:
            symbol: NSE stock symbol
            limit: Maximum number of announcements
            
        Returns:
            List of announcements
        """
        endpoint = self.ENDPOINTS["corporate_announcements"].format(symbol=symbol)
        data = self._get(endpoint)
        
        if data and isinstance(data, list):
            return data[:limit]
        return []
    
    def get_fiidii_data(self) -> Optional[Dict]:
        """
        Get FII/DII trading data.
        
        Returns:
            Dict with FII/DII buy/sell data
        """
        endpoint = self.ENDPOINTS["fiidii"]
        return self._get(endpoint)
    
    def get_market_status(self) -> Optional[Dict]:
        """
        Get market status (open/closed).
        
        Returns:
            Dict with market status
        """
        endpoint = self.ENDPOINTS["market_status"]
        return self._get(endpoint)
    
    def get_nifty50_data(self) -> List[Dict]:
        """
        Get Nifty 50 index data.
        
        Returns:
            List of Nifty 50 stocks with data
        """
        endpoint = self.ENDPOINTS["nifty50"]
        data = self._get(endpoint)
        
        if data and isinstance(data, list):
            return data
        return []
    
    def get_niftybank_data(self) -> List[Dict]:
        """
        Get Nifty Bank index data.
        
        Returns:
            List of Nifty Bank stocks with data
        """
        endpoint = self.ENDPOINTS["niftybank"]
        data = self._get(endpoint)
        
        if data and isinstance(data, list):
            return data
        return []
    
    def get_preopen_gainers(self) -> List[Dict]:
        """
        Get pre-market gainers.
        
        Returns:
            List of gainers
        """
        endpoint = self.ENDPOINTS["gainers"]
        data = self._get(endpoint)
        
        if data and isinstance(data, list):
            return data
        return []
    
    def get_preopen_losers(self) -> List[Dict]:
        """
        Get pre-market losers.
        
        Returns:
            List of losers
        """
        endpoint = self.ENDPOINTS["losers"]
        data = self._get(endpoint)
        
        if data and isinstance(data, list):
            return data
        return []
    
    def get_preopen_volume(self) -> List[Dict]:
        """
        Get pre-market volume leaders.
        
        Returns:
            List of high volume stocks
        """
        endpoint = self.ENDPOINTS["volume"]
        data = self._get(endpoint)
        
        if data and isinstance(data, list):
            return data
        return []
    
    def get_historical_data(
        self,
        symbol: str,
        from_date: str,
        to_date: str
    ) -> List[Dict]:
        """
        Get historical price data.
        
        Args:
            symbol: NSE stock symbol
            from_date: Start date (DD-MM-YYYY)
            to_date: End date (DD-MM-YYYY)
            
        Returns:
            List of historical data points
        """
        endpoint = self.ENDPOINTS["stock_history"].format(
            symbol=symbol,
            from_date=from_date,
            to_date=to_date
        )
        data = self._get(endpoint)
        
        if data and isinstance(data, list):
            return data
        return []
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive stock information.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Dict with all available stock data
        """
        quote = self.get_quote(symbol)
        announcements = self.get_corporate_announcements(symbol, limit=10)
        
        result = {
            "symbol": symbol.upper(),
            "quote": quote,
            "announcements": announcements,
            "timestamp": datetime.now().isoformat()
        }
        
        return result


# Global instance
nse_api = NSEIndiaAPI()


def get_quote(symbol: str) -> Optional[Dict]:
    """Get stock quote."""
    return nse_api.get_quote(symbol)


def get_fiidii() -> Optional[Dict]:
    """Get FII/DII data."""
    return nse_api.get_fiidii_data()


def get_market_status() -> Optional[Dict]:
    """Get market status."""
    return nse_api.get_market_status()


def get_nifty50() -> List[Dict]:
    """Get Nifty 50 data."""
    return nse_api.get_nifty50_data()


def get_preopen_data() -> Dict[str, List[Dict]]:
    """Get all pre-open market data."""
    return {
        "gainers": nse_api.get_preopen_gainers(),
        "losers": nse_api.get_preopen_losers(),
        "volume": nse_api.get_preopen_volume()
    }
