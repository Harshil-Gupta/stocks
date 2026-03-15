"""
Upstox API V3 Data Source

Real-time and historical market data from Upstox API V3.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class UpstoxClient:
    """
    Upstox API V3 Client for Indian market data.

    Usage:
        client = UpstoxClient()
        data = client.get_historical("RELIANCE", "days", "1", "2024-01-01", "2025-01-01")
    """

    BASE_URL = "https://api.upstox.com/v3"

    INSTRUMENT_KEYS = {
        "RELIANCE": "NSE_EQ|INE002A01018",
        "TCS": "NSE_EQ|INE467B01029",
        "INFY": "NSE_EQ|INE009A01021",
        "HDFCBANK": "NSE_EQ|INE040A01034",
        "ICICIBANK": "NSE_EQ|INE090A01021",
        "SBIN": "NSE_EQ|INE062A01020",
        "HINDUNILVR": "NSE_EQ|INE030A01027",
        "BHARTIARTL": "NSE_EQ|INE374D01026",
        "KOTAKBANK": "NSE_EQ|INE237A01025",
        "LT": "NSE_EQ|INE018A01030",
        "HCLTECH": "NSE_EQ|INE860A01027",
        "ASIANPAINT": "NSE_EQ|INE021A01026",
        "MARUTI": "NSE_EQ|INE585B01010",
        "TITAN": "NSE_EQ|INE280A01028",
        "BAJFINANCE": "NSE_EQ|INE099E01015",
        "WIPRO": "NSE_EQ|INE075A01022",
        "ULTRACEMCO": "NSE_EQ|INE481G01011",
        "NTPC": "NSE_EQ|INE733E01017",
        "POWERGRID": "NSE_EQ|INE752E01010",
        "M&M": "NSE_EQ|INE101A01026",
        "SUNPHARMA": "NSE_EQ|INE044A01036",
        "TATASTEEL": "NSE_EQ|INE040A01034",
        "AXISBANK": "NSE_EQ|INE238A01034",
    }

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize Upstox client.

        Args:
            access_token: Upstox access token. Reads from UPSTOX_TOKEN env if not provided.
        """
        self.access_token = access_token or os.getenv("UPSTOX_ACCESS_TOKEN")

        if not self.access_token:
            logger.warning(
                "No Upstox access token found. Set UPSTOX_ACCESS_TOKEN env variable."
            )

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}" if self.access_token else "",
        }

    def _get_instrument_key(self, symbol: str) -> str:
        """Get instrument key for symbol."""
        if "|" in symbol:
            return symbol

        return self.INSTRUMENT_KEYS.get(symbol.upper(), f"NSE_EQ|{symbol}")

    def get_historical(
        self,
        symbol: str,
        unit: str = "days",
        interval: str = "1",
        to_date: str = None,
        from_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data from Upstox API V3.

        Args:
            symbol: Stock symbol (e.g., "RELIANCE") or instrument key
            unit: Time unit - "minutes", "hours", "days", "weeks", "months"
            interval: Interval value - e.g., "1" for days, "5" for 5 minutes
            to_date: End date (YYYY-MM-DD)
            from_date: Start date (YYYY-MM-DD) - optional

        Returns:
            DataFrame with OHLCV data or None on error
        """
        if not self.access_token:
            logger.error("No access token configured")
            return None

        instrument_key = self._get_instrument_key(symbol)

        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")

        # Note: to_date comes BEFORE from_date in the URL (as per Upstox API)
        # URL format: /historical-candle/{key}/{unit}/{interval}/{to_date}/{from_date}
        url = f"{self.BASE_URL}/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}"

        if from_date:
            url += f"/{from_date}"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                candles = data.get("data", {}).get("candles", [])

                if not candles:
                    logger.warning(f"No candle data for {symbol}")
                    return None

                df = pd.DataFrame(
                    candles,
                    columns=[
                        "timestamp",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "oi",
                    ],
                )

                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.set_index("timestamp")

                df["open"] = pd.to_numeric(df["open"], errors="coerce")
                df["high"] = pd.to_numeric(df["high"], errors="coerce")
                df["low"] = pd.to_numeric(df["low"], errors="coerce")
                df["close"] = pd.to_numeric(df["close"], errors="coerce")
                df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
                df["oi"] = pd.to_numeric(df["oi"], errors="coerce")

                df = df.sort_index()

                return df

            elif response.status_code == 401:
                logger.error("Upstox authentication failed. Check access token.")
            elif response.status_code == 429:
                logger.warning("Upstox rate limit hit")
            else:
                logger.error(
                    f"Upstox API error: {response.status_code} - {response.text[:200]}"
                )

            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Upstox request failed: {e}")
            return None

    def get_daily(
        self, symbol: str, from_date: str, to_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """Get daily OHLCV data."""
        return self.get_historical(
            symbol,
            "days",
            "1",
            to_date or datetime.now().strftime("%Y-%m-%d"),
            from_date,
        )

    def get_weekly(
        self, symbol: str, from_date: str, to_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """Get weekly OHLCV data."""
        return self.get_historical(
            symbol,
            "weeks",
            "1",
            to_date or datetime.now().strftime("%Y-%m-%d"),
            from_date,
        )

    def get_minute(
        self,
        symbol: str,
        interval: int = 5,
        to_date: str = None,
        from_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """Get minute-level OHLCV data."""
        return self.get_historical(
            symbol,
            "minutes",
            str(interval),
            to_date or datetime.now().strftime("%Y-%m-%d"),
            from_date,
        )

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current quote for symbol.

        Returns:
            Dict with LTP, open, high, low, close, volume, etc.
        """
        if not self.access_token:
            return None

        instrument_key = self._get_instrument_key(symbol)
        url = f"{self.BASE_URL}/quote/{instrument_key}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json().get("data", {})

            return None
        except Exception as e:
            logger.error(f"Quote request failed: {e}")
            return None

    def search_instrument(self, query: str) -> List[Dict]:
        """Search for instruments by name/symbol."""
        if not self.access_token:
            return []

        url = f"{self.BASE_URL}/instruments/search"
        params = {"q": query}

        try:
            response = requests.get(
                url, params=params, headers=self.headers, timeout=10
            )

            if response.status_code == 200:
                return response.json().get("data", [])

            return []
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []


def get_upstox_client() -> UpstoxClient:
    """Factory function to get Upstox client."""
    return UpstoxClient()


def fetch_symbol_data(
    symbol: str,
    from_date: str,
    to_date: Optional[str] = None,
    unit: str = "days",
    interval: str = "1",
) -> Optional[pd.DataFrame]:
    """
    Fetch historical data for a symbol.

    Args:
        symbol: Stock symbol (e.g., "RELIANCE")
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        unit: Time unit (days, hours, minutes, weeks, months)
        interval: Interval value

    Returns:
        DataFrame with OHLCV data
    """
    client = UpstoxClient()
    return client.get_historical(symbol, unit, interval, to_date, from_date)


__all__ = [
    "UpstoxClient",
    "get_upstox_client",
    "fetch_symbol_data",
]
