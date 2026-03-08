"""
AMFI Data Source - Official NAV and Holdings data from Association of Mutual Funds in India

AMFI publishes:
- Daily NAV data: https://www.amfiindia.com/spages/NAVAll.txt
- Monthly portfolio holdings: https://www.amfiindia.com/research-info/holdings

This is the official source for mutual fund data in India.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class AMFIDataSource:
    """
    Fetch daily NAV data and portfolio holdings from AMFI.
    
    Official data source - reliable and comprehensive.
    """
    
    NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
    HOLDINGS_URL = "https://www.amfiindia.com/spages/portfolio-holdings"
    
    POPULAR_SCHEMES = {
        "PPFCF": "119551",
        "SBIBS": "101917",
        "HDFCBS": "103356",
        "ICICIBS": "100080",
        "UTIB": "100046",
    }
    
    SCHEME_CODES = {
        "119551": "Parag Parikh Flexi Cap Fund",
        "101917": "SBI Blue Chip Fund",
        "103356": "HDFC Top 100 Fund",
        "100080": "ICICI Blue Chip Fund",
        "100046": "UTI Flexi Cap Fund",
    }
    
    STOCK_SYMBOL_TO_ISIN = {
        "RELIANCE": "INE002A01018",
        "TCS": "INE467B01029",
        "HDFCBANK": "INE040A01034",
        "INFY": "INE009A01021",
        "ICICIBANK": "INE054A01027",
        "SBIN": "INE062A01020",
        "BHARTIARTL": "INE374A01013",
        "KOTAKBANK": "INE237A01028",
        "HINDUNILVR": "INE030A01027",
        "LT": "INE018A01030",
    }
    
    def __init__(self, cache_minutes: int = 15):
        """
        Initialize AMFI data source.
        
        Args:
            cache_minutes: How long to cache NAV data
        """
        self._cache: Optional[pd.DataFrame] = None
        self._cache_time: Optional[datetime] = None
        self._cache_minutes = cache_minutes
        self._holdings_cache: Dict[str, Any] = {}
        self._holdings_cache_time: Optional[datetime] = None
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
    
    def _is_cache_valid(self) -> bool:
        """Check if cached NAV data is still valid."""
        if self._cache is None or self._cache_time is None:
            return False
        elapsed = (datetime.now() - self._cache_time).total_seconds() / 60
        return elapsed < self._cache_minutes
    
    def _is_holdings_cache_valid(self) -> bool:
        """Check if cached holdings data is still valid."""
        if not self._holdings_cache or self._holdings_cache_time is None:
            return False
        elapsed = (datetime.now() - self._holdings_cache_time).total_seconds() / 3600
        return elapsed < 24
    
    def fetch_nav_data(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Fetch complete NAV data from AMFI.
        
        Args:
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            DataFrame with all mutual fund NAVs
        """
        if not force_refresh and self._is_cache_valid() and self._cache is not None:
            return self._cache
        
        try:
            df = pd.read_csv(
                self.NAV_URL, 
                sep=";", 
                encoding='latin-1',
                on_bad_lines='skip'
            )
            
            df.columns = df.columns.str.strip()
            
            required_cols = ['Scheme Type', 'Scheme Code', 'Net Asset Value']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.warning(f"AMFI data missing columns: {missing_cols}")
                if 'Net Asset Value' not in df.columns:
                    raise ValueError("Required column 'Net Asset Value' not found")
            
            if 'Scheme Type' in df.columns:
                try:
                    df = df[df['Scheme Type'].str.contains('Open', case=False, na=False)]
                    df = df[df['Scheme Type'].str.contains('Growth|ELSS', case=False, na=False)]
                except Exception as e:
                    logger.warning(f"Error filtering scheme type: {e}")
            
            self._cache = df
            self._cache_time = datetime.now()
            
            logger.info(f"Fetched {len(df)} mutual fund NAVs from AMFI")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching AMFI NAV data: {e}")
            return pd.DataFrame() if self._cache is None else self._cache
    
    def get_scheme_nav(self, scheme_code: str) -> Optional[float]:
        """Get NAV for a specific scheme code."""
        df = self.fetch_nav_data()
        
        if df.empty:
            return None
        
        scheme = df[df['Scheme Code'].astype(str) == str(scheme_code)]
        
        if scheme.empty:
            scheme = df[df['Scheme Name'].str.contains(scheme_code, case=False, na=False)]
        
        if not scheme.empty:
            try:
                nav = float(scheme.iloc[0]['Net Asset Value'])
                return nav
            except (ValueError, KeyError):
                return None
        
        return None
    
    def get_scheme_by_name(self, name: str) -> Optional[Dict]:
        """Search for a scheme by name."""
        df = self.fetch_nav_data()
        
        if df.empty:
            return None
        
        matches = df[df['Scheme Name'].str.contains(name, case=False, na=False)]
        
        if not matches.empty:
            row = matches.iloc[0]
            return {
                "scheme_code": str(row['Scheme Code']),
                "name": row['Scheme Name'],
                "nav": row['Net Asset Value'],
                "date": row['Date'],
                "scheme_type": row['Scheme Type'],
                "category": row.get('Category', '')
            }
        
        return None
    
    def get_top_funds_by_category(self, category: str, n: int = 10) -> List[Dict]:
        """Get top N funds by category."""
        df = self.fetch_nav_data()
        
        if df.empty:
            return []
        
        if category:
            df = df[df['Scheme Name'].str.contains(category, case=False, na=False)]
        
        funds = []
        for _, row in df.head(n).iterrows():
            try:
                funds.append({
                    "scheme_code": str(row['Scheme Code']),
                    "name": row['Scheme Name'],
                    "nav": float(row['Net Asset Value']),
                    "date": row['Date']
                })
            except (ValueError, KeyError):
                continue
        
        return funds
    
    def get_equity_schemes(self) -> pd.DataFrame:
        """Get all equity mutual fund schemes."""
        df = self.fetch_nav_data()
        
        if df.empty:
            return df
        
        equity_keywords = ['Growth', 'ELSS', 'Large Cap', 'Mid Cap', 'Small Cap', 
                          'Flexi Cap', 'Multi Cap', 'Value', 'Focus', 'Opportunity']
        
        mask = df['Scheme Name'].str.contains('|'.join(equity_keywords), case=False, na=False)
        return df[mask]
    
    def get_scheme_portfolio(self, scheme_code: str) -> List[Dict]:
        """
        Get portfolio holdings for a specific scheme.
        
        Args:
            scheme_code: AMFI scheme code
            
        Returns:
            List of holdings with stock symbol, quantity, value
        """
        cache_key = f"portfolio_{scheme_code}"
        
        if self._is_holdings_cache_valid() and cache_key in self._holdings_cache:
            return self._holdings_cache[cache_key]
        
        holdings = self._fetch_portfolio_from_amfi(scheme_code)
        
        if self._holdings_cache is None:
            self._holdings_cache = {}
        self._holdings_cache[cache_key] = holdings
        self._holdings_cache_time = datetime.now()
        
        return holdings
    
    def _fetch_portfolio_from_amfi(self, scheme_code: str) -> List[Dict]:
        """Fetch portfolio holdings from AMFI website."""
        try:
            url = f"{self.HOLDINGS_URL}?schemeCode={scheme_code}"
            response = self._session.get(url, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch portfolio for {scheme_code}: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            holdings = []
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        try:
                            symbol = cols[0].get_text(strip=True)
                            quantity = self._parse_number(cols[1].get_text(strip=True))
                            value = self._parse_number(cols[2].get_text(strip=True))
                            
                            if symbol and quantity:
                                holdings.append({
                                    "symbol": symbol,
                                    "quantity": quantity,
                                    "value": value,
                                    "scheme_code": scheme_code
                                })
                        except (ValueError, IndexError):
                            continue
            
            return holdings
            
        except Exception as e:
            logger.error(f"Error fetching portfolio for {scheme_code}: {e}")
            return []
    
    def _parse_number(self, text: str) -> Optional[float]:
        """Parse number from text."""
        if not text:
            return None
        
        text = text.strip()
        text = text.replace(',', '').replace('₹', '').replace('Rs', '')
        
        multipliers = {'Cr': 1e7, 'L': 1e5, 'Lac': 1e5, 'B': 1e9, 'M': 1e6}
        for suffix, mult in multipliers.items():
            if suffix in text:
                try:
                    return float(text.replace(suffix, '').strip()) * mult
                except ValueError:
                    pass
        
        try:
            return float(text)
        except ValueError:
            return None
    
    def get_stock_mf_holdings(self, symbol: str) -> Dict[str, Any]:
        """
        Get MF holdings summary for a specific stock.
        
        Args:
            symbol: NSE stock symbol (e.g., RELIANCE, TCS)
            
        Returns:
            Dict with MF holdings summary for the stock
        """
        cache_key = f"stock_holdings_{symbol}"
        
        if self._is_holdings_cache_valid() and cache_key in self._holdings_cache:
            return self._holdings_cache[cache_key]
        
        holdings = self._aggregate_stock_holdings(symbol)
        
        self._holdings_cache[cache_key] = holdings
        self._holdings_cache_time = datetime.now()
        
        return holdings
    
    def _aggregate_stock_holdings(self, symbol: str) -> Dict[str, Any]:
        """Aggregate holdings for a stock across all equity schemes."""
        equity_schemes = self.get_equity_schemes()
        
        total_value = 0.0
        total_quantity = 0
        scheme_count = 0
        schemes_holding = []
        
        for _, row in equity_schemes.iterrows():
            scheme_code = str(row['Scheme Code'])
            scheme_name = row['Scheme Name']
            
            portfolio = self.get_scheme_portfolio(scheme_code)
            
            for holding in portfolio:
                if symbol.upper() in holding.get('symbol', '').upper():
                    total_value += holding.get('value', 0) or 0
                    total_quantity += holding.get('quantity', 0) or 0
                    scheme_count += 1
                    schemes_holding.append({
                        "scheme_code": scheme_code,
                        "scheme_name": scheme_name,
                        "value": holding.get('value'),
                        "quantity": holding.get('quantity')
                    })
                    break
        
        return {
            "symbol": symbol.upper(),
            "num_schemes": scheme_count,
            "total_value": total_value,
            "total_quantity": total_quantity,
            "schemes_holding": schemes_holding[:20],
            "updated_at": datetime.now().isoformat()
        }
    
    def get_top_mf_holdings_for_stock(self, symbol: str, limit: int = 10) -> List[Dict]:
        """
        Get top mutual funds holding a specific stock.
        
        Args:
            symbol: NSE stock symbol
            limit: Number of top holders to return
            
        Returns:
            List of top MF holders with their holdings
        """
        data = self.get_stock_mf_holdings(symbol)
        
        schemes = data.get('schemes_holding', [])
        sorted_schemes = sorted(
            schemes, 
            key=lambda x: x.get('value', 0) or 0, 
            reverse=True
        )
        
        return sorted_schemes[:limit]
    
    def get_sector_holdings(self, sector: str) -> Dict[str, Any]:
        """
        Get aggregated sector-wise holdings across all MFs.
        
        Args:
            sector: Sector name (e.g., "Banking", "IT", "Pharma")
            
        Returns:
            Dict with sector holdings summary
        """
        equity_schemes = self.get_equity_schemes()
        
        total_value = 0.0
        stock_details = {}
        
        for _, row in equity_schemes.iterrows():
            scheme_code = str(row['Scheme Code'])
            portfolio = self.get_scheme_portfolio(scheme_code)
            
            for holding in portfolio:
                stock = holding.get('symbol', '')
                if sector.upper() in stock.upper():
                    value = holding.get('value', 0) or 0
                    total_value += value
                    
                    if stock not in stock_details:
                        stock_details[stock] = {'value': 0, 'quantity': 0}
                    stock_details[stock]['value'] += value
                    stock_details[stock]['quantity'] += holding.get('quantity', 0) or 0
        
        sorted_stocks = sorted(
            stock_details.items(), 
            key=lambda x: x[1]['value'], 
            reverse=True
        )
        
        return {
            "sector": sector,
            "total_value": total_value,
            "stocks": [
                {"symbol": s, "value": d['value'], "quantity": d['quantity']}
                for s, d in sorted_stocks
            ],
            "updated_at": datetime.now().isoformat()
        }
    
    def get_complete_stock_analysis(self, symbol: str) -> Dict[str, Any]:
        """
        Get complete MF analysis for a stock.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Complete analysis including holdings summary and top holders
        """
        holdings = self.get_stock_mf_holdings(symbol)
        top_holders = self.get_top_mf_holdings_for_stock(symbol, limit=15)
        
        return {
            "symbol": symbol.upper(),
            "holdings": holdings,
            "top_holders": top_holders,
            "analysis": self._analyze_holdings(holdings),
            "timestamp": datetime.now().isoformat()
        }
    
    def _analyze_holdings(self, holdings: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze holdings to generate insights."""
        num_schemes = holdings.get('num_schemes', 0)
        
        if num_schemes == 0:
            return {
                "sentiment": "unknown",
                "institutional_interest": "low",
                "confidence": "low"
            }
        
        if num_schemes >= 30:
            interest = "very_high"
            sentiment = "very_bullish"
        elif num_schemes >= 20:
            interest = "high"
            sentiment = "bullish"
        elif num_schemes >= 10:
            interest = "medium"
            sentiment = "neutral"
        else:
            interest = "low"
            sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "institutional_interest": interest,
            "num_schemes_holding": num_schemes,
            "confidence": "high" if num_schemes >= 15 else "medium"
        }
    
    def clear_cache(self):
        """Clear all cached data."""
        self._cache = None
        self._cache_time = None
        self._holdings_cache = {}
        self._holdings_cache_time = None


amfi_source = AMFIDataSource()
