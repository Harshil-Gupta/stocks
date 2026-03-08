"""
Feature Engineering - Technical Indicators
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime


class TechnicalFeatures:
    """Calculate technical analysis features from price data."""
    
    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators."""
        df = df.copy()
        
        # Price-based features
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Moving averages
        for window in [5, 10, 20, 50, 100, 200]:
            df[f'sma_{window}'] = df['close'].rolling(window=window).mean()
            df[f'ema_{window}'] = df['close'].ewm(span=window, adjust=False).mean()
        
        # Moving average crossovers
        df['sma_5_20_cross'] = (df['sma_5'] > df['sma_20']).astype(int)
        df['sma_20_50_cross'] = (df['sma_20'] > df['sma_50']).astype(int)
        df['sma_50_200_cross'] = (df['sma_50'] > df['sma_200']).astype(int)
        
        # RSI
        df['rsi'] = TechnicalFeatures.calculate_rsi(df['close'])
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = TechnicalFeatures.calculate_macd(
            df['close']
        )
        
        # Bollinger Bands
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = TechnicalFeatures.calculate_bollinger_bands(
            df['close']
        )
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR
        df['atr'] = TechnicalFeatures.calculate_atr(df)
        
        # Volume features
        df['volume_sma_20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        
        # Momentum
        for period in [5, 10, 20]:
            df[f'momentum_{period}'] = df['close'] / df['close'].shift(period) - 1
        
        # Stochastic
        df['stoch_k'], df['stoch_d'] = TechnicalFeatures.calculate_stochastic(df)
        
        # Support/Resistance
        df['pivot'], df['support_1'], df['resistance_1'] = TechnicalFeatures.calculate_pivot(df)
        
        # Price position
        df['price_position_20'] = (df['close'] - df['low'].rolling(20).min()) / \
                                   (df['high'].rolling(20).max() - df['low'].rolling(20).min())
        df['price_position_50'] = (df['close'] - df['low'].rolling(50).min()) / \
                                   (df['high'].rolling(50).max() - df['low'].rolling(50).min())
        
        # Volatility
        df['volatility_10'] = df['returns'].rolling(10).std()
        df['volatility_20'] = df['returns'].rolling(20).std()
        df['volatility_30'] = df['returns'].rolling(30).std()
        
        # Trend strength
        df['trend_strength'] = abs(df['sma_20'] - df['sma_50']) / df['sma_50']
        
        # Additional Advanced Indicators
        # Williams %R
        df['williams_r'] = TechnicalFeatures.calculate_williams_r(df)
        
        # CCI (Commodity Channel Index)
        df['cci'] = TechnicalFeatures.calculate_cci(df)
        
        # ADX (Average Directional Index)
        df['adx'], df['plus_di'], df['minus_di'] = TechnicalFeatures.calculate_adx(df)
        
        # OBV (On-Balance Volume)
        df['obv'] = TechnicalFeatures.calculate_obv(df)
        
        # VWAP (Volume Weighted Average Price)
        df['vwap'] = TechnicalFeatures.calculate_vwap(df)
        
        # MFI (Money Flow Index)
        df['mfi'] = TechnicalFeatures.calculate_mfi(df)
        
        # Keltner Channels
        df['keltner_upper'], df['keltner_middle'], df['keltner_lower'] = TechnicalFeatures.calculate_keltner_channels(df)
        
        # Donchian Channels
        df['donchian_upper'], df['donchian_middle'], df['donchian_lower'] = TechnicalFeatures.calculate_donchian_channels(df)
        
        # Ichimoku Cloud
        df['ichimoku_tenkan'], df['ichimoku_kijun'], df['ichimoku_senkou_a'], df['ichimoku_senkou_b'], df['ichimoku_cloud'] = TechnicalFeatures.calculate_ichimoku(df)
        
        # ROC (Rate of Change)
        for period in [5, 10, 20]:
            df[f'roc_{period}'] = ((df['close'] - df['close'].shift(period)) / df['close'].shift(period)) * 100
        
        # Average Price
        df['avg_price'] = (df['high'] + df['low'] + df['close']) / 3
        
        # Typical Price
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        
        # Median Price
        df['median_price'] = (df['high'] + df['low']) / 2
        
        # Weight Close Price
        df['weighted_close'] = (df['high'] + df['low'] + 2 * df['close']) / 4
        
        # True Range (for ADX)
        df['true_range'] = TechnicalFeatures.calculate_true_range(df)
        
        return df
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(
        prices: pd.Series, 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9
    ) -> tuple:
        """Calculate MACD indicator."""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: pd.Series, 
        window: int = 20, 
        num_std: float = 2.0
    ) -> tuple:
        """Calculate Bollinger Bands."""
        middle = prices.rolling(window).mean()
        std = prices.rolling(window).std()
        upper = middle + (std * num_std)
        lower = middle - (std * num_std)
        return upper, middle, lower
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean()
        return atr
    
    @staticmethod
    def calculate_stochastic(df: pd.DataFrame, period: int = 14) -> tuple:
        """Calculate Stochastic Oscillator."""
        low_min = df['low'].rolling(window=period).min()
        high_max = df['high'].rolling(window=period).max()
        
        stoch_k = 100 * (df['close'] - low_min) / (high_max - low_min)
        stoch_d = stoch_k.rolling(window=3).mean()
        return stoch_k, stoch_d
    
    @staticmethod
    def calculate_pivot(df: pd.DataFrame) -> tuple:
        """Calculate pivot points and support/resistance."""
        pivot = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
        support_1 = (pivot * 2) - df['high'].shift(1)
        resistance_1 = (pivot * 2) - df['low'].shift(1)
        return pivot, support_1, resistance_1
    
    @staticmethod
    def calculate_williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Williams %R indicator."""
        highest_high = df['high'].rolling(window=period).max()
        lowest_low = df['low'].rolling(window=period).min()
        
        williams_r = -100 * (highest_high - df['close']) / (highest_high - lowest_low)
        return williams_r
    
    @staticmethod
    def calculate_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Commodity Channel Index."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mean_deviation = typical_price.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
        )
        cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
        return cci
    
    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> tuple:
        """Calculate Average Directional Index (ADX)."""
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = TechnicalFeatures.calculate_true_range(df)
        
        atr = tr.rolling(window=period).mean()
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx, plus_di, minus_di
    
    @staticmethod
    def calculate_true_range(df: pd.DataFrame) -> pd.Series:
        """Calculate True Range."""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range
    
    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.Series:
        """Calculate On-Balance Volume."""
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        return obv
    
    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.Series:
        """Calculate Volume Weighted Average Price."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return vwap
    
    @staticmethod
    def calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Money Flow Index."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
        
        positive_sum = positive_flow.rolling(window=period).sum()
        negative_sum = negative_flow.rolling(window=period).sum()
        
        money_ratio = positive_sum / negative_sum
        mfi = 100 - (100 / (1 + money_ratio))
        
        return mfi
    
    @staticmethod
    def calculate_keltner_channels(df: pd.DataFrame, period: int = 20, multiplier: float = 2.0) -> tuple:
        """Calculate Keltner Channels."""
        middle = df['close'].ewm(span=period).mean()
        atr = TechnicalFeatures.calculate_atr(df).rolling(window=period).mean()
        
        upper = middle + (multiplier * atr)
        lower = middle - (multiplier * atr)
        
        return upper, middle, lower
    
    @staticmethod
    def calculate_donchian_channels(df: pd.DataFrame, period: int = 20) -> tuple:
        """Calculate Donchian Channels."""
        upper = df['high'].rolling(window=period).max()
        lower = df['low'].rolling(window=period).min()
        middle = (upper + lower) / 2
        
        return upper, middle, lower
    
    @staticmethod
    def calculate_ichimoku(df: pd.DataFrame) -> tuple:
        """Calculate Ichimoku Cloud."""
        nine_period_high = df['high'].rolling(window=9).max()
        nine_period_low = df['low'].rolling(window=9).min()
        tenkan = (nine_period_high + nine_period_low) / 2
        
        twenty_six_period_high = df['high'].rolling(window=26).max()
        twenty_six_period_low = df['low'].rolling(window=26).min()
        kijun = (twenty_six_period_high + twenty_six_period_low) / 2
        
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        
        fifty_two_period_high = df['high'].rolling(window=52).max()
        fifty_two_period_low = df['low'].rolling(window=52).min()
        senkou_b = ((fifty_two_period_high + fifty_two_period_low) / 2).shift(26)
        
        cloud = np.where(senkou_a >= senkou_b, 1, -1)
        
        return tenkan, kijun, senkou_a, senkou_b, cloud
    
    @staticmethod
    def get_current_features(df: pd.DataFrame) -> Dict:
        """Get latest feature values as a dictionary."""
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        
        # Ensure returns are calculated
        returns = 0.0
        if 'returns' in df.columns and len(df) > 1:
            returns = float(df['returns'].iloc[-1])
        
        return {
            'close': float(latest.get('close', 0)),
            'open': float(latest.get('open', 0)),
            'high': float(latest.get('high', 0)),
            'low': float(latest.get('low', 0)),
            'volume': float(latest.get('volume', 0)),
            'returns': returns,
            'rsi': float(latest.get('rsi', 50)),
            'macd': float(latest.get('macd', 0)),
            'macd_signal': float(latest.get('macd_signal', 0)),
            'macd_hist': float(latest.get('macd_hist', 0)),
            'sma_20': float(latest.get('sma_20', 0)),
            'sma_50': float(latest.get('sma_50', 0)),
            'sma_200': float(latest.get('sma_200', 0)),
            'bb_position': float(latest.get('bb_position', 0.5)),
            'atr': float(latest.get('atr', 0)),
            'volume_ratio': float(latest.get('volume_ratio', 1)),
            'momentum_5': float(latest.get('momentum_5', 0)),
            'momentum_20': float(latest.get('momentum_20', 0)),
            'volatility_20': float(latest.get('volatility_20', 0)),
            'trend_strength': float(latest.get('trend_strength', 0)),
            'stoch_k': float(latest.get('stoch_k', 50)),
            'stoch_d': float(latest.get('stoch_d', 50)),
            'price_position_20': float(latest.get('price_position_20', 0.5)),
            # New indicators
            'williams_r': float(latest.get('williams_r', -50)),
            'cci': float(latest.get('cci', 0)),
            'adx': float(latest.get('adx', 0)),
            'plus_di': float(latest.get('plus_di', 0)),
            'minus_di': float(latest.get('minus_di', 0)),
            'obv': float(latest.get('obv', 0)),
            'vwap': float(latest.get('vwap', 0)),
            'mfi': float(latest.get('mfi', 50)),
            'keltner_upper': float(latest.get('keltner_upper', 0)),
            'keltner_middle': float(latest.get('keltner_middle', 0)),
            'keltner_lower': float(latest.get('keltner_lower', 0)),
            'donchian_upper': float(latest.get('donchian_upper', 0)),
            'donchian_middle': float(latest.get('donchian_middle', 0)),
            'donchian_lower': float(latest.get('donchian_lower', 0)),
            'ichimoku_tenkan': float(latest.get('ichimoku_tenkan', 0)),
            'ichimoku_kijun': float(latest.get('ichimoku_kijun', 0)),
            'roc_5': float(latest.get('roc_5', 0)),
            'roc_10': float(latest.get('roc_10', 0)),
            'roc_20': float(latest.get('roc_20', 0)),
        }


class FundamentalFeatures:
    """Calculate fundamental analysis features."""
    
    @staticmethod
    def calculate_valuation_metrics(
        price: float,
        eps: float,
        book_value: float,
        sales_per_share: float,
        cashflow_per_share: float
    ) -> Dict:
        """Calculate valuation ratios."""
        return {
            'pe_ratio': price / eps if eps > 0 else 0,
            'pb_ratio': price / book_value if book_value > 0 else 0,
            'ps_ratio': price / sales_per_share if sales_per_share > 0 else 0,
            'pcf_ratio': price / cashflow_per_share if cashflow_per_share > 0 else 0,
        }
    
    @staticmethod
    def calculate_growth_metrics(
        current_eps: float,
        previous_eps: float,
        current_revenue: float,
        previous_revenue: float,
        current_book: float,
        previous_book: float
    ) -> Dict:
        """Calculate growth metrics."""
        return {
            'eps_growth': (current_eps - previous_eps) / previous_eps if previous_eps > 0 else 0,
            'revenue_growth': (current_revenue - previous_revenue) / previous_revenue if previous_revenue > 0 else 0,
            'book_growth': (current_book - previous_book) / previous_book if previous_book > 0 else 0,
        }
    
    @staticmethod
    def calculate_profitability_metrics(
        roe: float,
        roa: float,
        profit_margin: float,
        operating_margin: float
    ) -> Dict:
        """Calculate profitability metrics."""
        return {
            'roe': roe,
            'roa': roa,
            'profit_margin': profit_margin,
            'operating_margin': operating_margin,
        }


class SentimentFeatures:
    """Calculate sentiment features from news and social data."""
    
    @staticmethod
    def calculate_sentiment_score(
        positive_count: int,
        negative_count: int,
        neutral_count: int
    ) -> Dict:
        """Calculate sentiment scores."""
        total = positive_count + negative_count + neutral_count
        if total == 0:
            return {
                'sentiment_score': 0,
                'sentiment_magnitude': 0,
                'bull_bear_ratio': 1
            }
        
        score = (positive_count - negative_count) / total
        magnitude = (positive_count + negative_count) / total
        bull_bear = positive_count / negative_count if negative_count > 0 else float('inf')
        
        return {
            'sentiment_score': score,
            'sentiment_magnitude': magnitude,
            'bull_bear_ratio': bull_bear
        }
