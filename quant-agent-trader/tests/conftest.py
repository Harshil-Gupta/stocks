"""
Pytest Configuration and Shared Fixtures

This module provides shared fixtures and configuration for all tests.
"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests that require API calls"
    )


# ============================================================================
# Fixtures: Sample Data
# ============================================================================

@pytest.fixture
def sample_price_data() -> pd.DataFrame:
    """Generate sample OHLCV data for testing."""
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


@pytest.fixture
def sample_features() -> Dict[str, Any]:
    """Sample features dictionary for agent testing."""
    return {
        'close': 1550.0,
        'open': 1540.0,
        'high': 1560.0,
        'low': 1530.0,
        'volume': 5000000,
        'returns': 0.0125,
        'rsi': 65.0,
        'macd': 15.5,
        'macd_signal': 12.0,
        'macd_hist': 3.5,
        'sma_20': 1520.0,
        'sma_50': 1500.0,
        'sma_200': 1480.0,
        'bb_upper': 1580.0,
        'bb_middle': 1540.0,
        'bb_lower': 1500.0,
        'bb_position': 0.65,
        'atr': 25.0,
        'volume_sma_20': 4500000,
        'volume_ratio': 1.11,
        'momentum_5': 0.025,
        'momentum_20': 0.055,
        'volatility_20': 0.018,
        'trend_strength': 0.015,
        'stoch_k': 72.5,
        'stoch_d': 68.0,
        'price_position_20': 0.7,
        'price_position_50': 0.65,
    }


@pytest.fixture
def sample_features_oversold() -> Dict[str, Any]:
    """Sample features with oversold RSI for testing."""
    return {
        'close': 1480.0,
        'open': 1490.0,
        'high': 1500.0,
        'low': 1470.0,
        'volume': 3000000,
        'rsi': 28.0,
        'atr': 30.0,
        'price_position_20': 0.25,
    }


@pytest.fixture
def sample_features_overbought() -> Dict[str, Any]:
    """Sample features with overbought RSI for testing."""
    return {
        'close': 1620.0,
        'open': 1610.0,
        'high': 1630.0,
        'low': 1600.0,
        'volume': 7000000,
        'rsi': 78.0,
        'atr': 28.0,
        'price_position_20': 0.85,
    }


@pytest.fixture
def mock_agent_signals() -> List[Dict[str, Any]]:
    """Sample agent signals for aggregation testing."""
    return [
        {
            'agent_name': 'rsi_agent',
            'agent_category': 'technical',
            'signal': 'buy',
            'confidence': 75.0,
            'numerical_score': -0.8,
        },
        {
            'agent_name': 'macd_agent',
            'agent_category': 'technical',
            'signal': 'buy',
            'confidence': 70.0,
            'numerical_score': -0.6,
        },
        {
            'agent_name': 'valuation_agent',
            'agent_category': 'fundamental',
            'signal': 'hold',
            'confidence': 60.0,
            'numerical_score': 0.1,
        },
    ]


@pytest.fixture
def mock_nse_quote_response() -> Dict[str, Any]:
    """Mock NSE API quote response."""
    return {
        'info': {'companyName': 'Reliance Industries Ltd'},
        'priceInfo': {
            'lastPrice': 2950.50,
            'open': 2930.00,
            'previousClose': 2945.25,
            'intraDayHighLow': {'max': 2965.00, 'min': 2920.00},
            'vwap': 2945.80,
            'weekHighLow': {'max': 3200.00, 'min': 2400.00},
            'totalVolume': 8500000,
            'totalValue': 25000000000,
        },
        'metadata': {
            'pdSymbolPe': 28.5,
            'marketCap': 1990000000000,
            'ffmc': 980000000000,
            'isin': 'INE002A01018',
            'faceValue': 10.0,
            'bookValue': 850.0,
            'divYield': 0.35,
            'eps': 103.50,
        },
        'industryInfo': {
            'sector': 'Oil & Gas',
            'industry': 'Oil & Gas - Refining & Marketing',
        },
    }


@pytest.fixture
def mock_rbi_macro_response() -> Dict[str, Any]:
    """Mock RBI macro data response."""
    return {
        'policy_rates': {
            'repo_rate': 6.50,
            'reverse_repo_rate': 3.35,
            'marginal_standing_facility': 6.75,
            'bank_rate': 6.75,
            'cash_reserve_ratio': 4.50,
            'statutory_liquidity_ratio': 18.00,
        },
        'inflation': {
            'cpi_consumer': {'current': 4.85, 'previous': 5.10},
        },
    }


# ============================================================================
# Fixtures: Test Data Factories
# ============================================================================

class SignalFactory:
    """Factory for creating test signal data."""
    
    @staticmethod
    def create_signal(
        agent_name: str = 'test_agent',
        agent_category: str = 'technical',
        signal: str = 'hold',
        confidence: float = 50.0,
        numerical_score: float = 0.0,
    ) -> Dict[str, Any]:
        """Create a test signal dictionary."""
        return {
            'agent_name': agent_name,
            'agent_category': agent_category,
            'signal': signal,
            'confidence': confidence,
            'numerical_score': numerical_score,
            'reasoning': f'Test signal from {agent_name}',
            'supporting_data': {},
            'timestamp': datetime.now().isoformat(),
        }
    
    @staticmethod
    def create_buy_signal(
        agent_name: str = 'test_agent',
        confidence: float = 75.0,
    ) -> Dict[str, Any]:
        """Create a buy signal."""
        return SignalFactory.create_signal(
            agent_name=agent_name,
            signal='buy',
            confidence=confidence,
            numerical_score=-0.5,
        )
    
    @staticmethod
    def create_sell_signal(
        agent_name: str = 'test_agent',
        confidence: float = 75.0,
    ) -> Dict[str, Any]:
        """Create a sell signal."""
        return SignalFactory.create_signal(
            agent_name=agent_name,
            signal='sell',
            confidence=confidence,
            numerical_score=0.5,
        )
    
    @staticmethod
    def create_hold_signal(
        agent_name: str = 'test_agent',
        confidence: float = 50.0,
    ) -> Dict[str, Any]:
        """Create a hold signal."""
        return SignalFactory.create_signal(
            agent_name=agent_name,
            signal='hold',
            confidence=confidence,
            numerical_score=0.0,
        )


class PriceDataFactory:
    """Factory for creating test price data."""
    
    @staticmethod
    def create_ohlcv(
        n_periods: int = 100,
        start_price: float = 1000.0,
        volatility: float = 0.02,
    ) -> pd.DataFrame:
        """Create OHLCV data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=n_periods, freq='D')
        
        np.random.seed(42)
        returns = np.random.randn(n_periods) * volatility
        prices = start_price * np.exp(np.cumsum(returns))
        
        return pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.randn(n_periods) * 0.005),
            'high': prices * (1 + np.abs(np.random.randn(n_periods) * 0.01)),
            'low': prices * (1 - np.abs(np.random.randn(n_periods) * 0.01)),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, n_periods),
        })


# ============================================================================
# Fixtures: Mock Objects
# ============================================================================

@pytest.fixture
def mock_session():
    """Create a mock requests session."""
    session = Mock()
    session.get = Mock()
    session.post = Mock()
    session.cookies = {}
    return session


@pytest.fixture
def mock_aiohttp_session():
    """Create a mock aiohttp session."""
    session = AsyncMock()
    session.get = AsyncMock()
    session.close = AsyncMock()
    return session


# ============================================================================
# Fixtures: Configuration
# ============================================================================

@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        'cache_ttl': 60,
        'max_retries': 2,
        'timeout': 10,
        'enable_logging': False,
    }


# ============================================================================
# Fixtures: Sample Symbols
# ============================================================================

@pytest.fixture
def sample_nse_symbols() -> List[str]:
    """Sample NSE symbols for testing."""
    return [
        'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR',
        'ICICIBANK', 'SBIN', 'BHARTIARTL', 'KOTAKBANK', 'LT',
    ]


@pytest.fixture
def sample_fno_symbols() -> List[str]:
    """Sample F&O symbols for testing."""
    return [
        'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
        'KOTAKBANK', 'LT', 'HINDUNILVR', 'SBIN', 'BAJFINANCE',
    ]


# ============================================================================
# Fixtures: Portfolio Test Data
# ============================================================================

@pytest.fixture
def sample_portfolio_state() -> Dict[str, Any]:
    """Sample portfolio state for testing."""
    return {
        'cash': 100000.0,
        'positions': {
            'RELIANCE': {
                'entry_price': 2900.0,
                'current_price': 2950.0,
                'quantity': 100,
                'unrealized_pnl': 5000.0,
            },
            'TCS': {
                'entry_price': 3800.0,
                'current_price': 3750.0,
                'quantity': 50,
                'unrealized_pnl': -2500.0,
            },
        },
    }


@pytest.fixture
def sample_aggregated_signal() -> Dict[str, Any]:
    """Sample aggregated signal for portfolio testing."""
    return {
        'stock_symbol': 'RELIANCE',
        'final_score': 0.7,
        'decision': 'buy',
        'confidence': 75.0,
        'supporting_agents': ['rsi_agent', 'macd_agent'],
        'conflicting_agents': [],
        'regime': 'bull',
    }


# ============================================================================
# Test Utilities
# ============================================================================

def assert_signal_valid(signal_dict: Dict[str, Any]) -> None:
    """Validate signal dictionary structure."""
    required_fields = ['agent_name', 'agent_category', 'signal', 'confidence']
    
    for field in required_fields:
        assert field in signal_dict, f"Missing required field: {field}"
    
    assert signal_dict['signal'] in ['buy', 'sell', 'hold'], "Invalid signal type"
    assert 0 <= signal_dict['confidence'] <= 100, "Confidence must be between 0 and 100"


def assert_features_valid(features: Dict[str, Any], required_keys: List[str]) -> None:
    """Validate features dictionary has required keys."""
    for key in required_keys:
        assert key in features, f"Missing required feature: {key}"


# Export factories for use in tests
__all__ = [
    'SignalFactory',
    'PriceDataFactory',
    'assert_signal_valid',
    'assert_features_valid',
]
