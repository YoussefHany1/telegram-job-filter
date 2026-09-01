"""
tg/listeners.py

Real-time message listener.

DESIGN NOTE - do not add `chats=...` to the event decorator
-------------------------------------------------------------
Channels are managed dynamically at runtime (added/removed/enabled/disabled
via SQLite, eventually via Saved Messages admin commands). Telethon's
`chats=` filter on `events.NewMessage` is baked in at registration time and
would require re-registering the handler (or restarting the app) every time
the channel list changes. So instead:

    @client.on(events.NewMessage)   # <- no chats= filter
    async def handler(event):
        if not channel_service.is_enabled(event.chat_id):
            return
        ...

The very first thing the handler does is the enabled-channel check, using
ChannelService's in-memory cache (no DB hit). Every message from every chat
the account can see passes through this function, so that check has to stay
cheap - which is exactly why the cache exists.

Pipeline (Section 33), as implemented so far
---------------------------------------------
enabled-channel check -> extract text/caption -> has text? -> normalize +
include filter -> exclude filter -> duplicate check -> format + send to
Saved Messages on match, then mark as processed.
"""

from __future__ import annotations

from telethon import TelegramClient, events

from services.channel_service import ChannelService
from services.message_service import MessageService
from tg.sender import build_message_link, format_job_message, send_matched_job
from utils.logger import get_logger

logger = get_logger(__name__)


def register_listeners(
    client: TelegramClient,
    channel_service: ChannelService,
    message_service: MessageService,
    destination: str,
) -> None:
    @client.on(events.NewMessage)
    async def handler(event: events.NewMessage.Event) -> None:
        chat_id = event.chat_id

        # Step 1, always first: is this one of our enabled source channels?
        # Cheap in-memory check - bail out immediately for the other ~99%
        # of chats/messages the account sees.
        if not channel_service.is_enabled(chat_id):
            return

        try:
            await _handle_relevant_message(event, channel_service, message_service, client, destination)
        except Exception:
            # A single bad message must never take down the listener.
            logger.error("Failed to process message from chat_id=%s", chat_id, exc_info=True)

    logger.info("Message listener registered")


async def _handle_relevant_message(
    event: events.NewMessage.Event,
    channel_service: ChannelService,
    message_service: MessageService,
    client: TelegramClient,
    destination: str,
) -> None:
    channel = channel_service.get_channel(event.chat_id)
    source_label = f"@{channel.username}" if channel and channel.username else (
        channel.title if channel else str(event.chat_id)
    )

    # Text extraction: covers both plain message text and media captions -
    # Telethon exposes both through `.message`. Photo/video without a
    # caption, or files with no text, naturally end up empty here and are
    # ignored, per spec (no OCR / file-content extraction in v1).
    original_text = event.message.message or ""
    if not original_text.strip():
        logger.info("Message from %s has no text/caption - ignoring", source_label)
        return

    result = message_service.evaluate(original_text)
    if not result.matched:
        logger.info(
            "Message from %s did not match (reason=%s)", source_label, result.reason
        )
        return

    # Duplicate check (Section 13) - only needed on the path that's about
    # to forward, since that's the only place a duplicate actually matters.
    if await message_service.is_already_forwarded(event.chat_id, event.message.id):
        logger.info(
            "Message from %s already forwarded (channel_id=%s, message_id=%s) - skipping",
            source_label,
            event.chat_id,
            event.message.id,
        )
        return

    logger.info(
        "Message matched keyword(s): %s (source=%s)",
        ", ".join(result.matched_include_keywords),
        source_label,
    )

    link = build_message_link(
        username=channel.username if channel else None,
        telegram_channel_id=event.chat_id,
        message_id=event.message.id,
    )
    formatted = format_job_message(
        source_label=source_label,
        matched_keywords=result.matched_include_keywords,
        message_date=event.message.date,
        original_text=original_text,
        message_link=link,
    )

    await send_matched_job(client, destination, formatted)
    await message_service.mark_forwarded(event.chat_id, event.message.id, original_text)
