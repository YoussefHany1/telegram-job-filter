"""
database/db.py

Thin async wrapper around a single shared aiosqlite connection. Repositories
(database/repositories.py) use `get_db()` to get the connection - nobody
outside this module opens a connection directly.
"""

from __future__ import annotations

import aiosqlite

from config import settings
from database.models import DEFAULT_SETTINGS, SCHEMA_STATEMENTS
from utils.logger import get_logger

logger = get_logger(__name__)

_connection: aiosqlite.Connection | None = None


async def init_db() -> None:
    """Open the shared connection, create tables if missing, seed defaults."""
    global _connection

    _connection = await aiosqlite.connect(settings.db_path)
    # Return rows as dict-like objects instead of plain tuples.
    _connection.row_factory = aiosqlite.Row
    # Needed for the UNIQUE(channel_id, message_id) constraint to actually
    # protect us, and generally good practice for a concurrent app.
    await _connection.execute("PRAGMA foreign_keys = ON")
    await _connection.execute("PRAGMA journal_mode = WAL")

    for statement in SCHEMA_STATEMENTS:
        await _connection.execute(statement)

    for key, value in DEFAULT_SETTINGS.items():
        await _connection.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    await _connection.commit()
    logger.info("Database initialized at %s", settings.db_path)


def get_db() -> aiosqlite.Connection:
    if _connection is None:
        raise RuntimeError("Database not initialized - call init_db() first.")
    return _connection


async def close_db() -> None:
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
        logger.info("Database connection closed")
