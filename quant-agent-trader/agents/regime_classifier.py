"""
Regime Classifier - Automatic market regime detection.
"""

from typing import Dict, Optional
import pandas as pd
import numpy as np
from dataclasses import dataclass
from datetime import datetime

from features.indicators import TechnicalFeatures


@dataclass
class RegimeResult:
    """Result of market regime classification."""
    regime_type: str  # bull, bear, sideways, high_volatility
    volatility_level: str  # low, normal, high, extreme
    trend_direction: str  # up, down, sideways
    confidence: float  # 0-100
    details: Dict[str, float]


class RegimeClassifier:
    """Classifier for detecting market regimes based on technical indicators."""

    def __init__(self):
        """Initialize the regime classifier."""
        self._tech_features = TechnicalFeatures()

    def classify(self, df: pd.DataFrame) -> RegimeResult:
        """
        Perform full regime classification.

        Args:
            df: DataFrame with price data

        Returns:
            RegimeResult with full regime classification
        """
        if df.empty or len(df) < 200:
            return RegimeResult(
                regime_type="unknown",
                volatility_level="unknown",
                trend_direction="unknown",
                confidence=0.0,
                details={}
            )

        df = self._ensure_features(df)

        trend_direction = self.get_trend_direction(df)
        volatility_level = self.get_volatility_level(df)
        confidence = self.calculate_regime_confidence(df)

        regime_type = self._determine_regime_type(
            df, trend_direction, volatility_level
        )

        details = self._build_details(df, trend_direction, volatility_level)

        return RegimeResult(
            regime_type=regime_type,
            volatility_level=volatility_level,
            trend_direction=trend_direction,
            confidence=confidence,
            details=details
        )

    def classify_current(self, df: pd.DataFrame) -> str:
        """
        Get simple regime string for current market state.

        Args:
            df: DataFrame with price data

        Returns:
            Simple regime string: bull, bear, sideways, high_volatility, unknown
        """
        result = self.classify(df)
        return result.regime_type

    def get_volatility_level(self, df: pd.DataFrame) -> str:
        """
        Analyze volatility using ATR and standard deviation.

        Args:
            df: DataFrame with price data

        Returns:
            Volatility level: low, normal, high, extreme
        """
        df = self._ensure_features(df)

        latest = df.iloc[-1]
        atr = latest.get('atr', 0)
        close = latest.get('close', 0)

        if close == 0:
            return "normal"

        atr_pct = (atr / close) * 100

        volatility_20 = latest.get('volatility_20', 0)

        hist_vol = df['volatility_20'].dropna()
        if len(hist_vol) < 20:
            return "normal"

        avg_volatility = hist_vol.rolling(20).mean().iloc[-1]
        current_vol = volatility_20

        if current_vol > avg_volatility * 2.5 or atr_pct > 5:
            return "extreme"
        elif current_vol > avg_volatility * 2.0 or atr_pct > 3.5:
            return "high"
        elif current_vol < avg_volatility * 0.5 or atr_pct < 1:
            return "low"
        else:
            return "normal"

    def get_trend_direction(self, df: pd.DataFrame) -> str:
        """
        Analyze trend direction using SMA crossovers.

        Args:
            df: DataFrame with price data

        Returns:
            Trend direction: up, down, sideways
        """
        df = self._ensure_features(df)

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        sma_50 = latest.get('sma_50', 0)
        sma_200 = latest.get('sma_200', 0)
        sma_20 = latest.get('sma_20', 0)
        sma_50_prev = prev.get('sma_50', 0)
        sma_200_prev = prev.get('sma_200', 0)

        price = latest.get('close', 0)

        golden_cross = sma_50 > sma_200
        death_cross = sma_50 < sma_200

        sma_50_rising = sma_50 > sma_50_prev
        price_above_sma_50 = price > sma_50
        price_above_sma_20 = price > sma_20

        up_score = 0
        down_score = 0

        if golden_cross:
            up_score += 2
        elif death_cross:
            down_score += 2

        if sma_50_rising:
            up_score += 1
        else:
            down_score += 1

        if price_above_sma_50 and price_above_sma_20:
            up_score += 1

        trend_strength = abs(sma_50 - sma_200) / sma_200 if sma_200 != 0 else 0

        if trend_strength < 0.01:
            return "sideways"

        if up_score > down_score + 1:
            return "up"
        elif down_score > up_score + 1:
            return "down"
        else:
            return "sideways"

    def calculate_regime_confidence(self, df: pd.DataFrame) -> float:
        """
        Calculate confidence score for regime classification.

        Args:
            df: DataFrame with price data

        Returns:
            Confidence score 0-100
        """
        if df.empty or len(df) < 200:
            return 0.0

        df = self._ensure_features(df)

        latest = df.iloc[-1]

        sma_50 = latest.get('sma_50', 0)
        sma_200 = latest.get('sma_200', 0)
        rsi = latest.get('rsi', 50)
        volatility = latest.get('volatility_20', 0)

        hist_vol = df['volatility_20'].dropna()
        if len(hist_vol) >= 20:
            avg_volatility = hist_vol.rolling(20).mean().iloc[-1]
            vol_ratio = volatility / avg_volatility if avg_volatility > 0 else 1
        else:
            vol_ratio = 1

        confidence = 50.0

        if sma_200 != 0:
            sma_gap = abs(sma_50 - sma_200) / sma_200
            confidence += min(sma_gap * 100, 25)

        rsi_valid = 30 <= rsi <= 70
        if rsi_valid:
            rsi_centrality = 1 - abs(rsi - 50) / 20
            confidence += rsi_centrality * 15

        if 0.5 <= vol_ratio <= 2.0:
            vol_confidence = 1 - abs(vol_ratio - 1) / 1.5
            confidence += vol_confidence * 10

        return min(confidence, 100.0)

    def _ensure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure technical features are calculated."""
        if 'sma_200' not in df.columns:
            df = TechnicalFeatures.calculate_all(df)
        return df

    def _determine_regime_type(
        self,
        df: pd.DataFrame,
        trend_direction: str,
        volatility_level: str
    ) -> str:
        """Determine the regime type based on indicators."""
        latest = df.iloc[-1]

        sma_50 = latest.get('sma_50', 0)
        sma_200 = latest.get('sma_200', 0)
        rsi = latest.get('rsi', 50)

        if volatility_level == "extreme":
            return "high_volatility"

        if trend_direction == "up" and sma_50 > sma_200:
            if 40 <= rsi <= 70 and volatility_level in ["low", "normal"]:
                return "bull"
            else:
                return "bull"

        elif trend_direction == "down" and sma_50 < sma_200:
            if 30 <= rsi <= 60 and volatility_level in ["high", "normal"]:
                return "bear"
            else:
                return "bear"

        elif trend_direction == "sideways":
            return "sideways"

        if volatility_level == "high":
            return "high_volatility"

        return "sideways"

    def _build_details(
        self,
        df: pd.DataFrame,
        trend_direction: str,
        volatility_level: str
    ) -> Dict[str, float]:
        """Build detailed information dictionary."""
        latest = df.iloc[-1]

        return {
            'rsi': float(latest.get('rsi', 50)),
            'sma_50': float(latest.get('sma_50', 0)),
            'sma_200': float(latest.get('sma_200', 0)),
            'sma_20': float(latest.get('sma_20', 0)),
            'atr': float(latest.get('atr', 0)),
            'volatility_20': float(latest.get('volatility_20', 0)),
            'close': float(latest.get('close', 0)),
            'sma_50_200_diff': float(latest.get('sma_50_200_cross', 0)),
            'trend_strength': float(latest.get('trend_strength', 0))
        }


def create_regime_classifier() -> RegimeClassifier:
    """
    Factory function to create a RegimeClassifier instance.

    Returns:
        New RegimeClassifier instance
    """
    return RegimeClassifier()
