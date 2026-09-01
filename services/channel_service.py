"""
services/channel_service.py

Business logic for channel management, sitting between Telegram handlers
and the ChannelRepository.

Caching
-------
The listener (tg/listeners.py) has to decide, for *every single incoming
message from any chat the account is in*, whether that chat is one of our
enabled source channels. Hitting SQLite on every message is wasteful, so
this service keeps an in-memory set of enabled telegram_ids and only hits
the database when the channel list actually changes (add/remove/enable/
disable), or on first load. `is_enabled()` itself never awaits the DB.
"""

from __future__ import annotations

from telethon import utils as tl_utils
from telethon.errors import (
    ChannelPrivateError,
    ChannelInvalidError,
    FloodWaitError,
    RPCError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.tl.types import Channel as TLChannel, Chat as TLChat

from database.repositories import Channel, ChannelRepository
from utils.helpers import call_with_flood_wait_retry
from utils.logger import get_logger

logger = get_logger(__name__)


class ChannelValidationError(Exception):
    """Raised when a channel identifier can't be resolved/accessed."""


class ChannelService:
    def __init__(self, repository: ChannelRepository | None = None) -> None:
        self._repo = repository or ChannelRepository()
        # telegram_id -> Channel, for enabled channels only. A dict (not just
        # a set of ids) so matched-message formatting can read
        # username/title straight from cache too, without another Telegram
        # API round trip - it's the same O(1) lookup cost either way.
        self._enabled_cache: dict[int, Channel] = {}

    # ---- cache -----------------------------------------------------

    async def load_cache(self) -> None:
        channels = await self._repo.list_enabled()
        self._enabled_cache = {c.telegram_id: c for c in channels}
        logger.info("Loaded %d enabled channel(s)", len(self._enabled_cache))

    def is_enabled(self, telegram_chat_id: int) -> bool:
        """Cheap, synchronous, no DB access - safe to call on every message."""
        return telegram_chat_id in self._enabled_cache

    def get_channel(self, telegram_chat_id: int) -> Channel | None:
        """Cached channel metadata (username/title) for an enabled channel.
        Returns None if the channel isn't in the enabled cache."""
        return self._enabled_cache.get(telegram_chat_id)

    # ---- mutations (all refresh the cache afterward) ----------------

    async def add_channel(self, client, identifier: str) -> Channel:
        """
        Resolve `identifier` (a @username, t.me link, or numeric id) against
        Telegram via the live client, then persist it. Raises
        ChannelValidationError with a clear message on anything invalid,
        private-and-inaccessible, or otherwise unusable - callers (the
        command handler) are expected to catch this and reply to the user
        instead of letting the app crash.
        """
        try:
            entity = await call_with_flood_wait_retry(client.get_entity, identifier)
        except (UsernameInvalidError, UsernameNotOccupiedError):
            raise ChannelValidationError(f"'{identifier}' is not a valid/existing username.")
        except (ChannelPrivateError, ChannelInvalidError):
            raise ChannelValidationError(
                f"'{identifier}' is private or inaccessible to this account."
            )
        except ValueError as exc:
            # Telethon raises plain ValueError for a variety of "can't find
            # this entity" cases (bad id, never seen before, etc).
            raise ChannelValidationError(f"Could not resolve '{identifier}': {exc}")
        except FloodWaitError as exc:
            # Ran out of flood-wait retries.
            raise ChannelValidationError(
                f"Telegram is rate-limiting this account - try again in {exc.seconds}s."
            )
        except RPCError as exc:
            raise ChannelValidationError(f"Telegram rejected '{identifier}': {exc}")

        if not isinstance(entity, (TLChannel, TLChat)):
            raise ChannelValidationError(f"'{identifier}' is not a channel or group.")

        telegram_id = tl_utils.get_peer_id(entity)
        username = getattr(entity, "username", None)
        title = getattr(entity, "title", None)

        channel = await self._repo.add(telegram_id, username, title)
        await self.load_cache()
        logger.info("Channel added: %s (%s)", title or username or telegram_id, telegram_id)
        return channel

    async def remove_channel(self, telegram_id: int) -> bool:
        removed = await self._repo.remove(telegram_id)
        await self.load_cache()
        return removed

    async def set_enabled(self, telegram_id: int, enabled: bool) -> bool:
        changed = await self._repo.set_enabled(telegram_id, enabled)
        await self.load_cache()
        return changed

    async def list_channels(self) -> list[Channel]:
        return await self._repo.list_all()
