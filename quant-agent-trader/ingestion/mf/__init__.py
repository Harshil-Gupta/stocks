"""
MF Data Package - Mutual Fund data ingestion and analysis

Structure:
- models.py: Data structures
- engine.py: Main data engine (aggregates all sources)
- sources/: Multiple data sources
    - amfi_source.py: AMFI NAV data
    - mfapi_source.py: MFAPI.in data
    - valueresearch_scraper.py: Value Research Online
- utils/: Helper functions
"""

from ingestion.mf.engine import MFDataEngine
from ingestion.mf.models import (
    MFHoldingsData,
    MFFundData,
    MFStockHolding,
    InstitutionalHolding,
)

__all__ = [
    "MFDataEngine",
    "MFHoldingsData", 
    "MFFundData",
    "MFStockHolding",
    "InstitutionalHolding",
]
