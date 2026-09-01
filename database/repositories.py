"""
database/repositories.py

All raw SQL lives here. Services (services/*.py) call repositories; Telegram
handlers call services. Handlers and listeners never see SQL directly.

Only ChannelRepository is exercised by phases 1-3. KeywordRepository,
ExcludeKeywordRepository and ProcessedMessageRepository are included now so
the schema/architecture is complete and stable, ready for the filter and
dedup phases to build on without touching this file's shape.
"""

from __future__ import annotations

from dataclasses import dataclass

from database.db import get_db


@dataclass(frozen=True)
class Channel:
    id: int
    telegram_id: int
    username: str | None
    title: str | None
    enabled: bool
    created_at: str


class ChannelRepository:
    async def add(self, telegram_id: int, username: str | None, title: str | None) -> Channel:
        db = get_db()
        cursor = await db.execute(
            """
            INSERT INTO channels (telegram_id, username, title, enabled)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                title = excluded.title
            """,
            (telegram_id, username, title),
        )
        await db.commit()
        row = await self.get_by_telegram_id(telegram_id)
        assert row is not None  # just inserted/updated, must exist
        return row

    async def remove(self, telegram_id: int) -> bool:
        db = get_db()
        cursor = await db.execute("DELETE FROM channels WHERE telegram_id = ?", (telegram_id,))
        await db.commit()
        return cursor.rowcount > 0

    async def set_enabled(self, telegram_id: int, enabled: bool) -> bool:
        db = get_db()
        cursor = await db.execute(
            "UPDATE channels SET enabled = ? WHERE telegram_id = ?",
            (1 if enabled else 0, telegram_id),
        )
        await db.commit()
        return cursor.rowcount > 0

    async def get_by_telegram_id(self, telegram_id: int) -> Channel | None:
        db = get_db()
        cursor = await db.execute(
            "SELECT * FROM channels WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        return self._row_to_channel(row) if row else None

    async def list_all(self) -> list[Channel]:
        db = get_db()
        cursor = await db.execute("SELECT * FROM channels ORDER BY created_at ASC")
        rows = await cursor.fetchall()
        return [self._row_to_channel(row) for row in rows]

    async def list_enabled(self) -> list[Channel]:
        """Enabled channels with full metadata (username/title) - cached by
        ChannelService so matched-message formatting doesn't need an extra
        Telegram API call to know a channel's display name/link."""
        db = get_db()
        cursor = await db.execute("SELECT * FROM channels WHERE enabled = 1")
        rows = await cursor.fetchall()
        return [self._row_to_channel(row) for row in rows]

    @staticmethod
    def _row_to_channel(row) -> Channel:
        return Channel(
            id=row["id"],
            telegram_id=row["telegram_id"],
            username=row["username"],
            title=row["title"],
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
        )


@dataclass(frozen=True)
class Keyword:
    id: int
    keyword: str
    enabled: bool
    created_at: str


class _KeywordTableRepository:
    """Shared CRUD for `keywords` and `exclude_keywords` - same shape, only
    the table name differs, so the SQL lives here once instead of being
    duplicated between the two concrete repositories below."""

    table: str = ""  # set by subclasses

    async def add(self, keyword: str) -> Keyword:
        db = get_db()
        await db.execute(
            f"INSERT OR IGNORE INTO {self.table} (keyword, enabled) VALUES (?, 1)",
            (keyword,),
        )
        await db.commit()
        row = await self.get(keyword)
        assert row is not None
        return row

    async def remove(self, keyword: str) -> bool:
        db = get_db()
        cursor = await db.execute(f"DELETE FROM {self.table} WHERE keyword = ?", (keyword,))
        await db.commit()
        return cursor.rowcount > 0

    async def set_enabled(self, keyword: str, enabled: bool) -> bool:
        db = get_db()
        cursor = await db.execute(
            f"UPDATE {self.table} SET enabled = ? WHERE keyword = ?",
            (1 if enabled else 0, keyword),
        )
        await db.commit()
        return cursor.rowcount > 0

    async def get(self, keyword: str) -> Keyword | None:
        db = get_db()
        cursor = await db.execute(f"SELECT * FROM {self.table} WHERE keyword = ?", (keyword,))
        row = await cursor.fetchone()
        return self._row_to_keyword(row) if row else None

    async def list_all(self) -> list[Keyword]:
        db = get_db()
        cursor = await db.execute(f"SELECT * FROM {self.table} ORDER BY created_at ASC")
        rows = await cursor.fetchall()
        return [self._row_to_keyword(row) for row in rows]

    async def list_enabled(self) -> list[str]:
        """Just the keyword strings for enabled rows - what the filter
        engine needs, kept cheap and small so it can be cached freely."""
        db = get_db()
        cursor = await db.execute(f"SELECT keyword FROM {self.table} WHERE enabled = 1")
        rows = await cursor.fetchall()
        return [row["keyword"] for row in rows]

    @staticmethod
    def _row_to_keyword(row) -> Keyword:
        return Keyword(
            id=row["id"],
            keyword=row["keyword"],
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
        )


class KeywordRepository(_KeywordTableRepository):
    table = "keywords"


class ExcludeKeywordRepository(_KeywordTableRepository):
    table = "exclude_keywords"


class SettingsRepository:
    async def get(self, key: str, default: str | None = None) -> str | None:
        db = get_db()
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else default

    async def set(self, key: str, value: str) -> None:
        db = get_db()
        await db.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await db.commit()


class ProcessedMessageRepository:
    async def is_processed(self, channel_id: int, message_id: int) -> bool:
        db = get_db()
        cursor = await db.execute(
            "SELECT 1 FROM processed_messages WHERE channel_id = ? AND message_id = ?",
            (channel_id, message_id),
        )
        row = await cursor.fetchone()
        return row is not None

    async def mark_processed(
        self,
        channel_id: int,
        message_id: int,
        message_hash: str,
        matched: bool,
        forwarded: bool,
    ) -> None:
        """
        Records that this (channel_id, message_id) has been handled, so it
        is never forwarded twice - the UNIQUE(channel_id, message_id)
        constraint is the actual duplicate-protection mechanism (Section
        13); INSERT OR IGNORE makes a concurrent duplicate insert a no-op
        instead of a crash.
        """
        db = get_db()
        await db.execute(
            """
            INSERT OR IGNORE INTO processed_messages
                (channel_id, message_id, message_hash, matched, forwarded)
            VALUES (?, ?, ?, ?, ?)
            """,
            (channel_id, message_id, message_hash, 1 if matched else 0, 1 if forwarded else 0),
        )
        await db.commit()
