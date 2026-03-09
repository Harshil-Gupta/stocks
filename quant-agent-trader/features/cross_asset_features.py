"""
Cross-Asset Features - Macro signals that improve prediction power.

Adds features like:
- USDINR trend
- Bond yields
- NIFTY breadth
- Sector rotation
- FII/DII flows
- India VIX
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class CrossAssetFeatures:
    """
    Generates cross-asset features for Indian markets.
    
    These macro signals often move Indian equities before
    individual indicators react.
    """
    
    def __init__(self):
        self.feature_names = [
            "usdinr",
            "bond_yield_10y",
            "nifty_breadth",
            "nifty_fii_flow",
            "nifty_dii_flow",
            "india_vix",
            "sector_rotation",
            "gold_price",
            "crude_price",
            "us_market_trend",
            "global_risk"
        ]
    
    def compute_features(
        self,
        nifty_data: Optional[pd.DataFrame] = None,
        usdinr_data: Optional[pd.DataFrame] = None,
        bond_data: Optional[pd.DataFrame] = None,
        vix_data: Optional[pd.DataFrame] = None,
        fii_data: Optional[pd.DataFrame] = None,
        dii_data: Optional[pd.DataFrame] = None,
        gold_data: Optional[pd.DataFrame] = None,
        crude_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """
        Compute all cross-asset features.
        
        Args:
            nifty_data: NIFTY 50 price data
            usdinr_data: USD/INR exchange rate
            bond_data: 10-year bond yield
            vix_data: India VIX
            fii_data: FII flow data
            dii_data: DII flow data
            gold_data: Gold price
            crude_data: Crude oil price
            
        Returns:
            Dictionary of feature_name -> value
        """
        features = {}
        
        if nifty_data is not None and len(nifty_data) > 20:
            features.update(self._compute_breadth(nifty_data))
        
        if usdinr_data is not None and len(usdinr_data) > 5:
            features["usdinr"] = self._compute_trend(usdinr_data)
        
        if bond_data is not None and len(bond_data) > 5:
            features["bond_yield_10y"] = self._compute_trend(bond_data)
        
        if vix_data is not None and len(vix_data) > 5:
            features["india_vix"] = self._compute_level(vix_data)
        
        if fii_data is not None and len(fii_data) > 0:
            features["nifty_fii_flow"] = self._compute_flow(fii_data)
        
        if dii_data is not None and len(dii_data) > 0:
            features["nifty_dii_flow"] = self._compute_flow(dii_data)
        
        if gold_data is not None and len(gold_data) > 5:
            features["gold_price"] = self._compute_trend(gold_data)
        
        if crude_data is not None and len(crude_data) > 5:
            features["crude_price"] = self._compute_trend(crude_data)
        
        for name in self.feature_names:
            if name not in features:
                features[name] = 0.0
        
        return features
    
    def _compute_breadth(self, data: pd.DataFrame) -> Dict[str, float]:
        """Compute NIFTY breadth indicators."""
        if "close" not in data.columns:
            return {"nifty_breadth": 0.0}
        
        returns = data["close"].pct_change()
        
        advancing = (returns > 0).sum()
        declining = (returns < 0).sum()
        
        total = advancing + declining
        
        if total > 0:
            breadth = (advancing - declining) / total
        else:
            breadth = 0.0
        
        return {
            "nifty_breadth": breadth,
            "nifty_advance_decline_ratio": advancing / max(declining, 1)
        }
    
    def _compute_trend(self, data: pd.DataFrame) -> float:
        """Compute trend direction (-1 to 1)."""
        if "close" not in data.columns:
            return 0.0
        
        prices = data["close"]
        
        if len(prices) < 2:
            return 0.0
        
        recent = prices.iloc[-5:] if len(prices) >= 5 else prices
        trend = (recent.iloc[-1] - recent.iloc[0]) / recent.iloc[0]
        
        return float(np.clip(trend * 10, -1, 1))
    
    def _compute_level(self, data: pd.DataFrame) -> float:
        """Compute normalized level."""
        if "close" not in data.columns:
            return 0.0
        
        prices = data["close"]
        
        if len(prices) < 20:
            return 0.0
        
        current = prices.iloc[-1]
        mean = prices.rolling(20).mean().iloc[-1]
        std = prices.rolling(20).std().iloc[-1]
        
        if std > 0:
            zscore = (current - mean) / std
        else:
            zscore = 0.0
        
        return float(np.clip(zscore / 3, -1, 1))
    
    def _compute_flow(self, data: pd.DataFrame) -> float:
        """Compute flow direction."""
        if "close" not in data.columns and "flow" not in data.columns:
            return 0.0
        
        if "flow" in data.columns:
            flow = data["flow"]
        else:
            flow = data["close"]
        
        if len(flow) < 5:
            return 0.0
        
        recent_flow = flow.iloc[-5:].sum()
        
        return float(np.clip(recent_flow / 1e9, -1, 1))


class SectorRotationSignal:
    """
    Sector rotation signals for Indian markets.
    
    Identifies which sectors are outperforming.
    """
    
    SECTOR_ETFS = {
        "nifty_auto": "NIFTYAUTO.NS",
        "nifty_bank": "NIFTYBANK.NS",
        "nifty_it": "NIFTYIT.NS",
        "nifty_pharma": "NIFTYPHARMA.NS",
        "nifty_fmcg": "NIFTYFMCG.NS",
        "nifty_metal": "NIFTYMETAL.NS",
        "nifty_energy": "NIFTYENERGY.NS"
    }
    
    def compute_rotation(
        self,
        sector_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, float]:
        """
        Compute sector rotation signals.
        
        Args:
            sector_data: Dict of sector_name -> price data
            
        Returns:
            Dictionary of sector -> relative strength
        """
        returns = {}
        
        for sector, data in sector_data.items():
            if data is not None and "close" in data.columns and len(data) > 20:
                ret_20d = (data["close"].iloc[-1] / data["close"].iloc[-20] - 1)
                returns[sector] = ret_20d
        
        if not returns:
            return {}
        
        mean_return = np.mean(list(returns.values()))
        
        rotation = {}
        for sector, ret in returns.items():
            relative_strength = ret - mean_return
            rotation[f"{sector}_strength"] = relative_strength
        
        best_sector = max(returns.items(), key=lambda x: x[1])
        worst_sector = min(returns.items(), key=lambda x: x[1])
        
        rotation["best_sector"] = best_sector[0]
        rotation["best_sector_return"] = best_sector[1]
        rotation["worst_sector"] = worst_sector[0]
        rotation["worst_sector_return"] = worst_sector[1]
        
        return rotation


class MacroIndicatorCalculator:
    """
    Calculates macro indicators that affect Indian markets.
    """
    
    def calculate(
        self,
        market_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, float]:
        """
        Calculate macro indicators.
        
        Args:
            market_data: Dictionary of market data
            
        Returns:
            Macro indicators
        """
        indicators = {}
        
        for name, data in market_data.items():
            if data is not None and len(data) > 20:
                indicators[f"{name}_return_20d"] = float(
                    (data["close"].iloc[-1] / data["close"].iloc[-20] - 1)
                )
                indicators[f"{name}_volatility_20d"] = float(
                    data["close"].pct_change().rolling(20).std().iloc[-1]
                )
        
        return indicators
