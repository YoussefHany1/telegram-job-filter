"""
database/models.py

Holds the SQL schema for the whole application. All tables from the final
design are created up front (channels, keywords, exclude_keywords, settings,
processed_messages) so later phases only need to add repositories/services,
never migrations. Phases 1-3 only exercise the `channels` table; the rest
sit ready and unused until the keyword/filter/dedup phases land.
"""

from __future__ import annotations

SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS channels (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL UNIQUE,
        username    TEXT,
        title       TEXT,
        enabled     INTEGER NOT NULL DEFAULT 1,
        created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS keywords (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword    TEXT NOT NULL UNIQUE,
        enabled    INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS exclude_keywords (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword    TEXT NOT NULL UNIQUE,
        enabled    INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS processed_messages (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id     INTEGER NOT NULL,
        message_id     INTEGER NOT NULL,
        message_hash   TEXT,
        matched        INTEGER NOT NULL DEFAULT 0,
        forwarded      INTEGER NOT NULL DEFAULT 0,
        processed_at   TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(channel_id, message_id)
    )
    """,
    # Helpful indexes for the lookups the listener does on every message.
    "CREATE INDEX IF NOT EXISTS idx_channels_telegram_id ON channels(telegram_id)",
    "CREATE INDEX IF NOT EXISTS idx_channels_enabled ON channels(enabled)",
    "CREATE INDEX IF NOT EXISTS idx_processed_channel_message ON processed_messages(channel_id, message_id)",
]

# Default settings row(s). filter_enabled toggles the whole matching pipeline
# on/off via `/filter on` / `/filter off` (wired up in a later phase).
DEFAULT_SETTINGS: dict[str, str] = {
    "filter_enabled": "1",
}
