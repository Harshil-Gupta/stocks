"""
Test Utilities Module

Provides utility functions and helpers for writing tests.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime


def load_json_fixture(fixture_name: str) -> Dict[str, Any]:
    """
    Load a JSON fixture file.
    
    Args:
        fixture_name: Name of the fixture file (without .json extension)
        
    Returns:
        Dictionary containing fixture data
    """
    fixture_path = Path(__file__).parent / 'fixtures' / f'{fixture_name}.json'
    
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")
    
    with open(fixture_path, 'r') as f:
        return json.load(f)


def compare_signals(signal1: Dict[str, Any], signal2: Dict[str, Any]) -> bool:
    """
    Compare two signals for equality.
    
    Args:
        signal1: First signal dictionary
        signal2: Second signal dictionary
        
    Returns:
        True if signals are equal
    """
    ignore_keys = {'timestamp'}
    
    for key in set(signal1.keys()) | set(signal2.keys()):
        if key in ignore_keys:
            continue
        
        if key not in signal1 or key not in signal2:
            return False
        
        if isinstance(signal1[key], float) and isinstance(signal2[key], float):
            if abs(signal1[key] - signal2[key]) > 1e-6:
                return False
        elif signal1[key] != signal2[key]:
            return False
    
    return True


def create_mock_response(
    status_code: int = 200,
    json_data: Dict[str, Any] = None,
    text: str = '',
) -> Dict[str, Any]:
    """
    Create a mock HTTP response.
    
    Args:
        status_code: HTTP status code
        json_data: JSON response data
        text: Text response
        
    Returns:
        Mock response dictionary
    """
    return {
        'status_code': status_code,
        'json': json_data if json_data else lambda: json_data,
        'text': text,
        'ok': status_code >= 200 and status_code < 300,
    }


__all__ = [
    'load_json_fixture',
    'compare_signals',
    'create_mock_response',
]
