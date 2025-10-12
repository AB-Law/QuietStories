"""
Centralized logging configuration for QuietStories

Provides different logging levels and formats for better debugging:
- DEBUG: Detailed information for diagnosing problems
- INFO: General informational messages
- WARNING: Warning messages for potentially problematic situations
- ERROR: Error messages for serious problems
- CRITICAL: Critical messages for very serious errors

Usage:
    from backend.utils.logger import get_logger, setup_logging
    
    # Setup logging at application start
    setup_logging(level="INFO")  # or "DEBUG", "WARNING", "ERROR"
    
    # In your module
    logger = get_logger(__name__)
    logger.info("This is an info message")
    logger.debug("This is a debug message")
"""

import logging
import sys
from typing import Literal, Optional
from pathlib import Path
from datetime import datetime

# Color codes for terminal output
COLORS = {
    'DEBUG': '\033[36m',      # Cyan
    'INFO': '\033[32m',       # Green
    'WARNING': '\033[33m',    # Yellow
    'ERROR': '\033[31m',      # Red
    'CRITICAL': '\033[35m',   # Magenta
    'RESET': '\033[0m'        # Reset
}

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels"""
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in COLORS:
            record.levelname = f"{COLORS[levelname]}{levelname}{COLORS['RESET']}"
        
        # Add color to logger name
        record.name = f"\033[94m{record.name}\033[0m"  # Blue
        
        return super().format(record)


def setup_logging(
    level: LogLevel = "INFO",
    log_file: Optional[str] = None,
    enable_colors: bool = True,
    include_timestamp: bool = True
) -> None:
    """
    Setup logging configuration for the application
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If provided, logs will be written to file
        enable_colors: Whether to enable colored output for console
        include_timestamp: Whether to include timestamp in log messages
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatters
    if include_timestamp:
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
    else:
        fmt = "%(levelname)-8s | %(name)s | %(message)s"
        datefmt = None
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if enable_colors and sys.stdout.isatty():
        console_formatter = ColoredFormatter(fmt, datefmt=datefmt)
    else:
        console_formatter = logging.Formatter(fmt, datefmt=datefmt)
    
    console_handler.setFormatter(console_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Add console handler
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        
        # File logs don't need colors
        file_formatter = logging.Formatter(fmt, datefmt=datefmt)
        file_handler.setFormatter(file_formatter)
        
        root_logger.addHandler(file_handler)
    
    # Silence noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    root_logger.info(f"Logging initialized at {level} level")
    if log_file:
        root_logger.info(f"Logging to file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module
    
    Args:
        name: Name of the logger (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Context manager for temporary log level changes
class LogLevelContext:
    """Context manager to temporarily change logging level"""
    
    def __init__(self, level: LogLevel):
        self.level = getattr(logging, level.upper())
        self.old_level = None
    
    def __enter__(self):
        self.old_level = logging.getLogger().level
        logging.getLogger().setLevel(self.level)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.getLogger().setLevel(self.old_level)


def set_module_level(module_name: str, level: LogLevel) -> None:
    """
    Set logging level for a specific module
    
    Args:
        module_name: Name of the module (e.g., 'src.api.scenarios')
        level: Logging level to set
    """
    numeric_level = getattr(logging, level.upper())
    logging.getLogger(module_name).setLevel(numeric_level)


# Convenience function for logging function entry/exit
def log_function_call(logger: logging.Logger):
    """
    Decorator to log function entry and exit
    
    Usage:
        @log_function_call(logger)
        def my_function(arg1, arg2):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"Entering {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Exiting {func.__name__} with result={result}")
                return result
            except Exception as e:
                logger.error(f"Exception in {func.__name__}: {e}", exc_info=True)
                raise
        return wrapper
    return decorator
