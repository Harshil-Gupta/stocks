"""
Data Ingestion Module - Market data fetchers and loaders.
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
