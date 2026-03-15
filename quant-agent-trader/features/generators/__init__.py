"""
Modular Feature Generators.

Each feature is a pluggable component that:
- Computes a specific technical indicator or feature
- Has no lookahead bias (uses only past data)
- Declares its dependencies
- Specifies required lookback window
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from abc import ABC

from features.registry import FeatureGenerator, FeatureRegistry


class PriceFeatureGenerator(FeatureGenerator):
    """Base class for price-based features."""

    @property
    def lookback_required(self) -> int:
        return 1

    def get_dependencies(self) -> List[str]:
        return ["close"]


@FeatureRegistry.register(
    name="returns",
    category="price",
    description="Simple returns",
    lookback_required=2,
    provides=["returns", "log_returns"],
)
class ReturnsGenerator(PriceFeatureGenerator):
    """Generate return features."""

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)
        result["returns"] = data["close"].pct_change()
        result["log_returns"] = np.log(data["close"] / data["close"].shift(1))
        return result


@FeatureRegistry.register(
    name="sma",
    category="trend",
    description="Simple Moving Average",
    dependencies=["close"],
    lookback_required=20,
    provides=["sma"],
)
class SMAGenerator(FeatureGenerator):
    """Simple Moving Average generator."""

    def __init__(self, windows: List[int] = None):
        self.windows = windows or [5, 10, 20, 50, 100, 200]

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)
        for window in self.windows:
            result[f"sma_{window}"] = (
                data["close"].rolling(window=window, min_periods=window).mean()
            )
        return result

    def get_dependencies(self) -> List[str]:
        return ["close"]

    @property
    def lookback_required(self) -> int:
        return max(self.windows)


@FeatureRegistry.register(
    name="ema",
    category="trend",
    description="Exponential Moving Average",
    dependencies=["close"],
    lookback_required=20,
    provides=["ema"],
)
class EMAGenerator(FeatureGenerator):
    """Exponential Moving Average generator."""

    def __init__(self, spans: List[int] = None):
        self.spans = spans or [5, 10, 20, 50, 100, 200]

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)
        for span in self.spans:
            result[f"ema_{span}"] = (
                data["close"].ewm(span=span, adjust=False, min_periods=span).mean()
            )
        return result

    def get_dependencies(self) -> List[str]:
        return ["close"]

    @property
    def lookback_required(self) -> int:
        return max(self.spans)


@FeatureRegistry.register(
    name="rsi",
    category="momentum",
    description="Relative Strength Index",
    dependencies=["close"],
    lookback_required=14,
    provides=["rsi"],
)
class RSIGenerator(FeatureGenerator):
    """RSI (Relative Strength Index) generator."""

    def __init__(self, period: int = 14):
        self.period = period

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        delta = data["close"].diff()
        gain = (
            delta.where(delta > 0, 0)
            .rolling(window=self.period, min_periods=self.period)
            .mean()
        )
        loss = (
            (-delta.where(delta < 0, 0))
            .rolling(window=self.period, min_periods=self.period)
            .mean()
        )

        rs = gain / loss.replace(0, np.nan)
        result["rsi"] = 100 - (100 / (1 + rs))

        return result

    def get_dependencies(self) -> List[str]:
        return ["close"]

    @property
    def lookback_required(self) -> int:
        return self.period


@FeatureRegistry.register(
    name="macd",
    category="momentum",
    description="Moving Average Convergence Divergence",
    dependencies=["close"],
    lookback_required=26,
    provides=["macd", "macd_signal", "macd_hist"],
)
class MACDGenerator(FeatureGenerator):
    """MACD generator."""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        ema_fast = (
            data["close"]
            .ewm(span=self.fast, adjust=False, min_periods=self.fast)
            .mean()
        )
        ema_slow = (
            data["close"]
            .ewm(span=self.slow, adjust=False, min_periods=self.slow)
            .mean()
        )

        result["macd"] = ema_fast - ema_slow
        result["macd_signal"] = (
            result["macd"]
            .ewm(span=self.signal, adjust=False, min_periods=self.signal)
            .mean()
        )
        result["macd_hist"] = result["macd"] - result["macd_signal"]

        return result

    def get_dependencies(self) -> List[str]:
        return ["close"]

    @property
    def lookback_required(self) -> int:
        return self.slow


@FeatureRegistry.register(
    name="bollinger_bands",
    category="volatility",
    description="Bollinger Bands",
    dependencies=["close"],
    lookback_required=20,
    provides=["bb_upper", "bb_middle", "bb_lower", "bb_position", "bb_width"],
)
class BollingerBandsGenerator(FeatureGenerator):
    """Bollinger Bands generator."""

    def __init__(self, window: int = 20, num_std: float = 2.0):
        self.window = window
        self.num_std = num_std

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        rolling_mean = (
            data["close"].rolling(window=self.window, min_periods=self.window).mean()
        )
        rolling_std = (
            data["close"].rolling(window=self.window, min_periods=self.window).std()
        )

        result["bb_middle"] = rolling_mean
        result["bb_upper"] = rolling_mean + (rolling_std * self.num_std)
        result["bb_lower"] = rolling_mean - (rolling_std * self.num_std)

        bb_range = result["bb_upper"] - result["bb_lower"]
        result["bb_position"] = (data["close"] - result["bb_lower"]) / bb_range.replace(
            0, np.nan
        )
        result["bb_width"] = bb_range / result["bb_middle"].replace(0, np.nan)

        return result

    def get_dependencies(self) -> List[str]:
        return ["close"]

    @property
    def lookback_required(self) -> int:
        return self.window


@FeatureRegistry.register(
    name="atr",
    category="volatility",
    description="Average True Range",
    dependencies=["high", "low", "close"],
    lookback_required=14,
    provides=["atr", "true_range"],
)
class ATRGenerator(FeatureGenerator):
    """Average True Range generator."""

    def __init__(self, period: int = 14):
        self.period = period

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        high_low = data["high"] - data["low"]
        high_close = np.abs(data["high"] - data["close"].shift())
        low_close = np.abs(data["low"] - data["close"].shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        result["true_range"] = true_range
        result["atr"] = true_range.rolling(
            window=self.period, min_periods=self.period
        ).mean()

        return result

    def get_dependencies(self) -> List[str]:
        return ["high", "low", "close"]

    @property
    def lookback_required(self) -> int:
        return self.period + 1


@FeatureRegistry.register(
    name="volatility",
    category="volatility",
    description="Historical volatility",
    dependencies=["close"],
    lookback_required=20,
    provides=["volatility"],
)
class VolatilityGenerator(FeatureGenerator):
    """Historical volatility generator."""

    def __init__(self, windows: List[int] = None):
        self.windows = windows or [5, 10, 20, 30, 50]

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)
        returns = data["close"].pct_change()

        for window in self.windows:
            result[f"volatility_{window}"] = returns.rolling(
                window=window, min_periods=window
            ).std() * np.sqrt(252)

        return result

    def get_dependencies(self) -> List[str]:
        return ["close"]

    @property
    def lookback_required(self) -> int:
        return max(self.windows)


@FeatureRegistry.register(
    name="momentum",
    category="momentum",
    description="Price momentum",
    dependencies=["close"],
    lookback_required=20,
    provides=["momentum"],
)
class MomentumGenerator(FeatureGenerator):
    """Momentum generator."""

    def __init__(self, periods: List[int] = None):
        self.periods = periods or [5, 10, 20, 50]

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        for period in self.periods:
            result[f"momentum_{period}"] = (
                data["close"] / data["close"].shift(period) - 1
            )

        return result

    def get_dependencies(self) -> List[str]:
        return ["close"]

    @property
    def lookback_required(self) -> int:
        return max(self.periods)


@FeatureRegistry.register(
    name="roc",
    category="momentum",
    description="Rate of Change",
    dependencies=["close"],
    lookback_required=20,
    provides=["roc"],
)
class ROCGenerator(FeatureGenerator):
    """Rate of Change generator."""

    def __init__(self, periods: List[int] = None):
        self.periods = periods or [5, 10, 20]

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        for period in self.periods:
            result[f"roc_{period}"] = (
                (data["close"] - data["close"].shift(period))
                / data["close"].shift(period).replace(0, np.nan)
            ) * 100

        return result

    def get_dependencies(self) -> List[str]:
        return ["close"]

    @property
    def lookback_required(self) -> int:
        return max(self.periods)


@FeatureRegistry.register(
    name="volume_indicators",
    category="volume",
    description="Volume-based indicators",
    dependencies=["close", "volume"],
    lookback_required=20,
    provides=["volume_sma", "volume_ratio", "obv"],
)
class VolumeIndicatorsGenerator(FeatureGenerator):
    """Volume indicators generator."""

    def __init__(self, window: int = 20):
        self.window = window

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        result["volume_sma"] = (
            data["volume"].rolling(window=self.window, min_periods=self.window).mean()
        )
        result["volume_ratio"] = data["volume"] / result["volume_sma"].replace(
            0, np.nan
        )

        result["obv"] = (
            (np.sign(data["close"].diff()) * data["volume"]).fillna(0).cumsum()
        )

        return result

    def get_dependencies(self) -> List[str]:
        return ["close", "volume"]

    @property
    def lookback_required(self) -> int:
        return self.window


@FeatureRegistry.register(
    name="stochastic",
    category="momentum",
    description="Stochastic Oscillator",
    dependencies=["high", "low", "close"],
    lookback_required=14,
    provides=["stoch_k", "stoch_d"],
)
class StochasticGenerator(FeatureGenerator):
    """Stochastic Oscillator generator."""

    def __init__(self, period: int = 14, smooth_k: int = 3):
        self.period = period
        self.smooth_k = smooth_k

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        low_min = data["low"].rolling(window=self.period, min_periods=self.period).min()
        high_max = (
            data["high"].rolling(window=self.period, min_periods=self.period).max()
        )

        k_range = high_max - low_min
        result["stoch_k"] = 100 * (data["close"] - low_min) / k_range.replace(0, np.nan)
        result["stoch_d"] = (
            result["stoch_k"]
            .rolling(window=self.smooth_k, min_periods=self.smooth_k)
            .mean()
        )

        return result

    def get_dependencies(self) -> List[str]:
        return ["high", "low", "close"]

    @property
    def lookback_required(self) -> int:
        return self.period


@FeatureRegistry.register(
    name="cci",
    category="momentum",
    description="Commodity Channel Index",
    dependencies=["high", "low", "close"],
    lookback_required=20,
    provides=["cci"],
)
class CCIGenerator(FeatureGenerator):
    """CCI generator."""

    def __init__(self, period: int = 20):
        self.period = period

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        typical_price = (data["high"] + data["low"] + data["close"]) / 3
        sma_tp = typical_price.rolling(
            window=self.period, min_periods=self.period
        ).mean()

        mean_deviation = typical_price.rolling(window=self.period).apply(
            lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
        )

        result["cci"] = (typical_price - sma_tp) / (
            0.015 * mean_deviation.replace(0, np.nan)
        )

        return result

    def get_dependencies(self) -> List[str]:
        return ["high", "low", "close"]

    @property
    def lookback_required(self) -> int:
        return self.period


@FeatureRegistry.register(
    name="adx",
    category="trend",
    description="Average Directional Index",
    dependencies=["high", "low", "close"],
    lookback_required=28,
    provides=["adx", "plus_di", "minus_di"],
)
class ADXGenerator(FeatureGenerator):
    """ADX generator."""

    def __init__(self, period: int = 14):
        self.period = period

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        high_diff = data["high"].diff()
        low_diff = -data["low"].diff()

        plus_dm = high_diff.where(high_diff > low_diff, 0)
        minus_dm = low_diff.where(low_diff > high_diff, 0)

        high_low = data["high"] - data["low"]
        high_close = np.abs(data["high"] - data["close"].shift())
        low_close = np.abs(data["low"] - data["close"].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        atr = true_range.rolling(window=self.period, min_periods=self.period).mean()

        plus_di = 100 * (
            plus_dm.rolling(window=self.period, min_periods=self.period).mean()
            / atr.replace(0, np.nan)
        )
        minus_di = 100 * (
            minus_dm.rolling(window=self.period, min_periods=self.period).mean()
            / atr.replace(0, np.nan)
        )

        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        result["adx"] = dx.rolling(window=self.period, min_periods=self.period).mean()
        result["plus_di"] = plus_di
        result["minus_di"] = minus_di

        return result

    def get_dependencies(self) -> List[str]:
        return ["high", "low", "close"]

    @property
    def lookback_required(self) -> int:
        return self.period * 2


@FeatureRegistry.register(
    name="williams_r",
    category="momentum",
    description="Williams %R",
    dependencies=["high", "low", "close"],
    lookback_required=14,
    provides=["williams_r"],
)
class WilliamsRGenerator(FeatureGenerator):
    """Williams %R generator."""

    def __init__(self, period: int = 14):
        self.period = period

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        highest_high = (
            data["high"].rolling(window=self.period, min_periods=self.period).max()
        )
        lowest_low = (
            data["low"].rolling(window=self.period, min_periods=self.period).min()
        )

        result["williams_r"] = -100 * (
            (highest_high - data["close"])
            / (highest_high - lowest_low).replace(0, np.nan)
        )

        return result

    def get_dependencies(self) -> List[str]:
        return ["high", "low", "close"]

    @property
    def lookback_required(self) -> int:
        return self.period


@FeatureRegistry.register(
    name="mfi",
    category="volume",
    description="Money Flow Index",
    dependencies=["high", "low", "close", "volume"],
    lookback_required=14,
    provides=["mfi", "typical_price"],
)
class MFIGenerator(FeatureGenerator):
    """MFI generator."""

    def __init__(self, period: int = 14):
        self.period = period

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        typical_price = (data["high"] + data["low"] + data["close"]) / 3
        result["typical_price"] = typical_price

        money_flow = typical_price * data["volume"]

        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)

        positive_sum = positive_flow.rolling(
            window=self.period, min_periods=self.period
        ).sum()
        negative_sum = negative_flow.rolling(
            window=self.period, min_periods=self.period
        ).sum()

        money_ratio = positive_sum / negative_sum.replace(0, np.nan)
        result["mfi"] = 100 - (100 / (1 + money_ratio))

        return result

    def get_dependencies(self) -> List[str]:
        return ["high", "low", "close", "volume"]

    @property
    def lookback_required(self) -> int:
        return self.period + 1


@FeatureRegistry.register(
    name="vwap",
    category="volume",
    description="Volume Weighted Average Price",
    dependencies=["high", "low", "close", "volume"],
    lookback_required=1,
    provides=["vwap"],
)
class VWAPGenerator(FeatureGenerator):
    """VWAP generator."""

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        typical_price = (data["high"] + data["low"] + data["close"]) / 3
        result["vwap"] = (typical_price * data["volume"]).cumsum() / data[
            "volume"
        ].cumsum()

        return result

    def get_dependencies(self) -> List[str]:
        return ["high", "low", "close", "volume"]

    @property
    def lookback_required(self) -> int:
        return 1


@FeatureRegistry.register(
    name="price_position",
    category="price",
    description="Price position within range",
    dependencies=["high", "low", "close"],
    lookback_required=20,
    provides=["price_position"],
)
class PricePositionGenerator(FeatureGenerator):
    """Price position within rolling range."""

    def __init__(self, windows: List[int] = None):
        self.windows = windows or [20, 50]

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        for window in self.windows:
            low_min = data["low"].rolling(window=window, min_periods=window).min()
            high_max = data["high"].rolling(window=window, min_periods=window).max()
            range_val = high_max - low_min

            result[f"price_position_{window}"] = (
                data["close"] - low_min
            ) / range_val.replace(0, np.nan)

        return result

    def get_dependencies(self) -> List[str]:
        return ["high", "low", "close"]

    @property
    def lookback_required(self) -> int:
        return max(self.windows)


@FeatureRegistry.register(
    name="ma_crossover",
    category="trend",
    description="Moving Average Crossover signals",
    dependencies=["sma", "ema"],
    lookback_required=50,
    provides=["sma_cross", "ema_cross"],
)
class MACrossoverGenerator(FeatureGenerator):
    """MA Crossover signals generator."""

    def __init__(self):
        pass

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)

        if "sma_5" in data.columns and "sma_20" in data.columns:
            result["sma_5_20_cross"] = (data["sma_5"] > data["sma_20"]).astype(int)

        if "sma_20" in data.columns and "sma_50" in data.columns:
            result["sma_20_50_cross"] = (data["sma_20"] > data["sma_50"]).astype(int)

        if "sma_50" in data.columns and "sma_200" in data.columns:
            result["sma_50_200_cross"] = (data["sma_50"] > data["sma_200"]).astype(int)

        return result

    def get_dependencies(self) -> List[str]:
        return ["sma_5", "sma_20", "sma_50", "sma_200"]

    @property
    def lookback_required(self) -> int:
        return 200


__all__ = [
    "FeatureGenerator",
    "ReturnsGenerator",
    "SMAGenerator",
    "EMAGenerator",
    "RSIGenerator",
    "MACDGenerator",
    "BollingerBandsGenerator",
    "ATRGenerator",
    "VolatilityGenerator",
    "MomentumGenerator",
    "ROCGenerator",
    "VolumeIndicatorsGenerator",
    "StochasticGenerator",
    "CCIGenerator",
    "ADXGenerator",
    "WilliamsRGenerator",
    "MFIGenerator",
    "VWAPGenerator",
    "PricePositionGenerator",
    "MACrossoverGenerator",
]
