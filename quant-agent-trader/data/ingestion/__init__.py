"""
Data Ingestion Module - Market data fetchers and loaders.
"""

from data.ingestion.market_data import DataIngestionEngine, MockDataSource
from data.ingestion.india_data import IndiaDataSource, india_data_engine, NSE_SYMBOLS
from data.ingestion.mf_data import mf_data_engine
from data.ingestion.nse_api_client import (
    nse_api,
    NSEIndiaAPI,
    get_quote,
    get_fiidii,
    get_market_status,
    get_nifty50,
    get_preopen_data,
)
from data.ingestion.screener_data import (
    screener_data,
    ScreenerDataExtractor,
    get_financials,
    get_ratios,
    get_shareholding,
)
from data.ingestion.rbi_macro import (
    rbi_macro,
    RBIMacroData,
    get_macro_snapshot,
    get_policy_rates,
    get_regime,
)
from ingestion.mf.sources.amfi_source import amfi_source, AMFIDataSource

__all__ = [
    # Market data
    "DataIngestionEngine",
    "MockDataSource",
    "IndiaDataSource",
    "india_data_engine",
    "NSE_SYMBOLS",
    # NSE API
    "nse_api",
    "NSEIndiaAPI",
    "get_quote",
    "get_fiidii",
    "get_market_status",
    "get_nifty50",
    "get_preopen_data",
    # Screener data
    "screener_data",
    "ScreenerDataExtractor",
    "get_financials",
    "get_ratios",
    "get_shareholding",
    # RBI Macro
    "rbi_macro",
    "RBIMacroData",
    "get_macro_snapshot",
    "get_policy_rates",
    "get_regime",
    # MF Data
    "mf_data_engine",
    # AMFI Source
    "amfi_source",
    "AMFIDataSource",
]
