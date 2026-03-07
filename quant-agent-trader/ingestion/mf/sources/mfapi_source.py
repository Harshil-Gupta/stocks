"""
MFAPI Data Source - Historical NAV data from MFAPI.in

MFAPI.in provides historical NAV data for Indian mutual funds.
API: https://api.mfapi.in/mf/{scheme_code}
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)


class MFAPIDataSource:
    """
    Fetch historical NAV data using MFAPI.in
    
    Free API providing historical NAV data for Indian mutual funds.
    """
    
    BASE_URL = "https://api.mfapi.in/mf/"
    
    def __init__(self, cache_minutes: int = 60):
        """
        Initialize MFAPI data source.
        
        Args:
            cache_minutes: How long to cache responses
        """
        self._cache: Dict[str, Dict] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_minutes = cache_minutes
    
    def _is_cache_valid(self, scheme_code: str) -> bool:
        """Check if cached data is valid."""
        if scheme_code not in self._cache:
            return False
        if scheme_code not in self._cache_time:
            return False
        elapsed = (datetime.now() - self._cache_time[scheme_code]).total_seconds() / 60
        return elapsed < self._cache_minutes
    
    def get_nav_history(
        self, 
        scheme_code: str,
        days: int = 90
    ) -> List[Dict]:
        """
        Get historical NAV data for a scheme.
        
        Args:
            scheme_code: AMFI scheme code (e.g., "119551")
            days: Number of days of history to fetch
            
        Returns:
            List of dicts with date and nav
        """
        if self._is_cache_valid(scheme_code) and scheme_code in self._cache:
            data = self._cache[scheme_code]
        else:
            try:
                url = f"{self.BASE_URL}{scheme_code}"
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    self._cache[scheme_code] = data
                    self._cache_time[scheme_code] = datetime.now()
                else:
                    logger.warning(f"MFAPI returned status {response.status_code} for {scheme_code}")
                    return []
                    
            except requests.RequestException as e:
                logger.error(f"MFAPI request failed for {scheme_code}: {e}")
                return []
        
        # Filter to requested number of days
        nav_data = data.get("data", [])
        if not nav_data:
            return []
        
        # Parse dates and filter
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%d-%m-%Y")
        filtered = [
            {"date": item["date"], "nav": float(item["nav"])}
            for item in nav_data
            if item["date"] >= cutoff
        ]
        
        return filtered
    
    def get_latest_nav(self, scheme_code: str) -> Optional[float]:
        """
        Get the latest NAV for a scheme.
        
        Args:
            scheme_code: AMFI scheme code
            
        Returns:
            Latest NAV or None
        """
        history = self.get_nav_history(scheme_code, days=7)
        if history:
            return history[0]["nav"]
        return None
    
    def calculate_returns(
        self,
        scheme_code: str,
        period_days: int = 30
    ) -> Optional[Dict]:
        """
        Calculate returns for a period.
        
        Args:
            scheme_code: AMFI scheme code
            period_days: Number of days for return calculation
            
        Returns:
            Dict with return percentages
        """
        history = self.get_nav_history(scheme_code, days=period_days + 10)
        
        if len(history) < 2:
            return None
        
        # Get oldest and newest NAV in period
        oldest = history[-1]["nav"]
        newest = history[0]["nav"]
        
        if oldest == 0:
            return None
        
        total_return = ((newest - oldest) / oldest) * 100
        
        return {
            "scheme_code": scheme_code,
            "period_days": period_days,
            "start_nav": oldest,
            "end_nav": newest,
            "return_pct": round(total_return, 2)
        }
    
    def compare_funds(
        self,
        scheme_codes: List[str],
        days: int = 30
    ) -> List[Dict]:
        """
        Compare returns across multiple funds.
        
        Args:
            scheme_codes: List of AMFI scheme codes
            days: Number of days for comparison
            
        Returns:
            List of dicts with fund returns
        """
        results = []
        
        for code in scheme_codes:
            returns = self.calculate_returns(code, days)
            if returns:
                results.append(returns)
        
        # Sort by return
        results.sort(key=lambda x: x["return_pct"], reverse=True)
        
        return results


# Global instance
mfapi_source = MFAPIDataSource()
