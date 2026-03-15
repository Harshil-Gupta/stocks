"""
Market Data Caching Layer.

Features:
- Local Parquet cache storage
- Cache expiry (TTL)
- Incremental updates (fetch only new data)
- API fallback if cache miss
- Thread-safe operations

Usage:
    from data.cache import MarketDataCache

    cache = MarketDataCache(cache_dir="data/cache")

    # Get data (from cache or API)
    data = cache.get("RELIANCE", fetch_func=lambda: api.fetch("RELIANCE"))

    # Check cache status
    cache.info("RELIANCE")

    # Clear cache
    cache.clear("RELIANCE")
"""

import os
import shutil
import threading
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheMetadata:
    """Metadata for cached data."""

    symbol: str
    last_updated: datetime
    start_date: str
    end_date: str
    row_count: int
    source: str


class MarketDataCache:
    """
    Local parquet cache for market data.

    Features:
    - Parquet format for fast I/O and compression
    - TTL-based expiry
    - Incremental updates (only fetch missing dates)
    - Thread-safe operations
    """

    def __init__(
        self,
        cache_dir: str = "data/cache",
        default_ttl_hours: int = 24,
        enable_incremental: bool = True,
    ):
        self.cache_dir = Path(cache_dir)
        self.default_ttl_hours = default_ttl_hours
        self.enable_incremental = enable_incremental
        self._lock = threading.Lock()

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_file = self.cache_dir / "cache_metadata.json"

        logger.info(f"Market data cache initialized at: {self.cache_dir}")

    def _get_cache_path(self, symbol: str) -> Path:
        """Get path for cached symbol file."""
        safe_symbol = symbol.replace("/", "_").replace("\\", "_")
        return self.cache_dir / f"{safe_symbol}.parquet"

    def _get_metadata_path(self, symbol: str) -> Path:
        """Get path for symbol metadata file."""
        safe_symbol = symbol.replace("/", "_").replace("\\", "_")
        return self.cache_dir / f"{safe_symbol}_meta.json"

    def exists(self, symbol: str) -> bool:
        """Check if data is cached."""
        return self._get_cache_path(symbol).exists()

    def is_expired(self, symbol: str, ttl_hours: Optional[int] = None) -> bool:
        """Check if cached data is expired."""
        if not self.exists(symbol):
            return True

        meta_path = self._get_metadata_path(symbol)
        if not meta_path.exists():
            return True

        try:
            import json

            with open(meta_path, "r") as f:
                meta = json.load(f)

            last_updated = datetime.fromisoformat(meta["last_updated"])
            ttl = ttl_hours or self.default_ttl_hours

            return (datetime.now() - last_updated).total_seconds() > ttl * 3600
        except Exception:
            return True

    def get(
        self,
        symbol: str,
        fetch_func: Optional[Callable[[], pd.DataFrame]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ttl_hours: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Get data from cache or fetch from API.

        Args:
            symbol: Stock symbol
            fetch_func: Function to fetch data if not cached
            start_date: Start date for data (for incremental updates)
            end_date: End date for data
            ttl_hours: Cache TTL in hours

        Returns:
            DataFrame with market data
        """
        with self._lock:
            cache_path = self._get_cache_path(symbol)

            if self.exists(symbol) and not self.is_expired(symbol, ttl_hours):
                cached = self._load_from_cache(symbol)

                if cached is not None and self.enable_incremental:
                    return self._update_incremental(
                        symbol, cached, fetch_func, start_date, end_date
                    )

                return cached

            if fetch_func is None:
                logger.warning(f"No cache and no fetch_func for {symbol}")
                return None

            logger.info(f"Fetching fresh data for {symbol}")
            data = fetch_func()

            if data is not None and not data.empty:
                self._save_to_cache(symbol, data, start_date, end_date)

            return data

    def _load_from_cache(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load data from cache."""
        try:
            cache_path = self._get_cache_path(symbol)
            df = pd.read_parquet(cache_path)
            logger.debug(f"Cache hit for {symbol}: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Failed to load cache for {symbol}: {e}")
            return None

    def _save_to_cache(
        self,
        symbol: str,
        data: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> None:
        """Save data to cache."""
        try:
            cache_path = self._get_cache_path(symbol)

            if isinstance(data.index, pd.DatetimeIndex):
                data = data.reset_index()
            elif "date" not in data.columns and "Date" not in data.columns:
                data = data.reset_index()

            data.to_parquet(cache_path, index=False)

            end = end_date or (
                data.iloc[-1]["Date"].isoformat()
                if "Date" in data.columns
                else str(data.index[-1])
            )
            start = start_date or (
                data.iloc[0]["Date"].isoformat()
                if "Date" in data.columns
                else str(data.index[0])
            )

            self._save_metadata(symbol, start, end, len(data))

            logger.info(f"Cached {symbol}: {len(data)} rows, dates: {start} to {end}")
        except Exception as e:
            logger.error(f"Failed to save cache for {symbol}: {e}")

    def _update_incremental(
        self,
        symbol: str,
        cached_data: pd.DataFrame,
        fetch_func: Optional[Callable],
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.DataFrame:
        """Update cache with incremental data."""
        if fetch_func is None:
            return cached_data

        try:
            cached_dates = set()
            date_cols = [c for c in cached_data.columns if "date" in c.lower()]
            if date_cols:
                date_col = date_cols[0]
                cached_dates = set(pd.to_datetime(cached_data[date_col]).dt.date)

            new_data = fetch_func()

            if new_data is None or new_data.empty:
                return cached_data

            new_dates = set()
            date_cols = [c for c in new_data.columns if "date" in c.lower()]
            if date_cols:
                date_col = date_cols[0]
                new_dates = set(pd.to_datetime(new_data[date_col]).dt.date)

            missing_dates = new_dates - cached_dates

            if missing_dates:
                new_rows = new_data.copy()
                date_cols = [c for c in new_data.columns if "date" in c.lower()]
                if date_cols:
                    date_col = date_cols[0]
                    new_rows = new_data[
                        pd.to_datetime(new_data[date_col]).dt.date.isin(missing_dates)
                    ]

                if not new_rows.empty:
                    updated = pd.concat([cached_data, new_rows], ignore_index=True)

                    if "Date" in updated.columns or "date" in [
                        c.lower() for c in updated.columns
                    ]:
                        date_col = "Date" if "Date" in updated.columns else "date"
                        updated = updated.sort_values(date_col)

                    self._save_to_cache(symbol, updated, None, None)
                    logger.info(
                        f"Updated cache for {symbol}: +{len(new_rows)} new rows"
                    )
                    return updated

            return cached_data
        except Exception as e:
            logger.warning(f"Incremental update failed for {symbol}: {e}")
            return cached_data

    def _save_metadata(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        row_count: int,
    ) -> None:
        """Save cache metadata."""
        import json

        meta = {
            "symbol": symbol,
            "last_updated": datetime.now().isoformat(),
            "start_date": start_date,
            "end_date": end_date,
            "row_count": row_count,
            "source": "api",
        }

        meta_path = self._get_metadata_path(symbol)
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    def info(self, symbol: str) -> Optional[CacheMetadata]:
        """Get cache information for symbol."""
        if not self.exists(symbol):
            return None

        import json

        meta_path = self._get_metadata_path(symbol)

        if meta_path.exists():
            try:
                with open(meta_path, "r") as f:
                    meta = json.load(f)

                return CacheMetadata(
                    symbol=meta["symbol"],
                    last_updated=datetime.fromisoformat(meta["last_updated"]),
                    start_date=meta["start_date"],
                    end_date=meta["end_date"],
                    row_count=meta["row_count"],
                    source=meta.get("source", "unknown"),
                )
            except Exception:
                pass

        cache_path = self._get_cache_path(symbol)
        df = pd.read_parquet(cache_path)

        return CacheMetadata(
            symbol=symbol,
            last_updated=datetime.fromtimestamp(cache_path.stat().st_mtime),
            start_date="unknown",
            end_date="unknown",
            row_count=len(df),
            source="unknown",
        )

    def list_cached(self) -> List[str]:
        """List all cached symbols."""
        return [f.stem for f in self.cache_dir.glob("*.parquet")]

    def clear(self, symbol: Optional[str] = None) -> None:
        """Clear cache for symbol or all."""
        with self._lock:
            if symbol:
                cache_path = self._get_cache_path(symbol)
                meta_path = self._get_metadata_path(symbol)

                if cache_path.exists():
                    cache_path.unlink()
                if meta_path.exists():
                    meta_path.unlink()

                logger.info(f"Cleared cache for {symbol}")
            else:
                for f in self.cache_dir.glob("*.parquet"):
                    f.unlink()
                for f in self.cache_dir.glob("*_meta.json"):
                    f.unlink()

                logger.info("Cleared all cache")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cached = self.list_cached()
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.parquet"))

        return {
            "cached_symbols": len(cached),
            "total_size_mb": total_size / (1024 * 1024),
            "symbols": cached,
        }


class DataCacheManager:
    """
    Manager for multiple data caches.
    """

    def __init__(self, cache_dir: str = "data/cache"):
        self.market_cache = MarketDataCache(cache_dir)
        self.feature_cache = MarketDataCache(
            f"{cache_dir}/features", default_ttl_hours=168
        )

    def get_market_data(
        self,
        symbol: str,
        fetch_func: Callable,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """Get market data with caching."""
        return self.market_cache.get(symbol, fetch_func, start_date, end_date)

    def get_features(
        self,
        symbol: str,
        fetch_func: Callable,
    ) -> Optional[pd.DataFrame]:
        """Get feature data with caching."""
        return self.feature_cache.get(symbol, fetch_func, ttl_hours=168)


__all__ = [
    "MarketDataCache",
    "DataCacheManager",
    "CacheMetadata",
]
