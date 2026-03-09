"""
Data Validators - Data quality checks for market data.

Usage:
    validator = DataValidator()
    issues = validator.validate(data)
    
    if issues:
        for issue in issues:
            print(f"{issue.severity}: {issue.description}")
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class IssueSeverity:
    """Severity levels for data issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class DataIssue:
    """Represents a data quality issue."""
    severity: str
    category: str
    description: str
    location: Optional[Dict[str, Any]] = None
    value: Optional[Any] = None


class DataValidator:
    """
    Validate market data quality.
    
    Checks:
    - Missing prices
    - Zero volume
    - Duplicate timestamps
    - Price spikes
    - Negative prices
    - Invalid OHLC relationships
    """
    
    def __init__(self):
        self.issues: List[DataIssue] = []
    
    def validate(
        self,
        data: pd.DataFrame,
        symbol: str = "unknown"
    ) -> List[DataIssue]:
        """
        Validate DataFrame for data quality issues.
        
        Args:
            data: Price data DataFrame
            symbol: Symbol name for logging
            
        Returns:
            List of issues found
        """
        self.issues = []
        self.symbol = symbol
        
        self._check_missing_values(data)
        self._check_duplicates(data)
        self._check_zero_volume(data)
        self._check_negative_prices(data)
        self._check_ohlc_relationships(data)
        self._check_price_spikes(data)
        self._check_gaps(data)
        self._check_stale_data(data)
        
        return self.issues
    
    def _check_missing_values(self, data: pd.DataFrame) -> None:
        """Check for missing values."""
        required_cols = ['close', 'open', 'high', 'low']
        
        for col in required_cols:
            if col not in data.columns:
                self.issues.append(DataIssue(
                    severity=IssueSeverity.ERROR,
                    category="missing_column",
                    description=f"Required column '{col}' is missing",
                    location={"column": col}
                ))
                continue
            
            missing = data[col].isna().sum()
            if missing > 0:
                pct = missing / len(data) * 100
                self.issues.append(DataIssue(
                    severity=IssueSeverity.WARNING if pct < 5 else IssueSeverity.ERROR,
                    category="missing_values",
                    description=f"{col} has {missing} missing values ({pct:.1f}%)",
                    location={"column": col, "count": missing}
                ))
    
    def _check_duplicates(self, data: pd.DataFrame) -> None:
        """Check for duplicate timestamps."""
        if not isinstance(data.index, pd.DatetimeIndex):
            return
        
        duplicates = data.index.duplicated().sum()
        if duplicates > 0:
            self.issues.append(DataIssue(
                severity=IssueSeverity.ERROR,
                category="duplicates",
                description=f"Found {duplicates} duplicate timestamps",
                location={"count": duplicates}
            ))
    
    def _check_zero_volume(self, data: pd.DataFrame) -> None:
        """Check for zero volume."""
        if 'volume' not in data.columns:
            return
        
        zero_vol = (data['volume'] == 0).sum()
        if zero_vol > 0:
            pct = zero_vol / len(data) * 100
            self.issues.append(DataIssue(
                severity=IssueSeverity.WARNING,
                category="zero_volume",
                description=f"Found {zero_vol} days with zero volume ({pct:.1f}%)",
                location={"count": zero_vol}
            ))
    
    def _check_negative_prices(self, data: pd.DataFrame) -> None:
        """Check for negative prices."""
        price_cols = ['close', 'open', 'high', 'low']
        
        for col in price_cols:
            if col not in data.columns:
                continue
            
            negative = (data[col] < 0).sum()
            if negative > 0:
                self.issues.append(DataIssue(
                    severity=IssueSeverity.ERROR,
                    category="negative_price",
                    description=f"Found {negative} negative values in {col}",
                    location={"column": col, "count": negative}
                ))
    
    def _check_ohlc_relationships(self, data: pd.DataFrame) -> None:
        """Check OHLC relationship validity."""
        required = ['open', 'high', 'low', 'close']
        if not all(c in data.columns for c in required):
            return
        
        issues_count = 0
        
        high_low = (data['high'] < data['low']).sum()
        if high_low > 0:
            issues_count += high_low
            self.issues.append(DataIssue(
                severity=IssueSeverity.ERROR,
                category="ohlc_invalid",
                description=f"Found {high_low} rows where high < low",
                location={"count": high_low}
            ))
        
        open_high = (data['open'] > data['high']).sum()
        if open_high > 0:
            issues_count += open_high
        
        open_low = (data['open'] < data['low']).sum()
        if open_low > 0:
            issues_count += open_low
        
        close_high = (data['close'] > data['high']).sum()
        if close_high > 0:
            issues_count += close_high
        
        close_low = (data['close'] < data['low']).sum()
        if close_low > 0:
            issues_count += close_low
        
        if issues_count > 0:
            self.issues.append(DataIssue(
                severity=IssueSeverity.ERROR,
                category="ohlc_invalid",
                description=f"Found {issues_count} OHLC relationship violations",
                location={"count": issues_count}
            ))
    
    def _check_price_spikes(self, data: pd.DataFrame) -> None:
        """Check for suspicious price changes."""
        if 'close' not in data.columns:
            return
        
        returns = data['close'].pct_change()
        
        threshold = 0.5  # 50% change
        spikes = (returns.abs() > threshold).sum()
        
        if spikes > 0:
            self.issues.append(DataIssue(
                severity=IssueSeverity.WARNING,
                category="price_spike",
                description=f"Found {spikes} days with >{threshold*100}% price change",
                location={"count": spikes, "threshold": threshold}
            ))
    
    def _check_gaps(self, data: pd.DataFrame) -> None:
        """Check for large gaps in data."""
        if not isinstance(data.index, pd.DatetimeIndex):
            return
        
        if len(data) < 2:
            return
        
        time_diffs = data.index.to_series().diff()
        
        max_gap = time_diffs.max()
        
        if max_gap.days > 7:
            self.issues.append(DataIssue(
                severity=IssueSeverity.WARNING,
                category="data_gap",
                description=f"Found gap of {max_gap.days} days in data",
                location={"max_gap_days": max_gap.days}
            ))
    
    def _check_stale_data(self, data: pd.DataFrame) -> None:
        """Check if data is stale."""
        if not isinstance(data.index, pd.DatetimeIndex):
            return
        
        latest_date = data.index.max()
        days_old = (datetime.now() - latest_date).days
        
        if days_old > 7:
            severity = IssueSeverity.ERROR if days_old > 30 else IssueSeverity.WARNING
            self.issues.append(DataIssue(
                severity=severity,
                category="stale_data",
                description=f"Data is {days_old} days old",
                location={"days_old": days_old}
            ))
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        errors = [i for i in self.issues if i.severity == IssueSeverity.ERROR]
        warnings = [i for i in self.issues if i.severity == IssueSeverity.WARNING]
        
        return {
            "total_issues": len(self.issues),
            "errors": len(errors),
            "warnings": len(warnings),
            "is_valid": len(errors) == 0
        }


class DataQualityMonitor:
    """
    Monitor data quality over time.
    
    Usage:
        monitor = DataQualityMonitor()
        
        # After each data load
        monitor.check(data, symbol="TCS")
        
        # Get report
        report = monitor.get_report()
    """
    
    def __init__(self):
        self.history: List[Dict] = []
    
    def check(
        self,
        data: pd.DataFrame,
        symbol: str,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Check data quality and record results."""
        validator = DataValidator()
        issues = validator.validate(data, symbol)
        
        result = {
            "symbol": symbol,
            "timestamp": timestamp or datetime.now(),
            "issues_count": len(issues),
            "errors": len([i for i in issues if i.severity == IssueSeverity.ERROR]),
            "warnings": len([i for i in issues if i.severity == IssueSeverity.WARNING]),
            "is_valid": len([i for i in issues if i.severity == IssueSeverity.ERROR]) == 0,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "description": i.description
                }
                for i in issues
            ]
        }
        
        self.history.append(result)
        
        return result
    
    def get_report(self) -> Dict[str, Any]:
        """Get quality report."""
        if not self.history:
            return {}
        
        total_checks = len(self.history)
        valid_checks = sum(1 for r in self.history if r["is_valid"])
        
        return {
            "total_checks": total_checks,
            "valid_checks": valid_checks,
            "success_rate": valid_checks / total_checks if total_checks > 0 else 0,
            "history": self.history
        }
    
    def get_symbol_stats(self, symbol: str) -> Dict[str, Any]:
        """Get stats for a specific symbol."""
        symbol_history = [r for r in self.history if r["symbol"] == symbol]
        
        if not symbol_history:
            return {}
        
        return {
            "symbol": symbol,
            "checks": len(symbol_history),
            "avg_issues": sum(r["issues_count"] for r in symbol_history) / len(symbol_history),
            "success_rate": sum(1 for r in symbol_history if r["is_valid"]) / len(symbol_history)
        }


class MarketDataValidator:
    """
    Specialized validator for market data sources.
    """
    
    def validate_nse(self, data: pd.DataFrame) -> List[DataIssue]:
        """Validate NSE India data."""
        validator = DataValidator()
        return validator.validate(data, "NSE")
    
    def validate_yahoo(self, data: pd.DataFrame) -> List[DataIssue]:
        """Validate Yahoo Finance data."""
        validator = DataValidator()
        issues = validator.validate(data, "Yahoo")
        
        if 'adj_close' in data.columns and 'close' in data.columns:
            diff = (data['adj_close'] - data['close']).abs().sum()
            if diff > 0:
                issues.append(DataIssue(
                    severity=IssueSeverity.INFO,
                    category="adjusted_close",
                    description="Data has adjusted close column",
                    location={"diff_sum": float(diff)}
                ))
        
        return issues
    
    def validate_polygon(self, data: pd.DataFrame) -> List[DataIssue]:
        """Validate Polygon.io data."""
        validator = DataValidator()
        issues = validator.validate(data, "Polygon")
        
        required = ['T', 'O', 'H', 'L', 'C', 'V']
        missing = [c for c in required if c not in data.columns]
        
        if missing:
            issues.append(DataIssue(
                severity=IssueSeverity.WARNING,
                category="column_mapping",
                description=f"Polygon data missing columns: {missing}",
                location={"missing": missing}
            ))
        
        return issues
