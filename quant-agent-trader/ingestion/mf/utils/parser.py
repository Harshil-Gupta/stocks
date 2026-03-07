"""
Parser Utilities for MF Data

Helper functions for parsing and normalizing MF data.
"""

import re
from datetime import datetime
from typing import Optional


def parse_percentage(text: str) -> float:
    """
    Parse percentage string to float.
    
    Args:
        text: String like "12.5%" or "12.5"
        
    Returns:
        Float value (e.g., 12.5)
    """
    if not text or not isinstance(text, str):
        return 0.0
    
    # Remove % and whitespace
    cleaned = text.replace("%", "").replace(",", "").strip()
    
    try:
        return float(cleaned)
    except (ValueError, AttributeError):
        return 0.0


def parse_date(date_str: str, format: str = "%d-%m-%Y") -> Optional[datetime]:
    """
    Parse date string to datetime.
    
    Args:
        date_str: Date string
        format: Expected format (default: dd-mm-yyyy)
        
    Returns:
        datetime object or None
    """
    if not date_str:
        return None
    
    try:
        return datetime.strptime(date_str, format)
    except ValueError:
        # Try common formats
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None


def normalize_symbol(symbol: str) -> str:
    """
    Normalize stock symbol to standard format.
    
    Args:
        symbol: Raw symbol string
        
    Returns:
        Normalized uppercase symbol
    """
    if not symbol:
        return ""
    
    # Remove common suffixes and clean
    symbol = symbol.upper().strip()
    symbol = re.sub(r'\..*', '', symbol)  # Remove .NS, .BO, etc.
    symbol = re.sub(r'[^A-Z0-9]', '', symbol)  # Keep only alphanumeric
    
    return symbol


def parse_market_cap(text: str) -> float:
    """
    Parse market cap string to numeric value (in crores).
    
    Args:
        text: String like "1,23,456 Cr" or "123456 Cr"
        
    Returns:
        Value in crores
    """
    if not text:
        return 0.0
    
    # Remove common suffixes
    cleaned = text.upper().replace("CR", "").replace("LAKH", "").replace(",", "").strip()
    
    try:
        value = float(cleaned)
        # Convert lakhs to crores if needed
        if "LAKH" in text.upper():
            value = value / 100
        return value
    except ValueError:
        return 0.0


def calculate_weight_change(old_weight: float, new_weight: float) -> float:
    """
    Calculate change in portfolio weight.
    
    Args:
        old_weight: Previous weight
        new_weight: Current weight
        
    Returns:
        Change in weight (percentage points)
    """
    return new_weight - old_weight


def is_turnover_high(holdings: list, threshold: float = 30.0) -> bool:
    """
    Check if fund has high turnover.
    
    Args:
        holdings: List of holdings
        threshold: Percentage threshold for high turnover
        
    Returns:
        True if turnover appears high
    """
    if not holdings:
        return False
    
    # Calculate sum of changes
    total_change = sum(abs(h.get("change", 0)) for h in holdings)
    
    return total_change > threshold
