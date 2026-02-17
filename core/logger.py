"""
Structured logging for AegisRAG.
Provides JSON logging for production, human-readable for development.
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class HumanFormatter(logging.Formatter):
    """Format logs as human-readable text."""

    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[41m",   # Red background
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]

        log_msg = f"{color}[{record.levelname}]{reset} {record.getMessage()}"

        # Add module info
        if record.module:
            log_msg += f" ({record.module}:{record.funcName}:{record.lineno})"

        # Add exception if present
        if record.exc_info:
            log_msg += f"\n{self.formatException(record.exc_info)}"

        return log_msg


def setup_logging(
    name: str = "aegisrag",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    use_json: bool = False,
) -> logging.Logger:
    """
    Configure logging for AegisRAG.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging
        use_json: Use JSON formatting (for production)

    Returns:
        Configured logger instance
    """

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    formatter = (
        JSONFormatter() if use_json else HumanFormatter()
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = None


def get_logger(name: str = __name__) -> logging.Logger:
    """Get or create the global logger."""
    global logger
    if logger is None:
        from config.settings import settings
        logger = setup_logging(
            name="aegisrag",
            level=settings.LOG_LEVEL,
            log_file=settings.LOG_FILE_PATH,
            use_json=not settings.DEBUG,
        )
    return logger
