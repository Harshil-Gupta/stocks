"""
Data Module - Market data ingestion and management.

This module provides:
- DataIngestionEngine: Main engine for fetching market data
- MockDataSource: Mock data source for testing
- IndiaDataSource: India-specific market data source
- MarketDataCache: Local parquet caching layer
- mf_data_engine: Mutual fund data engine
- unified_data_service: Unified interface to all data sources
"""

from data.ingestion.market_data import DataIngestionEngine, MockDataSource
from data.ingestion.india_data import IndiaDataSource, india_data_engine, NSE_SYMBOLS
from data.ingestion.mf_data import mf_data_engine
from data.services import (
    unified_data_service,
    UnifiedDataService,
    get_stock_data,
    get_market_dashboard,
    get_institutional_holdings,
    get_macro,
    get_regime,
    get_amfi_stock_holdings,
    get_amfi_top_holders,
    get_amfi_sector_holdings,
    DataServiceRegistry,
)
from data.cache import MarketDataCache, DataCacheManager, CacheMetadata

__all__ = [
    "DataIngestionEngine",
    "MockDataSource",
    "IndiaDataSource",
    "india_data_engine",
    "mf_data_engine",
    "NSE_SYMBOLS",
    # Services
    "unified_data_service",
    "UnifiedDataService",
    "get_stock_data",
    "get_market_dashboard",
    "get_institutional_holdings",
    "get_macro",
    "get_regime",
    "get_amfi_stock_holdings",
    "get_amfi_top_holders",
    "get_amfi_sector_holdings",
    "DataServiceRegistry",
    # Cache
    "MarketDataCache",
    "DataCacheManager",
    "CacheMetadata",
]
