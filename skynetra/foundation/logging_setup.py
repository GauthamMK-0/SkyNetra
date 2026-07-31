"""
Foundation layer (L0) — logging configuration.

May import from: itself only.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


def configure_logging(
    level: str = "INFO",
    fmt: Optional[str] = None,
    use_structlog: bool = False,
) -> None:
    if use_structlog:
        try:
            import structlog

            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.dev.ConsoleRenderer(),
                ],
                wrapper_class=structlog.stdlib.BoundLogger,
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,
            )
        except ImportError:
            pass

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt or "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
