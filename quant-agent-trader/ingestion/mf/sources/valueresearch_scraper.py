"""
ValueResearch Scraper - Mutual fund portfolio holdings from ValueResearchOnline.com

Value Research Online provides detailed portfolio holdings for mutual funds.
This scraper extracts stock holdings from their pages.

Note: Web scraping should be done responsibly and in compliance with ToS.
"""

import logging
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ValueResearchScraper:
    """
    Scrape mutual fund portfolio data from Value Research Online.
    
    Provides:
    - Top holdings of a fund
    - Sector allocation
    - Portfolio changes
    """
    
    BASE_URL = "https://www.valueresearchonline.com"
    FUND_URL = f"{BASE_URL}/funds"
    
    # Common fund slugs for major Indian MFs
    FUND_SLUGS = {
        "ppfcf": "parag-parikh-flexi-cap-fund",
        "sbi-blue-chip": "sbi-blue-chip-fund",
        "hdfc-top-100": "hdfc-top-100-fund",
        "icici-blue-chip": "icici-blue-chip-fund",
        "uti-flexi": "uti-flexi-cap-fund",
    }
    
    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    def get_holdings(self, fund_slug: str) -> List[Dict]:
        """
        Get top holdings for a mutual fund.
        
        Args:
            fund_slug: URL-friendly fund name (e.g., "parag-parikh-flexi-cap-fund")
            
        Returns:
            List of holdings with stock name, weight, etc.
        """
        try:
            url = f"{self.FUND_URL}/{fund_slug}/portfolio"
            response = self._session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"VRO returned status {response.status_code} for {fund_slug}")
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            holdings = []
            
            # Find holdings table - typically in "Holdings" section
            tables = soup.find_all("table")
            
            for table in tables:
                # Look for tables with stock data
                rows = table.find_all("tr")[1:]  # Skip header
                
                for row in rows:
                    cols = row.find_all("td")
                    
                    if len(cols) >= 3:
                        # Try to extract stock name and weight
                        stock_link = cols[0].find("a")
                        if stock_link:
                            stock_name = stock_link.text.strip()
                            weight_text = cols[1].text.strip() if len(cols) > 1 else "0%"
                            
                            # Parse weight
                            weight = self._parse_percentage(weight_text)
                            
                            if stock_name and weight > 0:
                                holding = {
                                    "stock": stock_name,
                                    "weight": weight,
                                    "type": "Equity"
                                }
                                
                                # Try to get sector if available
                                if len(cols) > 2:
                                    sector = cols[2].text.strip()
                                    if sector:
                                        holding["sector"] = sector
                                
                                holdings.append(holding)
                
                # If we found holdings, stop looking
                if holdings:
                    break
            
            logger.info(f"Found {len(holdings)} holdings for {fund_slug}")
            return holdings
            
        except requests.RequestException as e:
            logger.error(f"Error fetching VRO data for {fund_slug}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing VRO data for {fund_slug}: {e}")
            return []
    
    def get_fund_info(self, fund_slug: str) -> Optional[Dict]:
        """
        Get basic fund information.
        
        Args:
            fund_slug: URL-friendly fund name
            
        Returns:
            Dict with fund details
        """
        try:
            url = f"{self.FUND_URL}/{fund_slug}"
            response = self._session.get(url, timeout=15)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            info = {"slug": fund_slug}
            
            # Find fund name
            title = soup.find("h1")
            if title:
                info["name"] = title.text.strip()
            
            # Find key metrics
            metrics = soup.find_all("span", class_="metric-value")
            labels = soup.find_all("span", class_="metric-label")
            
            for label, metric in zip(labels, metrics):
                label_text = label.text.strip().lower()
                value = metric.text.strip()
                
                if "nav" in label_text:
                    info["nav"] = value
                elif "aum" in label_text:
                    info["aum"] = value
                elif "expense" in label_text:
                    info["expense_ratio"] = value
            
            return info
            
        except Exception as e:
            logger.error(f"Error fetching fund info for {fund_slug}: {e}")
            return None
    
    def search_funds(self, query: str) -> List[Dict]:
        """
        Search for mutual funds by name.
        
        Args:
            query: Search query
            
        Returns:
            List of matching funds
        """
        try:
            url = f"{self.FUND_URL}/search"
            params = {"q": query}
            response = self._session.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            results = []
            # Parse search results
            # (Simplified - actual implementation would need to inspect the page)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching funds: {e}")
            return []
    
    def _parse_percentage(self, text: str) -> float:
        """Parse percentage string to float."""
        if not text:
            return 0.0
        
        # Remove % and whitespace
        cleaned = text.replace("%", "").strip()
        
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def get_stock_in_funds(self, stock_name: str) -> Dict[str, List[Dict]]:
        """
        Find which funds hold a specific stock.
        
        This is useful for smart money analysis.
        
        Args:
            stock_name: Name of the stock to search for
            
        Returns:
            Dict mapping fund slugs to their holdings of this stock
        """
        # This would require searching each fund - expensive operation
        # For production, you'd want to cache this or use a database
        logger.warning("get_stock_in_funds is expensive - consider caching")
        return {}


# Global instance
value_research_scraper = ValueResearchScraper()
