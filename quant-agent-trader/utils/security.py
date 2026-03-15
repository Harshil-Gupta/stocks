"""
Security Utilities Module

Provides security utilities for the trading system:
- Secrets management
- Environment variable enforcement
- Input validation
- Safe deserialization
- API request security
"""

import os
import json
import hashlib
import hmac
import re
from typing import Any, Dict, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Base exception for security-related errors."""

    pass


class MissingSecretError(SecurityError):
    """Raised when a required secret is not configured."""

    pass


class InvalidSecretError(SecurityError):
    """Raised when a secret format is invalid."""

    pass


def get_required_secret(name: str, default: Optional[str] = None) -> str:
    """
    Get a required secret from environment variables.

    Args:
        name: Environment variable name
        default: Default value if not required

    Returns:
        Secret value

    Raises:
        MissingSecretError: If secret is not set and no default provided
    """
    value = os.getenv(name, default)

    if value is None or value == "":
        raise MissingSecretError(
            f"Required secret '{name}' is not configured. "
            f"Please set it in your .env file."
        )

    return value


def get_optional_secret(name: str, default: str = "") -> str:
    """
    Get an optional secret from environment variables.

    Args:
        name: Environment variable name
        default: Default value if not set

    Returns:
        Secret value or default
    """
    return os.getenv(name, default)


def validate_api_key(api_key: str, name: str = "API key") -> bool:
    """
    Validate API key format.

    Args:
        api_key: API key to validate
        name: Name for error messages

    Returns:
        True if valid

    Raises:
        InvalidSecretError: If API key format is invalid
    """
    if not api_key:
        return False

    # Basic validation - ensure it's not obviously fake
    if len(api_key) < 8:
        raise InvalidSecretError(
            f"{name} appears to be too short (minimum 8 characters)"
        )

    # Check for common placeholder patterns
    placeholder_patterns = [
        r"^your_.*",
        r"^<.*>",
        r"^placeholder",
        r"^test_",
    ]

    for pattern in placeholder_patterns:
        if re.match(pattern, api_key, re.IGNORECASE):
            raise InvalidSecretError(
                f"{name} appears to be a placeholder. Please configure a valid key."
            )

    return True


def validate_access_token(token: str) -> bool:
    """
    Validate access token format.

    Args:
        token: Access token to validate

    Returns:
        True if valid
    """
    if not token or len(token) < 10:
        return False

    # Tokens should not contain spaces or special chars that could indicate injection
    if not re.match(r"^[A-Za-z0-9_-]+$", token):
        return False

    return True


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """
    Mask a secret for safe logging.

    Args:
        secret: Secret to mask
        visible_chars: Number of characters to show at the end

    Returns:
        Masked secret
    """
    if not secret:
        return "***"

    if len(secret) <= visible_chars:
        return "*" * len(secret)

    return secret[:visible_chars] + "*" * (len(secret) - visible_chars)


def hash_secret(secret: str, salt: Optional[str] = None) -> str:
    """
    Hash a secret for storage/comparison.

    Args:
        secret: Secret to hash
        salt: Optional salt (uses env var SALT if not provided)

    Returns:
        Hashed secret
    """
    if salt is None:
        salt = os.getenv("APP_SECRET_SALT", "default_salt_change_me")

    return hashlib.pbkdf2_hmac(
        "sha256", secret.encode("utf-8"), salt.encode("utf-8"), 100000
    ).hex()


def verify_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify HMAC signature.

    Args:
        payload: Payload that was signed
        signature: Signature to verify
        secret: Secret key used for signing

    Returns:
        True if signature is valid
    """
    expected = hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


class SecretManager:
    """
    Centralized secrets management.

    Loads and validates secrets from environment variables.
    """

    REQUIRED_SECRETS: List[str] = []
    OPTIONAL_SECRETS: List[str] = []

    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._validated = False

    def load_secrets(self) -> Dict[str, str]:
        """
        Load all configured secrets.

        Returns:
            Dictionary of secret names to values
        """
        if self._secrets:
            return self._secrets

        # Load required secrets
        for name in self.REQUIRED_SECRETS:
            try:
                self._secrets[name] = get_required_secret(name)
            except MissingSecretError as e:
                logger.warning(f"Required secret not configured: {name}")
                if os.getenv("STRICT_MODE", "").lower() == "true":
                    raise

        # Load optional secrets
        for name in self.OPTIONAL_SECRETS:
            value = get_optional_secret(name)
            if value:
                self._secrets[name] = value

        self._validated = True
        return self._secrets

    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret by name.

        Args:
            name: Secret name
            default: Default value if not found

        Returns:
            Secret value or default
        """
        if not self._validated:
            self.load_secrets()

        return self._secrets.get(name, default)

    def validate_all(self) -> List[str]:
        """
        Validate all required secrets.

        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []

        for name in self.REQUIRED_SECRETS:
            try:
                value = get_required_secret(name)
                # Add specific validation based on secret type
                if "API_KEY" in name or "API_SECRET" in name:
                    validate_api_key(value, name)
                elif "ACCESS_TOKEN" in name or "TOKEN" in name:
                    if not validate_access_token(value):
                        errors.append(f"Invalid token format: {name}")
            except MissingSecretError:
                errors.append(f"Missing required secret: {name}")
            except InvalidSecretError as e:
                errors.append(str(e))

        return errors


class SafeUnpickler:
    """
    Safe pickle deserialization with allowlist.
    """

    ALLOWED_MODELS: List[str] = [
        "sklearn",
        "lightgbm",
        "xgboost",
        "numpy",
        "pandas",
    ]

    @classmethod
    def safe_load(cls, data: bytes, expected_class: Optional[str] = None) -> Any:
        """
        Safely unpickle data with class validation.

        Args:
            data: Pickled data bytes
            expected_class: Expected class name (optional)

        Returns:
            Unpickled object

        Raises:
            SecurityError: If deserialization is unsafe
        """
        import pickle

        # Create a restricted unpickler
        class RestrictedUnpickler(pickle.Unpickler):
            def find_class(self, module: str, name: str):
                # Check if module is in allowlist
                module_base = module.split(".")[0]

                if module_base not in cls.ALLOWED_MODELS:
                    # Allow internal classes
                    if not module.startswith("_"):
                        logger.warning(
                            f"Pickle: Blocking access to module {module}.{name}"
                        )
                    raise SecurityError(f"Unsafe pickle: module '{module}' not allowed")

                return super().find_class(module, name)

        import io

        unpickler = RestrictedUnpickler(io.BytesIO(data))
        return unpickler.load()


def sanitize_path(path: str, base_dir: Optional[str] = None) -> Path:
    """
    Sanitize and validate file path to prevent path traversal.

    Args:
        path: File path to sanitize
        base_dir: Base directory to restrict access to

    Returns:
        Sanitized Path object

    Raises:
        SecurityError: If path is unsafe
    """
    # Resolve the path and check for traversal
    path_obj = Path(path).resolve()

    if base_dir:
        base_obj = Path(base_dir).resolve()

        # Ensure path is within base directory
        try:
            path_obj.relative_to(base_obj)
        except ValueError:
            raise SecurityError(
                f"Path traversal attempt detected: {path} is outside {base_dir}"
            )

    # Check for dangerous patterns
    dangerous_patterns = ["../", "..\\", "~/", "~/"]
    for pattern in dangerous_patterns:
        if pattern in str(path_obj):
            raise SecurityError(f"Dangerous path pattern detected: {pattern}")

    return path_obj


def validate_symbol(symbol: str) -> bool:
    """
    Validate stock symbol to prevent injection.

    Args:
        symbol: Stock symbol to validate

    Returns:
        True if valid
    """
    if not symbol or not isinstance(symbol, str):
        return False

    # Only allow alphanumeric and common separators
    if not re.match(r"^[A-Za-z0-9._-]+$", symbol):
        return False

    # Check for path traversal
    if ".." in symbol or "/" in symbol or "\\" in symbol:
        return False

    # Limit length
    if len(symbol) > 20:
        return False

    return True


def validate_date_string(date_str: str) -> bool:
    """
    Validate date string format.

    Args:
        date_str: Date string to validate

    Returns:
        True if valid
    """
    from datetime import datetime

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# Default secret manager for the application
secrets_manager = SecretManager()


__all__ = [
    "SecurityError",
    "MissingSecretError",
    "InvalidSecretError",
    "get_required_secret",
    "get_optional_secret",
    "validate_api_key",
    "validate_access_token",
    "mask_secret",
    "hash_secret",
    "verify_signature",
    "SecretManager",
    "SafeUnpickler",
    "sanitize_path",
    "validate_symbol",
    "validate_date_string",
    "secrets_manager",
]
