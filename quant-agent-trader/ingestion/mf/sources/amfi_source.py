"""
AMFI Data Source - Official NAV data from Association of Mutual Funds in India

AMFI publishes daily NAV data at:
https://www.amfiindia.com/spages/NAVAll.txt

This is the official source for mutual fund NAVs in India.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class AMFIDataSource:
    """
    Fetch daily NAV data from AMFI (Association of Mutual Funds in India).
    
    Official NAV data source - reliable and comprehensive.
    """
    
    NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
    
    # Common Indian equity mutual funds scheme codes
    POPULAR_SCHEMES = {
        "PPFCF": "119551",  # Parag Parikh Flexi Cap
        "SBIBS": "101917",  # SBI Blue Chip
        "HDFCBS": "103356",  # HDFC Top 100
        "ICICIBS": "100080",  # ICICI Blue Chip
        "UTIB": "100046",  # UTI Flexi Cap
    }
    
    # Reverse mapping: scheme code -> name
    SCHEME_CODES = {
        "119551": "Parag Parikh Flexi Cap Fund",
        "101917": "SBI Blue Chip Fund",
        "103356": "HDFC Top 100 Fund",
        "100080": "ICICI Blue Chip Fund",
        "100046": "UTI Flexi Cap Fund",
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
    
    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid."""
        if self._cache is None or self._cache_time is None:
            return False
        elapsed = (datetime.now() - self._cache_time).total_seconds() / 60
        return elapsed < self._cache_minutes
    
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
            # AMFI uses semicolon-separated format
            df = pd.read_csv(
                self.NAV_URL, 
                sep=";", 
                encoding='latin-1',
                on_bad_lines='skip'
            )
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Validate required columns exist
            required_cols = ['Scheme Type', 'Scheme Code', 'Net Asset Value']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.warning(f"AMFI data missing columns: {missing_cols}. Available: {list(df.columns)}")
                # Try to proceed with available columns
                if 'Net Asset Value' not in df.columns:
                    raise ValueError(f"Required column 'Net Asset Value' not found in AMFI data")
            
            # Filter for equity schemes only (safe with try-except)
            if 'Scheme Type' in df.columns:
                try:
                    df = df[df['Scheme Type'].str.contains('Open', case=False, na=False)]
                    df = df[df['Scheme Type'].str.contains('Growth|ELSS', case=False, na=False)]
                except Exception as e:
                    logger.warning(f"Error filtering scheme type: {e}")
            
            # Store in cache
            self._cache = df
            self._cache_time = datetime.now()
            
            logger.info(f"Fetched {len(df)} mutual fund NAVs from AMFI")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching AMFI NAV data: {e}")
            return pd.DataFrame() if self._cache is None else self._cache
    
    def get_scheme_nav(self, scheme_code: str) -> Optional[float]:
        """
        Get NAV for a specific scheme code.
        
        Args:
            scheme_code: AMFI scheme code (e.g., "119551")
            
        Returns:
            Latest NAV or None if not found
        """
        df = self.fetch_nav_data()
        
        if df.empty:
            return None
        
        # Match scheme code
        scheme = df[df['Scheme Code'].astype(str) == str(scheme_code)]
        
        if scheme.empty:
            # Try matching by name
            scheme = df[df['Scheme Name'].str.contains(scheme_code, case=False, na=False)]
        
        if not scheme.empty:
            try:
                nav = float(scheme.iloc[0]['Net Asset Value'])
                return nav
            except (ValueError, KeyError):
                return None
        
        return None
    
    def get_scheme_by_name(self, name: str) -> Optional[Dict]:
        """
        Search for a scheme by name.
        
        Args:
            name: Partial or full scheme name
            
        Returns:
            Dict with scheme details or None
        """
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
        """
        Get top N funds by category.
        
        Args:
            category: Category name (e.g., "Large Cap", "Mid Cap")
            n: Number of funds to return
            
        Returns:
            List of fund dictionaries
        """
        df = self.fetch_nav_data()
        
        if df.empty:
            return []
        
        # Filter by category
        if category:
            df = df[df['Scheme Name'].str.contains(category, case=False, na=False)]
        
        # Sort by NAV (just return first n)
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


# Global instance
amfi_source = AMFIDataSource()
