"""
Input validation utilities for the trading system.
"""

import re
from typing import Optional


def validate_stock_symbol(symbol: str) -> bool:
    """
    Validate a stock symbol.

    Args:
        symbol: Stock symbol to validate

    Returns:
        True if valid, False otherwise
    """
    if not symbol or not isinstance(symbol, str):
        return False

    symbol = symbol.strip().upper()

    # Indian stock symbols: 1-10 uppercase letters
    if re.match(r"^[A-Z]{1,10}$", symbol):
        return True

    return False


def validate_date_range(start_date: str, end_date: str) -> tuple[bool, Optional[str]]:
    """
    Validate date range for backtesting.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Tuple of (is_valid, error_message)
    """
    from datetime import datetime

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if start >= end:
            return False, "Start date must be before end date"

        # Max 10 years of historical data
        if (end - start).days > 3650:
            return False, "Date range cannot exceed 10 years"

        return True, None

    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD"


def validate_capital(capital: float) -> tuple[bool, Optional[str]]:
    """
    Validate trading capital.

    Args:
        capital: Capital amount

    Returns:
        Tuple of (is_valid, error_message)
    """
    if capital <= 0:
        return False, "Capital must be positive"

    if capital < 10000:
        return False, "Minimum capital is Rs. 10,000"

    if capital > 100000000:
        return False, "Maximum capital is Rs. 100,000,000"

    return True, None


def sanitize_symbol(symbol: str) -> str:
    """
    Sanitize and normalize a stock symbol.

    Args:
        symbol: Raw symbol input

    Returns:
        Sanitized uppercase symbol
    """
    if not symbol:
        return ""

    # Remove common suffixes
    symbol = symbol.strip().upper()
    symbol = re.sub(r"\.(NS|BO|NSE|BSE)$", "", symbol)

    # Keep only alphanumeric
    symbol = re.sub(r"[^A-Z0-9]", "", symbol)

    return symbol[:10]  # Max 10 chars
