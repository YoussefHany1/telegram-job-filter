"""
utils/logger.py

Central logging configuration. Import get_logger(__name__) from any module
instead of calling logging.getLogger directly, so formatting stays consistent.
"""

from __future__ import annotations

import logging
import sys


_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.handlers.clear()
    root.addHandler(handler)

    # Telethon is very chatty on DEBUG/INFO - keep it at WARNING unless the
    # app itself is running in DEBUG mode.
    if level.upper() != "DEBUG":
        logging.getLogger("telethon").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
