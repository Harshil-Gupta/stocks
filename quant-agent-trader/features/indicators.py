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
    def get_current_features(df: pd.DataFrame) -> Dict:
        """Get latest feature values as a dictionary."""
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        return {
            'close': float(latest.get('close', 0)),
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
