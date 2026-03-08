"""
Technical Indicators Tests

Tests for technical analysis feature calculations.
"""

import pytest
import pandas as pd
import numpy as np
from features.indicators import TechnicalFeatures, FundamentalFeatures, SentimentFeatures


class TestTechnicalFeatures:
    """Tests for TechnicalFeatures class."""
    
    @pytest.fixture
    def sample_df(self):
        """Create sample price data."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        
        np.random.seed(42)
        base_price = 1500
        prices = base_price + np.cumsum(np.random.randn(100) * 10)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices + np.random.randn(100) * 2,
            'high': prices + np.abs(np.random.randn(100) * 5),
            'low': prices - np.abs(np.random.randn(100) * 5),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 100),
        })
        
        return df
    
    def test_calculate_all(self, sample_df):
        """Test calculating all indicators."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'returns' in result.columns
        assert 'sma_20' in result.columns
        assert 'ema_20' in result.columns
        assert 'rsi' in result.columns
        assert 'macd' in result.columns
        assert 'bb_upper' in result.columns
        assert 'atr' in result.columns
    
    def test_returns_calculation(self, sample_df):
        """Test returns calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'returns' in result.columns
        assert 'log_returns' in result.columns
        
        # Check a sample return
        expected_return = (sample_df['close'].iloc[1] / sample_df['close'].iloc[0]) - 1
        assert abs(result['returns'].iloc[1] - expected_return) < 0.001
    
    def test_sma_calculation(self, sample_df):
        """Test SMA calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        # Check SMA 20
        expected_sma = sample_df['close'].rolling(20).mean().iloc[-1]
        assert abs(result['sma_20'].iloc[-1] - expected_sma) < 0.001
    
    def test_ema_calculation(self, sample_df):
        """Test EMA calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'ema_20' in result.columns
        # EMA should be calculated (not NaN) after warmup period
        assert not pd.isna(result['ema_20'].iloc[-1])
    
    def test_rsi_calculation(self, sample_df):
        """Test RSI calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'rsi' in result.columns
        # RSI should be between 0 and 100
        valid_rsi = result['rsi'].dropna()
        assert all((valid_rsi >= 0) & (valid_rsi <= 100))
    
    def test_rsi_static_method(self):
        """Test RSI static method directly."""
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 
                           110, 108, 111, 113, 112, 114, 116, 115, 117, 119])
        
        rsi = TechnicalFeatures.calculate_rsi(prices)
        
        assert len(rsi) == len(prices)
        assert not pd.isna(rsi.iloc[-1])
    
    def test_macd_calculation(self, sample_df):
        """Test MACD calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'macd' in result.columns
        assert 'macd_signal' in result.columns
        assert 'macd_hist' in result.columns
    
    def test_bollinger_bands(self, sample_df):
        """Test Bollinger Bands calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'bb_upper' in result.columns
        assert 'bb_middle' in result.columns
        assert 'bb_lower' in result.columns
        assert 'bb_position' in result.columns
        
        # Upper band should be above lower band
        assert all(result['bb_upper'].dropna() >= result['bb_lower'].dropna())
    
    def test_atr_calculation(self, sample_df):
        """Test ATR calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'atr' in result.columns
        # ATR should be positive
        assert all(result['atr'].dropna() > 0)
    
    def test_stochastic(self, sample_df):
        """Test Stochastic Oscillator calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'stoch_k' in result.columns
        assert 'stoch_d' in result.columns
    
    def test_pivot_points(self, sample_df):
        """Test pivot points calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'pivot' in result.columns
        assert 'support_1' in result.columns
        assert 'resistance_1' in result.columns
    
    def test_momentum_calculation(self, sample_df):
        """Test momentum calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'momentum_5' in result.columns
        assert 'momentum_10' in result.columns
        assert 'momentum_20' in result.columns
    
    def test_volatility_calculation(self, sample_df):
        """Test volatility calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'volatility_10' in result.columns
        assert 'volatility_20' in result.columns
        assert 'volatility_30' in result.columns
    
    def test_volume_features(self, sample_df):
        """Test volume features."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'volume_sma_20' in result.columns
        assert 'volume_ratio' in result.columns
    
    def test_price_position(self, sample_df):
        """Test price position calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'price_position_20' in result.columns
        assert 'price_position_50' in result.columns
    
    def test_get_current_features(self, sample_df):
        """Test getting current features."""
        result = TechnicalFeatures.calculate_all(sample_df)
        current = TechnicalFeatures.get_current_features(result)
        
        assert 'close' in current
        assert 'rsi' in current
        assert 'macd' in current
        assert 'volume' in current
    
    def test_empty_dataframe(self):
        """Test handling empty dataframe."""
        df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        result = TechnicalFeatures.calculate_all(df)
        
        # Should return empty dataframe with expected columns
        assert 'returns' in result.columns
    
    def test_sma_crossover(self, sample_df):
        """Test SMA crossover indicators."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'sma_5_20_cross' in result.columns
        assert 'sma_20_50_cross' in result.columns
        assert 'sma_50_200_cross' in result.columns
    
    def test_trend_strength(self, sample_df):
        """Test trend strength calculation."""
        result = TechnicalFeatures.calculate_all(sample_df)
        
        assert 'trend_strength' in result.columns


class TestFundamentalFeatures:
    """Tests for FundamentalFeatures class."""
    
    def test_valuation_metrics(self):
        """Test valuation metrics calculation."""
        result = FundamentalFeatures.calculate_valuation_metrics(
            price=100.0,
            eps=10.0,
            book_value=50.0,
            sales_per_share=25.0,
            cashflow_per_share=15.0
        )
        
        assert result['pe_ratio'] == 10.0
        assert result['pb_ratio'] == 2.0
        assert result['ps_ratio'] == 4.0
        assert result['pcf_ratio'] == pytest.approx(6.667, rel=0.01)
    
    def test_valuation_zero_denominator(self):
        """Test valuation with zero values."""
        result = FundamentalFeatures.calculate_valuation_metrics(
            price=100.0,
            eps=0.0,
            book_value=50.0,
            sales_per_share=25.0,
            cashflow_per_share=15.0
        )
        
        assert result['pe_ratio'] == 0
    
    def test_growth_metrics(self):
        """Test growth metrics calculation."""
        result = FundamentalFeatures.calculate_growth_metrics(
            current_eps=12.0,
            previous_eps=10.0,
            current_revenue=150.0,
            previous_revenue=100.0,
            current_book=60.0,
            previous_book=50.0
        )
        
        assert result['eps_growth'] == 0.2  # 20%
        assert result['revenue_growth'] == 0.5  # 50%
        assert result['book_growth'] == 0.2  # 20%
    
    def test_growth_zero_denominator(self):
        """Test growth with zero previous values."""
        result = FundamentalFeatures.calculate_growth_metrics(
            current_eps=12.0,
            previous_eps=0.0,
            current_revenue=150.0,
            previous_revenue=0.0,
            current_book=60.0,
            previous_book=0.0
        )
        
        assert result['eps_growth'] == 0
        assert result['revenue_growth'] == 0
        assert result['book_growth'] == 0
    
    def test_profitability_metrics(self):
        """Test profitability metrics."""
        result = FundamentalFeatures.calculate_profitability_metrics(
            roe=0.15,
            roa=0.08,
            profit_margin=0.12,
            operating_margin=0.15
        )
        
        assert result['roe'] == 0.15
        assert result['roa'] == 0.08
        assert result['profit_margin'] == 0.12
        assert result['operating_margin'] == 0.15


class TestSentimentFeatures:
    """Tests for SentimentFeatures class."""
    
    def test_sentiment_score_calculation(self):
        """Test sentiment score calculation."""
        result = SentimentFeatures.calculate_sentiment_score(
            positive_count=70,
            negative_count=20,
            neutral_count=10
        )
        
        assert result['sentiment_score'] > 0
        assert result['sentiment_magnitude'] > 0
        assert result['bull_bear_ratio'] > 1
    
    def test_sentiment_all_positive(self):
        """Test with all positive sentiment."""
        result = SentimentFeatures.calculate_sentiment_score(
            positive_count=100,
            negative_count=0,
            neutral_count=0
        )
        
        assert result['sentiment_score'] == 1.0
        assert result['bull_bear_ratio'] == float('inf')
    
    def test_sentiment_all_negative(self):
        """Test with all negative sentiment."""
        result = SentimentFeatures.calculate_sentiment_score(
            positive_count=0,
            negative_count=100,
            neutral_count=0
        )
        
        assert result['sentiment_score'] == -1.0
        assert result['bull_bear_ratio'] == 0
    
    def test_sentiment_all_neutral(self):
        """Test with all neutral sentiment."""
        result = SentimentFeatures.calculate_sentiment_score(
            positive_count=0,
            negative_count=0,
            neutral_count=100
        )
        
        assert result['sentiment_score'] == 0
        assert result['sentiment_magnitude'] == 0
        assert result['bull_bear_ratio'] == 1
    
    def test_sentiment_empty(self):
        """Test with no sentiment data."""
        result = SentimentFeatures.calculate_sentiment_score(
            positive_count=0,
            negative_count=0,
            neutral_count=0
        )
        
        assert result['sentiment_score'] == 0
        assert result['sentiment_magnitude'] == 0
        assert result['bull_bear_ratio'] == 1
