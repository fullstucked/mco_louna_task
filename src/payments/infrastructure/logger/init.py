import logging
import sys

import structlog


def setup_logging(
    level: str,
    env: str,
) -> None:
    """
    Configure structlog for JSON logging with context support.
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        env: Deployment environment (DEV, STAGE, PROD)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Processors common to all environments
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Environment-specific rendering
    # if env == "DEV": TODO FIX
    #     shared_processors.append(structlog.dev.ConsoleRenderer(colors=True))
    # else:
    #     shared_processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=shared_processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )

    # Configure root stdlib logger with handler
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Add handler to root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(log_level)
    root_logger.addHandler(handler)
