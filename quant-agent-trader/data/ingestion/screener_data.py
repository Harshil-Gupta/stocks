"""
Screener.in Data Extractor - Financial statements and fundamentals.

This module extracts financial data from Screener.in including:
- Balance sheet
- Profit & Loss
- Cash flow
- Ratios
- Shareholding pattern
- Management information
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


class ScreenerDataExtractor:
    """
    Extract financial data from Screener.in.
    
    Note: This uses web scraping. Rate limit your requests.
    """
    
    BASE_URL = "https://www.screener.in"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    def __init__(self, timeout: int = 30):
        """
        Initialize Screener data extractor.
        
        Args:
            timeout: Request timeout in seconds
        """
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(self.HEADERS)
    
    def _get(self, path: str) -> Optional[str]:
        """Make GET request to Screener."""
        try:
            url = f"{self.BASE_URL}{path}"
            response = self._session.get(url, timeout=self._timeout)
            
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Screener returned {response.status_code}: {path}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Screener timeout: {path}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Screener error: {e}")
        
        return None
    
    def _parse_number(self, text: str) -> Optional[float]:
        """Parse number from text."""
        if not text:
            return None
        
        text = text.strip()
        text = text.replace(',', '').replace('₹', '').replace('Rs', '')
        
        multipliers = {
            'Cr': 1e7,
            'cr': 1e7,
            'L': 1e5,
            'l': 1e5,
            'Lac': 1e5,
            'lac': 1e5,
            'B': 1e9,
            'b': 1e9,
            'M': 1e6,
            'm': 1e6,
            'K': 1e3,
            'k': 1e3,
        }
        
        for suffix, multiplier in multipliers.items():
            if suffix in text:
                try:
                    num = float(text.replace(suffix, '').strip())
                    return num * multiplier
                except ValueError:
                    continue
        
        try:
            return float(text)
        except ValueError:
            return None
    
    def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get company overview.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Dict with company overview
        """
        html = self._get(f"/company/{symbol}/")
        
        if not html:
            return {"error": "Failed to fetch data"}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            "symbol": symbol.upper(),
            "name": soup.title.string if soup.title else "Unknown",
            "sector": "",
            "industry": "",
            "market_cap": None,
            "current_price": None,
            "pe_ratio": None,
            "pb_ratio": None,
            "roe": None,
            "debt_equity": None,
        }
        
        try:
            # Market cap
            mc_elem = soup.find('span', {'class': 'market-cap'})
            if mc_elem:
                result["market_cap"] = self._parse_number(mc_elem.text)
            
            # Current price
            price_elem = soup.find('span', {'class': 'current-price'})
            if price_elem:
                result["current_price"] = self._parse_number(price_elem.text)
            
            # Company name and sector from profile
            for h1 in soup.find_all('h1'):
                if h1.get('class') and 'name' in h1.get('class', []):
                    result["name"] = h1.text.strip()
                    
        except Exception as e:
            logger.debug(f"Error parsing overview: {e}")
        
        return result
    
    def get_profit_loss(self, symbol: str, years: int = 5) -> List[Dict]:
        """
        Get Profit & Loss statement.
        
        Args:
            symbol: NSE stock symbol
            years: Number of years of data
            
        Returns:
            List of P&L data by year
        """
        html = self._get(f"/company/{symbol}/profit-loss/")
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        
        results = []
        
        try:
            table = soup.find('table', {'class': 'profit-loss'})
            if not table:
                return []
            
            headers = []
            header_row = table.find('thead')
            if header_row:
                for th in header_row.find_all('th')[1:years+1]:
                    headers.append(th.text.strip())
            
            rows = table.find('tbody')
            if rows:
                for row in rows.find_all('tr'):
                    cols = row.find_all('td')
                    if len(cols) < 2:
                        continue
                    
                    label = cols[0].text.strip()
                    values = []
                    
                    for col in cols[1:years+1]:
                        val = self._parse_number(col.text)
                        values.append(val)
                    
                    result = {"metric": label}
                    for i, header in enumerate(headers):
                        if i < len(values):
                            result[header] = values[i]
                    
                    results.append(result)
                    
        except Exception as e:
            logger.error(f"Error parsing P&L: {e}")
        
        return results
    
    def get_balance_sheet(self, symbol: str, years: int = 5) -> List[Dict]:
        """
        Get Balance Sheet data.
        
        Args:
            symbol: NSE stock symbol
            years: Number of years of data
            
        Returns:
            List of Balance Sheet data by year
        """
        html = self._get(f"/company/{symbol}/balance-sheet/")
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        
        results = []
        
        try:
            table = soup.find('table', {'class': 'balance-sheet'})
            if not table:
                return []
            
            headers = []
            header_row = table.find('thead')
            if header_row:
                for th in header_row.find_all('th')[1:years+1]:
                    headers.append(th.text.strip())
            
            rows = table.find('tbody')
            if rows:
                for row in rows.find_all('tr'):
                    cols = row.find_all('td')
                    if len(cols) < 2:
                        continue
                    
                    label = cols[0].text.strip()
                    values = []
                    
                    for col in cols[1:years+1]:
                        val = self._parse_number(col.text)
                        values.append(val)
                    
                    result = {"metric": label}
                    for i, header in enumerate(headers):
                        if i < len(values):
                            result[header] = values[i]
                    
                    results.append(result)
                    
        except Exception as e:
            logger.error(f"Error parsing Balance Sheet: {e}")
        
        return results
    
    def get_ratios(self, symbol: str) -> Dict[str, Any]:
        """
        Get key ratios.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Dict with ratios
        """
        html = self._get(f"/company/{symbol}/ratios/")
        
        if not html:
            return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        ratios = {}
        
        try:
            sections = soup.find_all('section', {'class': 'ratios-section'})
            
            for section in sections:
                title = section.find('h3')
                if title:
                    section_name = title.text.strip()
                
                table = section.find('table')
                if table:
                    rows = table.find('tbody')
                    if rows:
                        for row in rows.find_all('tr'):
                            cols = row.find_all('td')
                            if len(cols) >= 2:
                                metric = cols[0].text.strip()
                                value = self._parse_number(cols[1].text)
                                ratios[metric] = value
                                
        except Exception as e:
            logger.error(f"Error parsing ratios: {e}")
        
        return ratios
    
    def get_shareholding_pattern(self, symbol: str) -> List[Dict]:
        """
        Get shareholding pattern.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            List of shareholding data
        """
        html = self._get(f"/company/{symbol}/shareholding/")
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        
        results = []
        
        try:
            table = soup.find('table', {'class': 'shareholding'})
            if not table:
                return []
            
            headers = []
            header_row = table.find('thead')
            if header_row:
                for th in header_row.find_all('th')[1:]:
                    headers.append(th.text.strip())
            
            rows = table.find('tbody')
            if rows:
                for row in rows.find_all('tr'):
                    cols = row.find_all('td')
                    if len(cols) < 2:
                        continue
                    
                    holder = cols[0].text.strip()
                    values = []
                    
                    for col in cols[1:]:
                        val = self._parse_number(col.text)
                        values.append(val)
                    
                    result = {"holder": holder}
                    for i, header in enumerate(headers):
                        if i < len(values):
                            result[header] = values[i]
                    
                    results.append(result)
                    
        except Exception as e:
            logger.error(f"Error parsing shareholding: {e}")
        
        return results
    
    def get_complete_analysis(self, symbol: str) -> Dict[str, Any]:
        """
        Get complete financial analysis.
        
        Args:
            symbol: NSE stock symbol
            
        Returns:
            Dict with all financial data
        """
        logger.info(f"Fetching complete analysis for {symbol}")
        
        return {
            "overview": self.get_company_overview(symbol),
            "profit_loss": self.get_profit_loss(symbol),
            "balance_sheet": self.get_balance_sheet(symbol),
            "ratios": self.get_ratios(symbol),
            "shareholding": self.get_shareholding_pattern(symbol),
            "timestamp": datetime.now().isoformat()
        }


# Global instance
screener_data = ScreenerDataExtractor()


def get_financials(symbol: str) -> Dict[str, Any]:
    """Get complete financial data for a stock."""
    return screener_data.get_complete_analysis(symbol)


def get_ratios(symbol: str) -> Dict[str, Any]:
    """Get key ratios for a stock."""
    return screener_data.get_ratios(symbol)


def get_shareholding(symbol: str) -> List[Dict]:
    """Get shareholding pattern for a stock."""
    return screener_data.get_shareholding_pattern(symbol)
