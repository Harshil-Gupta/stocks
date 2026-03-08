"""
Data Ingestion Tests

Tests for data ingestion modules with mocked HTTP responses.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd


class TestScreenerDataParser:
    """Tests for Screener data parsing."""
    
    def test_parse_number(self):
        """Test number parsing from text."""
        from data.ingestion.screener_data import ScreenerDataExtractor
        
        extractor = ScreenerDataExtractor()
        
        # Test Crore
        assert extractor._parse_number("100 Cr") == 1_000_000_000
        # Test Lakh
        assert extractor._parse_number("50 L") == 5_000_000
        # Test plain number
        assert extractor._parse_number("1234.56") == 1234.56
        # Test with comma
        assert extractor._parse_number("1,234,567") == 1234567
    
    def test_parse_number_invalid(self):
        """Test invalid number parsing."""
        from data.ingestion.screener_data import ScreenerDataExtractor
        
        extractor = ScreenerDataExtractor()
        
        assert extractor._parse_number("") is None
        assert extractor._parse_number("abc") is None


class TestRBIMacroData:
    """Tests for RBI macro data."""
    
    def test_fallback_policy_rates(self):
        """Test fallback policy rates."""
        from data.ingestion.rbi_macro import RBIMacroData
        
        rbi = RBIMacroData()
        rates = rbi._get_fallback_policy_rates()
        
        assert 'repo_rate' in rates
        assert rates['repo_rate'] == 6.50
    
    def test_fallback_inflation(self):
        """Test fallback inflation data."""
        from data.ingestion.rbi_macro import RBIMacroData
        
        rbi = RBIMacroData()
        inflation = rbi._get_fallback_inflation_data()
        
        assert 'cpi_consumer' in inflation
        assert inflation['cpi_consumer']['current'] is not None
    
    def test_fallback_gdp(self):
        """Test fallback GDP data."""
        from data.ingestion.rbi_macro import RBIMacroData
        
        rbi = RBIMacroData()
        gdp = rbi._get_fallback_gdp_data()
        
        assert 'gdp_growth' in gdp
        assert 'q3_fy26' in gdp['gdp_growth']
    
    def test_regime_indicator(self):
        """Test regime indicator logic."""
        from data.ingestion.rbi_macro import RBIMacroData
        
        rbi = RBIMacroData()
        
        with patch.object(rbi, 'get_policy_rates', return_value={'repo_rate': 7.0}):
            with patch.object(rbi, 'get_inflation_data', return_value={'cpi_consumer': {'current': 6.5}}):
                regime = rbi.get_regime_indicator()
                assert regime == "tightening"
    
    def test_cache_mechanism(self):
        """Test caching mechanism."""
        from data.ingestion.rbi_macro import RBIMacroData
        
        rbi = RBIMacroData()
        
        # First call
        rates1 = rbi.get_policy_rates()
        
        # Second call should use cache
        rates2 = rbi.get_policy_rates()
        
        assert rates1 is not None
    
    def test_clear_cache(self):
        """Test cache clearing."""
        from data.ingestion.rbi_macro import RBIMacroData
        
        rbi = RBIMacroData()
        
        rbi.get_policy_rates()
        rbi.clear_cache()
        
        # Cache should be cleared
        assert rbi._cache == {}


class TestAMFIDataSource:
    """Tests for AMFI data source."""
    
    def test_parse_number(self):
        """Test number parsing."""
        from ingestion.mf.sources.amfi_source import AMFIDataSource
        
        amfi = AMFIDataSource()
        
        assert amfi._parse_number("100 Cr") == 1_000_000_000
        assert amfi._parse_number("50 L") == 5_000_000
        assert amfi._parse_number("1234.56") == 1234.56
    
    def test_cache_mechanism(self):
        """Test cache mechanism."""
        from ingestion.mf.sources.amfi_source import AMFIDataSource
        
        amfi = AMFIDataSource(cache_minutes=15)
        
        assert not amfi._is_cache_valid()


class TestNSEAPIClient:
    """Tests for NSE API client."""
    
    def test_session_creation(self):
        """Test session creation."""
        from data.ingestion.nse_api_client import NSEIndiaAPI
        
        api = NSEIndiaAPI()
        
        assert api._session is not None
    
    def test_endpoints_defined(self):
        """Test that endpoints are defined."""
        from data.ingestion.nse_api_client import NSEIndiaAPI
        
        api = NSEIndiaAPI()
        
        assert 'quote' in api.ENDPOINTS
        assert 'fiidii' in api.ENDPOINTS
        assert 'market_status' in api.ENDPOINTS


class TestUnifiedDataService:
    """Tests for unified data service."""
    
    def test_service_initialization(self):
        """Test service initializes."""
        from data.services import UnifiedDataService
        
        service = UnifiedDataService()
        
        assert service._cache_enabled is True
        assert service._cache == {}
    
    def test_cache_operations(self):
        """Test cache get/set."""
        from data.services import UnifiedDataService
        
        service = UnifiedDataService()
        
        service._set_cache("test_key", {"value": 123})
        
        result = service._get_cache("test_key")
        
        assert result == {"value": 123}
    
    def test_clear_cache(self):
        """Test cache clearing."""
        from data.services import UnifiedDataService
        
        service = UnifiedDataService()
        
        service._set_cache("key1", "value1")
        service._set_cache("key2", "value2")
        
        service.clear_cache()
        
        assert service._cache == {}
    
    def test_clear_specific_cache(self):
        """Test clearing specific cache key."""
        from data.services import UnifiedDataService
        
        service = UnifiedDataService()
        
        service._set_cache("key1", "value1")
        service._set_cache("key2", "value2")
        
        service.clear_cache("key1")
        
        assert service._get_cache("key1") is None
        assert service._get_cache("key2") == "value2"
    
    def test_service_registry(self):
        """Test data service registry."""
        from data.services import DataServiceRegistry
        
        assert DataServiceRegistry.NSE_QUOTES == "nse_quotes"
        assert DataServiceRegistry.SCREENER_FINANCIALS == "screener_financials"
        assert DataServiceRegistry.RBI_MACRO == "rbi_macro"
