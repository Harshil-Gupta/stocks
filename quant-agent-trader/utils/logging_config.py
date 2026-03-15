"""
Enhanced Logging and Observability Module.

Features:
- Structured logging with layer tags
- Log rotation (daily/hourly)
- Performance timing decorators
- API request/response logging
- Error monitoring and alerting
- Module-specific loggers (data, model, signals, execution)

Usage:
    from utils.logging_config import get_logger, LogLayer, log_performance, log_api_request

    logger = get_logger(__name__, LogLayer.DATA)
    logger.info("Fetching data")

    @log_performance(logger)
    def my_function():
        pass
"""

import logging
import sys
import json
import traceback
from typing import Optional, Any, Dict, Callable
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum
from pathlib import Path
import threading
import time
import uuid

from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class LogLayer(Enum):
    """Log layer categories for systematic debugging."""

    DATA = "DATA"
    FEATURE = "FEATURE"
    AGENT = "AGENT"
    SIGNAL = "SIGNAL"
    AGGREGATOR = "AGGREGATOR"
    MODEL = "MODEL"
    BACKTEST = "BACKTEST"
    PORTFOLIO = "PORTFOLIO"
    EXECUTION = "EXECUTION"
    API = "API"
    SYSTEM = "SYSTEM"


class LogLevel(Enum):
    """Custom log levels."""

    PERFORMANCE = 25
    API_REQUEST = 35
    TRADING = 45


logging.addLevelName(LogLevel.PERFORMANCE.value, "PERFORMANCE")
logging.addLevelName(LogLevel.API_REQUEST.value, "API_REQUEST")
logging.addLevelName(LogLevel.TRADING.value, "TRADING")


class StructuredLogger:
    """
    Structured logger with layer tags for debugging.

    Usage:
        logger = get_logger(__name__, LogLayer.AGENT)
        logger.info("Running RSI agent")

        # Output: [AGENT] [INFO] Running RSI agent
    """

    _layer_colors = {
        LogLayer.DATA: "\033[94m",
        LogLayer.FEATURE: "\033[92m",
        LogLayer.AGENT: "\033[93m",
        LogLayer.SIGNAL: "\033[96m",
        LogLayer.AGGREGATOR: "\033[95m",
        LogLayer.MODEL: "\033[96m",
        LogLayer.BACKTEST: "\033[91m",
        LogLayer.PORTFOLIO: "\033[90m",
        LogLayer.EXECUTION: "\033[97m",
        LogLayer.API: "\033[94m",
        LogLayer.SYSTEM: "\033[94m",
    }

    _reset = "\033[0m"

    def __init__(self, logger: logging.Logger, layer: LogLayer, use_color: bool = True):
        self.logger = logger
        self.layer = layer
        self.use_color = use_color and sys.stdout.isatty()

    def _format_message(self, level: str, message: str) -> str:
        layer_tag = f"[{self.layer.value}]"

        if self.use_color:
            color = self._layer_colors.get(self.layer, "")
            return f"{color}{layer_tag}{self._reset} [{level}] {message}"

        return f"{layer_tag} [{level}] {message}"

    def debug(self, message: str, **kwargs):
        self.logger.debug(self._format_message("DEBUG", message), **kwargs)

    def info(self, message: str, **kwargs):
        self.logger.info(self._format_message("INFO", message), **kwargs)

    def warning(self, message: str, **kwargs):
        self.logger.warning(self._format_message("WARNING", message), **kwargs)

    def error(self, message: str, **kwargs):
        self.logger.error(self._format_message("ERROR", message), **kwargs)

    def critical(self, message: str, **kwargs):
        self.logger.critical(self._format_message("CRITICAL", message), **kwargs)

    def exception(self, message: str, **kwargs):
        self.logger.exception(self._format_message("ERROR", message), **kwargs)

    def performance(self, message: str, **kwargs):
        self.logger.log(
            LogLevel.PERFORMANCE.value, self._format_message("PERF", message), **kwargs
        )

    def api_request(self, message: str, **kwargs):
        self.logger.log(
            LogLevel.API_REQUEST.value, self._format_message("API", message), **kwargs
        )

    def trading(self, message: str, **kwargs):
        self.logger.log(
            LogLevel.TRADING.value, self._format_message("TRADE", message), **kwargs
        )


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if self.include_extra:
            extra_fields = {
                k: v
                for k, v in record.__dict__.items()
                if k not in logging.LogRecord("", 0, "", 0, "", (), None).__dict__
            }
            log_data.update(extra_fields)

        return json.dumps(log_data)


def get_logger(
    name: str,
    layer: LogLayer = LogLayer.SYSTEM,
    level: int = logging.INFO,
    use_color: bool = True,
) -> StructuredLogger:
    """Get a structured logger with layer tags."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    return StructuredLogger(logger, layer, use_color)


def configure_logging(
    level: int = logging.INFO,
    log_dir: str = "logs",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 30,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = False,
) -> None:
    """
    Configure global logging with rotation.

    Args:
        level: Global logging level
        log_dir: Directory for log files
        max_bytes: Max size per log file (for RotatingFileHandler)
        backup_count: Number of backup files to keep
        enable_console: Enable console output
        enable_file: Enable file output
        enable_json: Enable JSON formatting
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(message)s", datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    if enable_file:
        app_handler = RotatingFileHandler(
            log_path / "app.log", maxBytes=max_bytes, backupCount=backup_count
        )
        app_handler.setLevel(level)
        app_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        app_handler.setFormatter(app_formatter)
        root_logger.addHandler(app_handler)

        data_handler = RotatingFileHandler(
            log_path / "data.log", maxBytes=max_bytes, backupCount=backup_count
        )
        data_handler.setLevel(level)
        data_handler.setFormatter(app_formatter)
        logging.getLogger("data").addHandler(data_handler)

        signal_handler = RotatingFileHandler(
            log_path / "signals.log", maxBytes=max_bytes, backupCount=backup_count
        )
        signal_handler.setLevel(level)
        signal_handler.setFormatter(app_formatter)
        logging.getLogger("signals").addHandler(signal_handler)

        model_handler = RotatingFileHandler(
            log_path / "models.log", maxBytes=max_bytes, backupCount=backup_count
        )
        model_handler.setLevel(level)
        model_handler.setFormatter(app_formatter)
        logging.getLogger("models").addHandler(model_handler)

        execution_handler = RotatingFileHandler(
            log_path / "execution.log", maxBytes=max_bytes, backupCount=backup_count
        )
        execution_handler.setLevel(level)
        execution_handler.setFormatter(app_formatter)
        logging.getLogger("execution").addHandler(execution_handler)

        error_handler = RotatingFileHandler(
            log_path / "errors.log", maxBytes=max_bytes, backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(app_formatter)
        root_logger.addHandler(error_handler)

        if enable_json:
            json_handler = RotatingFileHandler(
                log_path / "structured.json",
                maxBytes=max_bytes,
                backupCount=backup_count,
            )
            json_handler.setFormatter(JsonFormatter())
            json_handler.setLevel(level)
            root_logger.addHandler(json_handler)


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(
        self, logger: StructuredLogger, operation: str, log_level: str = "info"
    ):
        self.logger = logger
        self.operation = operation
        self.log_level = log_level
        self.start_time = None
        self.result = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        self.logger.debug(f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self.start_time

        if exc_type is None:
            msg = f"{self.operation} completed in {elapsed * 1000:.2f}ms"
            if self.log_level == "performance":
                self.logger.performance(msg)
            else:
                self.logger.info(msg)
        else:
            self.logger.error(
                f"{self.operation} failed after {elapsed * 1000:.2f}ms: {exc_val}"
            )

        return False


def log_performance(logger: StructuredLogger, operation: Optional[str] = None):
    """
    Decorator to log function performance.

    Usage:
        @log_performance(logger, "data_fetch")
        def fetch_data():
            pass
    """

    def decorator(func: Callable) -> Callable:
        op_name = operation or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.performance(f"{op_name} completed in {elapsed * 1000:.2f}ms")
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"{op_name} failed after {elapsed * 1000:.2f}ms: {e}")
                raise

        return wrapper

    return decorator


def log_api_request(logger: StructuredLogger):
    """
    Decorator to log API requests.

    Usage:
        @log_api_request(logger)
        def fetch_market_data():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            request_id = str(uuid.uuid4())[:8]
            start = time.perf_counter()

            logger.api_request(f"[{request_id}] {func.__name__} request started")
            logger.debug(f"[{request_id}] Args: {args}, Kwargs: {kwargs}")

            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.api_request(
                    f"[{request_id}] {func.__name__} completed in {elapsed * 1000:.2f}ms"
                )
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(
                    f"[{request_id}] {func.__name__} failed after {elapsed * 1000:.2f}ms: {e}"
                )
                raise

        return wrapper

    return decorator


class ErrorMonitor:
    """Monitor and track errors."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.error_counts: Dict[str, int] = {}
        self.error_lock = threading.Lock()

    def track_error(self, error_type: str, context: str = ""):
        """Track an error occurrence."""
        with self.error_lock:
            key = f"{error_type}:{context}" if context else error_type
            self.error_counts[key] = self.error_counts.get(key, 0) + 1

            if self.error_counts[key] == 1:
                self.logger.warning(f"First occurrence of {key}")
            elif self.error_counts[key] % 10 == 0:
                self.logger.warning(
                    f"Error {key} occurred {self.error_counts[key]} times"
                )

    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of error counts."""
        with self.error_lock:
            return self.error_counts.copy()

    def reset(self):
        """Reset error counts."""
        with self.error_lock:
            self.error_counts.clear()


def log_exception(logger: StructuredLogger, reraise: bool = True):
    """
    Decorator to log exceptions with full traceback.

    Usage:
        @log_exception(logger)
        def risky_function():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                tb = traceback.format_exc()
                logger.exception(
                    f"{func.__name__} raised {type(e).__name__}: {e}\n{tb}"
                )
                if reraise:
                    raise

        return wrapper

    return decorator


class RequestLogger:
    """Logger for HTTP API requests."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    def log_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        body: Any = None,
    ):
        """Log outgoing request."""
        self.logger.api_request(f"REQUEST: {method} {url}")
        if headers:
            self.logger.debug(f"Headers: {headers}")
        if body:
            self.logger.debug(f"Body: {str(body)[:500]}")

    def log_response(
        self,
        status_code: int,
        url: str,
        elapsed_ms: float,
        body: Any = None,
    ):
        """Log incoming response."""
        level = "info" if status_code < 400 else "error"
        log_fn = getattr(self.logger, level)

        log_fn(f"RESPONSE: {status_code} from {url} in {elapsed_ms:.0f}ms")

        if body and status_code >= 400:
            self.logger.debug(f"Error body: {str(body)[:500]}")


_loggers: Dict[str, StructuredLogger] = {}
_error_monitor: Optional[ErrorMonitor] = None


def get_data_logger() -> StructuredLogger:
    """Get logger for data ingestion."""
    if "data" not in _loggers:
        _loggers["data"] = get_logger("data", LogLayer.DATA)
    return _loggers["data"]


def get_signal_logger() -> StructuredLogger:
    """Get logger for signal generation."""
    if "signals" not in _loggers:
        _loggers["signals"] = get_logger("signals", LogLayer.SIGNAL)
    return _loggers["signals"]


def get_model_logger() -> StructuredLogger:
    """Get logger for model predictions."""
    if "models" not in _loggers:
        _loggers["models"] = get_logger("models", LogLayer.MODEL)
    return _loggers["models"]


def get_execution_logger() -> StructuredLogger:
    """Get logger for execution decisions."""
    if "execution" not in _loggers:
        _loggers["execution"] = get_logger("execution", LogLayer.EXECUTION)
    return _loggers["execution"]


def get_error_monitor(logger: StructuredLogger) -> ErrorMonitor:
    """Get error monitor instance."""
    global _error_monitor
    if _error_monitor is None:
        _error_monitor = ErrorMonitor(logger)
    return _error_monitor


__all__ = [
    "LogLayer",
    "LogLevel",
    "StructuredLogger",
    "get_logger",
    "configure_logging",
    "PerformanceTimer",
    "log_performance",
    "log_api_request",
    "log_exception",
    "ErrorMonitor",
    "RequestLogger",
    "get_data_logger",
    "get_signal_logger",
    "get_model_logger",
    "get_execution_logger",
    "get_error_monitor",
]
