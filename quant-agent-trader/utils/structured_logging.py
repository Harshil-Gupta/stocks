"""
Structured Logging - Layer-tagged logging for systematic debugging.

Adds layer prefixes to log messages for easier debugging:
    [DATA] fetching market data
    [FEATURE] computing indicators
    [AGENT] running rsi_agent
    [AGGREGATOR] computing final signal
    [META] ML model prediction
    [BACKTEST] backtest iteration
    [PORTFOLIO] position sizing
    [EXECUTION] order execution
"""

import logging
import sys
from typing import Optional
from datetime import datetime
from enum import Enum


class LogLayer(Enum):
    """Log layer categories for systematic debugging."""
    DATA = "DATA"
    FEATURE = "FEATURE"
    AGENT = "AGENT"
    AGGREGATOR = "AGGREGATOR"
    META = "META"
    BACKTEST = "BACKTEST"
    PORTFOLIO = "PORTFOLIO"
    EXECUTION = "EXECUTION"
    SYSTEM = "SYSTEM"


class StructuredLogger:
    """
    Structured logger with layer tags for debugging.
    
    Usage:
        logger = get_logger(__name__, LogLayer.AGENT)
        logger.info("Running RSI agent")
        
        # Output: [AGENT] [INFO] Running RSI agent
    """
    
    _layer_colors = {
        LogLayer.DATA: "\033[94m",       # Blue
        LogLayer.FEATURE: "\033[92m",    # Green
        LogLayer.AGENT: "\033[93m",      # Yellow
        LogLayer.AGGREGATOR: "\033[95m", # Magenta
        LogLayer.META: "\033[96m",       # Cyan
        LogLayer.BACKTEST: "\033[91m",   # Red
        LogLayer.PORTFOLIO: "\033[90m",  # Gray
        LogLayer.EXECUTION: "\033[97m",  # White
        LogLayer.SYSTEM: "\033[94m",     # Blue
    }
    
    _reset = "\033[0m"
    
    def __init__(self, logger: logging.Logger, layer: LogLayer, use_color: bool = True):
        self.logger = logger
        self.layer = layer
        self.use_color = use_color and sys.stdout.isatty()
    
    def _format_message(self, level: str, message: str) -> str:
        """Format message with layer tag."""
        layer_tag = f"[{self.layer.value}]"
        
        if self.use_color:
            color = self._layer_colors.get(self.layer, "")
            return f"{color}{layer_tag}{self._reset} [{level}] {message}"
        
        return f"{layer_tag} [{level}] {message}"
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(self._format_message("DEBUG", message), **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(self._format_message("INFO", message), **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(self._format_message("WARNING", message), **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(self._format_message("ERROR", message), **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(self._format_message("CRITICAL", message), **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(self._format_message("ERROR", message), **kwargs)


def get_logger(
    name: str, 
    layer: LogLayer = LogLayer.SYSTEM,
    level: int = logging.INFO,
    use_color: bool = True
) -> StructuredLogger:
    """
    Get a structured logger with layer tags.
    
    Args:
        name: Logger name (typically __name__)
        layer: Log layer for this logger
        level: Logging level
        use_color: Whether to use colored output
        
    Returns:
        StructuredLogger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(level)
    
    return StructuredLogger(logger, layer, use_color)


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    use_color: bool = True
) -> None:
    """
    Configure global logging for the system.
    
    Args:
        level: Global logging level
        log_file: Optional file path for logging
        use_color: Whether to use colored output in console
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    root_logger.handlers.clear()
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if use_color and sys.stdout.isatty():
        console_formatter = logging.Formatter(
            '%(asctime)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


class LayerContext:
    """
    Context manager for temporary layer switching.
    
    Usage:
        logger = get_logger(__name__, LogLayer.AGENT)
        
        with LayerContext(logger, LogLayer.META):
            logger.info("Inside meta layer")
    """
    
    def __init__(self, logger: StructuredLogger, new_layer: LogLayer):
        self.logger = logger
        self.new_layer = new_layer
        self.old_layer = None
    
    def __enter__(self):
        self.old_layer = self.logger.layer
        self.logger.layer = self.new_layer
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.layer = self.old_layer


class DebugTimer:
    """
    Context manager for timing operations.
    
    Usage:
        logger = get_logger(__name__, LogLayer.AGENT)
        
        with DebugTimer(logger, "compute_rsi"):
            # do work
            pass
        # Logs: [AGENT] [INFO] compute_rsi completed in 0.023s
    """
    
    def __init__(self, logger: StructuredLogger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if exc_type is None:
            self.logger.debug(f"{self.operation} completed in {elapsed:.3f}s")
        else:
            self.logger.error(f"{self.operation} failed after {elapsed:.3f}s")


def log_function_call(logger: StructuredLogger):
    """
    Decorator to log function calls.
    
    Usage:
        @log_function_call(logger)
        def my_function(a, b):
            return a + b
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} returned {type(result)}")
                return result
            except Exception as e:
                logger.exception(f"{func.__name__} raised {type(e).__name__}: {e}")
                raise
        return wrapper
    return decorator
