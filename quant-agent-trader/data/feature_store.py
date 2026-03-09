"""
Feature Store - Persists agent outputs for ML training.

Stores agent features per symbol per timestamp in Parquet format.

Schema:
    timestamp, symbol
    # agent features (rsi_score, macd_score, etc.)
    # market features (close, volume, volatility, vix)
    # labels (future_return_5d, future_return_10d)
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os
import glob
import logging
from dataclasses import dataclass

from signals.signal_schema import AgentSignal
from signals.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)


@dataclass
class FeatureStoreConfig:
    """Configuration for feature store."""
    base_path: str = "data/feature_store"
    partition_by: str = "month"  # month, day, symbol
    compression: str = "snappy"


class FeatureStore:
    """
    Feature store for persisting agent and market features.
    
    Stores features in Parquet format partitioned by time.
    
    Example:
        data/feature_store/
            features_2024_01.parquet
            features_2024_02.parquet
            ...
    """
    
    AGENT_FEATURE_NAMES = [
        "rsi_score", "macd_score", "momentum_score", "mean_reversion_score",
        "stat_arb_score", "pairs_trading_score", "sentiment_score", "macro_score",
        "bollinger_score", "atr_score", "volume_score", "trend_score",
        "breakout_score", "vwap_score", "mfi_score", "obv_score",
        "adx_score", "cci_score", "williams_r_score", "ichimoku_score",
        "valuation_score", "dividend_score", "growth_score", "earnings_score",
        "insider_score", "news_score", "analyst_score", "social_score",
        "interest_rate_score", "inflation_score", "gdp_score", "currency_score",
        "sector_rotation_score", "commodity_score", "options_flow_score",
        "put_call_ratio_score", "drawdown_score", "correlation_risk_score",
        "tail_risk_score", "volatility_regime_score"
    ]
    
    MARKET_FEATURE_NAMES = [
        "close", "open", "high", "low", "volume",
        "volatility", "vix", "returns_1d", "returns_5d", "returns_20d",
        "atr", "rsi", "macd", "sma_20", "sma_50", "sma_200"
    ]
    
    LABEL_NAMES = [
        "future_return_5d", "future_return_10d", "future_return_20d",
        "target_binary_5d", "target_binary_10d", "target_binary_20d"
    ]
    
    def __init__(self, config: Optional[FeatureStoreConfig] = None):
        self.config = config or FeatureStoreConfig()
        self.feature_extractor = FeatureExtractor()
        os.makedirs(self.config.base_path, exist_ok=True)
    
    def _get_partition_key(self, date: datetime) -> str:
        """Get partition key based on config."""
        if self.config.partition_by == "month":
            return f"features_{date.year}_{date.month:02d}.parquet"
        elif self.config.partition_by == "day":
            return f"features_{date.year}_{date.month:02d}_{date.day:02d}.parquet"
        else:
            return "features.parquet"
    
    def _get_file_path(self, date: datetime) -> str:
        """Get full file path for date."""
        return os.path.join(self.config.base_path, self._get_partition_key(date))
    
    def write_features(
        self,
        timestamp: datetime,
        symbol: str,
        agent_signals: List[AgentSignal],
        market_features: Optional[Dict[str, float]] = None,
        future_returns: Optional[Dict[str, float]] = None
    ) -> None:
        """
        Write a single feature row to the store.
        
        Args:
            timestamp: Feature timestamp
            symbol: Stock symbol
            agent_signals: List of agent signals
            market_features: Market features (price, volume, etc.)
            future_returns: Future returns for labels
        """
        row = {
            "timestamp": timestamp,
            "symbol": symbol
        }
        
        agent_features = self.feature_extractor.signals_to_features(agent_signals)
        
        for key, value in agent_features.items():
            if key not in ["date", "symbol"]:
                row[key] = value
        
        if market_features:
            row.update(market_features)
        
        if future_returns:
            row["future_return_5d"] = future_returns.get("5d", np.nan)
            row["future_return_10d"] = future_returns.get("10d", np.nan)
            row["future_return_20d"] = future_returns.get("20d", np.nan)
            
            row["target_binary_5d"] = 1 if future_returns.get("5d", 0) > 0 else 0
            row["target_binary_10d"] = 1 if future_returns.get("10d", 0) > 0 else 0
            row["target_binary_20d"] = 1 if future_returns.get("20d", 0) > 0 else 0
        
        df_new = pd.DataFrame([row])
        
        filepath = self._get_file_path(timestamp)
        
        if os.path.exists(filepath):
            df_existing = pd.read_parquet(filepath)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_parquet(filepath, index=False, compression=self.config.compression)
        else:
            df_new.to_parquet(filepath, index=False, compression=self.config.compression)
    
    def write_batch(self, rows: List[Dict[str, Any]]) -> None:
        """
        Write multiple feature rows at once.
        
        Args:
            rows: List of feature dictionaries
        """
        if not rows:
            return
        
        df = pd.DataFrame(rows)
        
        dates = pd.to_datetime(df["timestamp"])
        unique_dates = dates.dt.to_period("M").unique()
        
        for period in unique_dates:
            mask = dates.dt.to_period("M") == period
            period_df = df[mask]
            
            year = period.year
            month = period.month
            filename = f"features_{year}_{month:02d}.parquet"
            filepath = os.path.join(self.config.base_path, filename)
            
            if os.path.exists(filepath):
                df_existing = pd.read_parquet(filepath)
                df_combined = pd.concat([df_existing, period_df], ignore_index=True)
                df_combined.to_parquet(filepath, index=False, compression=self.config.compression)
            else:
                period_df.to_parquet(filepath, index=False, compression=self.config.compression)
        
        logger.info(f"Wrote {len(df)} feature rows")
    
    def read_features(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Read features from the store.
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            symbols: List of symbols to filter
            
        Returns:
            DataFrame of features
        """
        pattern = os.path.join(self.config.base_path, "features_*.parquet")
        files = glob.glob(pattern)
        
        if not files:
            logger.warning("No feature files found")
            return pd.DataFrame()
        
        dfs = []
        for filepath in files:
            df = pd.read_parquet(filepath)
            dfs.append(df)
        
        df = pd.concat(dfs, ignore_index=True)
        
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        if start_date:
            df = df[df["timestamp"] >= start_date]
        if end_date:
            df = df[df["timestamp"] <= end_date]
        if symbols:
            df = df[df["symbol"].isin(symbols)]
        
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        return df
    
    def get_latest_features(self, symbol: str, n: int = 1) -> pd.DataFrame:
        """Get latest n features for a symbol."""
        all_features = self.read_features()
        
        if all_features.empty:
            return pd.DataFrame()
        
        symbol_features = all_features[all_features["symbol"] == symbol]
        
        return symbol_features.tail(n)
    
    def get_feature_names(self) -> List[str]:
        """Get list of all feature names in the store."""
        pattern = os.path.join(self.config.base_path, "features_*.parquet")
        files = glob.glob(pattern)
        
        if not files:
            return []
        
        df = pd.read_parquet(files[0])
        return [c for c in df.columns if c not in ["timestamp", "symbol"]]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the feature store."""
        pattern = os.path.join(self.config.base_path, "features_*.parquet")
        files = glob.glob(pattern)
        
        if not files:
            return {"files": 0, "rows": 0, "symbols": 0}
        
        total_rows = 0
        all_symbols = set()
        
        for filepath in files:
            df = pd.read_parquet(filepath)
            total_rows += len(df)
            all_symbols.update(df["symbol"].unique())
        
        return {
            "files": len(files),
            "rows": total_rows,
            "symbols": len(all_symbols),
            "date_range": self._get_date_range()
        }
    
    def _get_date_range(self) -> Optional[Dict[str, str]]:
        """Get date range of stored features."""
        pattern = os.path.join(self.config.base_path, "features_*.parquet")
        files = glob.glob(pattern)
        
        if not files:
            return None
        
        first_df = pd.read_parquet(files[0])
        last_df = pd.read_parquet(files[-1])
        
        return {
            "start": str(first_df["timestamp"].min()),
            "end": str(last_df["timestamp"].max())
        }


class CrossAssetFeatureStore:
    """
    Feature store for cross-asset signals.
    
    Adds macro signals like:
    - USDINR trend
    - Bond yields
    - NIFTY breadth
    - Sector rotation
    - FII/DII flows
    """
    
    def __init__(self, base_path: str = "data/feature_store/cross_asset"):
        self.base_path = base_path
        os.makedirs(base_path, exist_okasy)
    
    def write_cross_asset_features(
        self,
        timestamp: datetime,
        features: Dict[str, float]
    ) -> None:
        """Write cross-asset features."""
        row = {"timestamp": timestamp, **features}
        
        filepath = os.path.join(self.base_path, "cross_asset.parquet")
        
        df_new = pd.DataFrame([row])
        
        if os.path.exists(filepath):
            df_existing = pd.read_parquet(filepath)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_parquet(filepath, index=False)
        else:
            df_new.to_parquet(filepath, index=False)
    
    def get_cross_asset_features(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Get cross-asset features."""
        filepath = os.path.join(self.base_path, "cross_asset.parquet")
        
        if not os.path.exists(filepath):
            return pd.DataFrame()
        
        df = pd.read_parquet(filepath)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        if start_date:
            df = df[df["timestamp"] >= start_date]
        if end_date:
            df = df[df["timestamp"] <= end_date]
        
        return df.sort_values("timestamp")
