"""Structured JSON logging configuration.

Patient data MUST NEVER appear in log messages.
"""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt=(
            '{"timestamp":"%(asctime)s",'
            '"level":"%(levelname)s",'
            '"logger":"%(name)s",'
            '"message":"%(message)s"}'
        ),
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger("mediextract")
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False

    # Quieten noisy libraries
    for lib in ("azure", "httpx", "httpcore", "openai"):
        logging.getLogger(lib).setLevel(logging.WARNING)
