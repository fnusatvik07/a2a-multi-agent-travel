"""A very small logging helper, so the five services print in one voice.

Deliberately dependency-free: each agent already drags in a different console
library, and this way none of them wins.
"""

from __future__ import annotations

import logging
import os
import sys

from .config import settings

_COLOURS = {
    "concierge": "\033[95m",
    "skyline": "\033[96m",
    "hearth": "\033[93m",
    "sentinel": "\033[92m",
    "ledger": "\033[94m",
    "mcp": "\033[90m",
    "client": "\033[97m",
}
_RESET = "\033[0m"


def _supports_colour() -> bool:
    return sys.stderr.isatty() and os.environ.get("NO_COLOR") is None


class _Prefixer(logging.Formatter):
    def __init__(self, service: str) -> None:
        colour = _COLOURS.get(service, "") if _supports_colour() else ""
        reset = _RESET if colour else ""
        super().__init__(
            fmt=f"{colour}%(asctime)s {service:<10}{reset} %(message)s",
            datefmt="%H:%M:%S",
        )


def get_logger(service: str) -> logging.Logger:
    """Return a logger that tags every line with the service name."""
    logger = logging.getLogger(f"atlastrip.{service}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_Prefixer(service))
        logger.addHandler(handler)
        logger.setLevel(settings().log_level)
        logger.propagate = False
    return logger
