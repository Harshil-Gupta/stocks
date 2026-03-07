"""
Data Module - Market data ingestion and management.

This module provides:
- DataIngestionEngine: Main engine for fetching market data
- MockDataSource: Mock data source for testing
- IndiaDataSource: India-specific market data source
- india_data_engine: Pre-configured India data engine
- mf_data_engine: Mutual fund data engine
"""

from data.ingestion.market_data import DataIngestionEngine, MockDataSource
from data.ingestion.india_data import IndiaDataSource, india_data_engine, NSE_SYMBOLS
from data.ingestion.mf_data import mf_data_engine

__all__ = [
    "DataIngestionEngine",
    "MockDataSource",
    "IndiaDataSource",
    "india_data_engine",
    "mf_data_engine",
    "NSE_SYMBOLS",
]
