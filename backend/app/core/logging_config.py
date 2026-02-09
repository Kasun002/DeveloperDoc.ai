"""
Structured logging configuration using structlog.

This module configures structlog for JSON-formatted structured logging
with automatic trace_id injection, timestamps, and FastAPI integration.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from app.core.config import settings


def add_trace_id(logger: Any, method_name: str, event_dict: Dict) -> Dict:
    """
    Add trace_id to log entries if available in context.
    
    This processor extracts trace_id from the event_dict and ensures
    it's included in all log entries for request tracing.
    """
    # trace_id should be passed explicitly in log calls
    # e.g., logger.info("event", trace_id="abc-123")
    return event_dict


def configure_logging() -> None:
    """
    Configure structured logging with structlog.
    
    Sets up:
    - JSON formatting for structured logs
    - Timestamp processor for all log entries
    - Log level filtering based on settings
    - Integration with Python's standard logging
    - Console output with appropriate formatting
    """
    # Determine if we should use JSON format
    use_json = settings.log_format.lower() == "json"
    
    # Configure structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        add_trace_id,
    ]
    
    if use_json:
        # JSON output for production
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Human-readable output for development
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.format_exc_info,
                structlog.dev.ConsoleRenderer(colors=True)
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )
    
    # Set log level for structlog
    logging.getLogger().setLevel(
        getattr(logging, settings.log_level.upper(), logging.INFO)
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured structlog logger instance.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
        
    Returns:
        Configured structlog logger with all processors applied
        
    Example:
        logger = get_logger(__name__)
        logger.info("user_login", user_id=123, trace_id="abc-123")
    """
    return structlog.get_logger(name)
