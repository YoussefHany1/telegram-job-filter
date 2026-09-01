"""
tg/commands.py

Saved-Messages-only admin command handler (Sections 15-17).

Security
--------
This handler ONLY reacts to messages that are both sent by the account
owner AND in the Saved Messages / self chat:

    @client.on(events.NewMessage(from_users='me', chats='me'))

No other chat can trigger administration, by construction - Telethon's
`from_users`/`chats` filters are applied by the library before our code
ever runs, so there's no separate "is this really me" check to get wrong.

We additionally require the message to start with "/": the job posts we
ourselves forward into Saved Messages are also from='me' to chat='me', so
without this guard every forwarded job would be parsed as an unknown
command and get a spammy reply back into Saved Messages.
"""

from __future__ import annotations

from telethon import TelegramClient, events
from telethon import utils as tl_utils

from filters.rules import MatchMode
from services.channel_service import ChannelService, ChannelValidationError
from services.keyword_service import KeywordService
from utils.logger import get_logger

logger = get_logger(__name__)

_USAGE = (
    "Available commands:\n"
    "/addchannel <@channel|id>\n"
    "/removechannel <@channel|id>\n"
    "/enablechannel <@channel|id>\n"
    "/disablechannel <@channel|id>\n"
    "/channels\n"
    "/addkeyword <keyword>\n"
    "/removekeyword <keyword>\n"
    "/keywords\n"
    "/addexclude <keyword>\n"
    "/removeexclude <keyword>\n"
    "/excludes\n"
    "/filter on|off\n"
    "/mode and|or"
)


def register_commands(
    client: TelegramClient,
    channel_service: ChannelService,
    keyword_service: KeywordService,
) -> None:
    @client.on(events.NewMessage(from_users="me", chats="me"))
    async def command_handler(event: events.NewMessage.Event) -> None:
        text = (event.raw_text or "").strip()
        if not text.startswith("/"):
            # Not a command (e.g. one of our own forwarded job posts, or a
            # normal note the user wrote to themselves) - leave it alone.
            return

        parts = text.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        try:
            reply = await _dispatch(command, arg, client, channel_service, keyword_service)
        except ChannelValidationError as exc:
            reply = f"❌ {exc}"
        except Exception:
            logger.error("Command failed: %s", text, exc_info=True)
            reply = "❌ Something went wrong running that command. Check the logs for details."

        if reply:
            await event.respond(reply)

    logger.info("Admin command handler registered (Saved Messages only)")


async def _dispatch(
    command: str,
    arg: str,
    client: TelegramClient,
    channel_service: ChannelService,
    keyword_service: KeywordService,
) -> str:
    if command == "/addchannel":
        return await _add_channel(client, channel_service, arg)
    if command == "/removechannel":
        return await _remove_channel(client, channel_service, arg)
    if command == "/enablechannel":
        return await _set_channel_enabled(client, channel_service, arg, True)
    if command == "/disablechannel":
        return await _set_channel_enabled(client, channel_service, arg, False)
    if command == "/channels":
        return await _list_channels(channel_service)

    if command == "/addkeyword":
        return await _add_keyword(keyword_service, arg)
    if command == "/removekeyword":
        return await _remove_keyword(keyword_service, arg)
    if command == "/keywords":
        return await _list_keywords(keyword_service)

    if command == "/addexclude":
        return await _add_exclude(keyword_service, arg)
    if command == "/removeexclude":
        return await _remove_exclude(keyword_service, arg)
    if command == "/excludes":
        return await _list_excludes(keyword_service)

    if command == "/filter":
        return await _set_filter(keyword_service, arg)
    if command == "/mode":
        return await _set_mode(keyword_service, arg)

    if command in ("/help", "/start"):
        return _USAGE

    return f"❓ Unknown command: {command}\n\n{_USAGE}"


# ---- channel commands -----------------------------------------------------

async def _add_channel(client, channel_service: ChannelService, arg: str) -> str:
    if not arg:
        return "Usage: /addchannel <@channel|id>"
    channel = await channel_service.add_channel(client, arg)
    label = f"@{channel.username}" if channel.username else (channel.title or str(channel.telegram_id))
    return f"✅ Channel added successfully: {label}"


async def _resolve_channel_id(client, channel_service: ChannelService, arg: str) -> int:
    """
    Resolve a user-typed identifier to the telegram_id primary key.
    Prefers an already-known local channel first (so /removechannel and
    /disablechannel keep working even if the channel later became
    inaccessible or was deleted on Telegram's side), then falls back to a
    live lookup for identifiers we haven't seen before.
    """
    if not arg:
        raise ChannelValidationError("Please provide a channel username or id.")

    stripped_username = arg.lstrip("@").lower()
    for ch in await channel_service.list_channels():
        if ch.username and ch.username.lower() == stripped_username:
            return ch.telegram_id
        if str(ch.telegram_id) == arg:
            return ch.telegram_id

    try:
        return int(arg)
    except ValueError:
        pass

    entity = await client.get_entity(arg)
    return tl_utils.get_peer_id(entity)


async def _remove_channel(client, channel_service: ChannelService, arg: str) -> str:
    telegram_id = await _resolve_channel_id(client, channel_service, arg)
    removed = await channel_service.remove_channel(telegram_id)
    return "✅ Channel removed." if removed else "⚠️ That channel wasn't in the list."


async def _set_channel_enabled(client, channel_service: ChannelService, arg: str, enabled: bool) -> str:
    telegram_id = await _resolve_channel_id(client, channel_service, arg)
    changed = await channel_service.set_enabled(telegram_id, enabled)
    if not changed:
        return "⚠️ That channel wasn't found."
    return f"✅ Channel {'enabled' if enabled else 'disabled'}."


async def _list_channels(channel_service: ChannelService) -> str:
    channels = await channel_service.list_channels()
    if not channels:
        return "No channels configured yet. Add one with /addchannel @channel"
    lines = ["📋 Channels:"]
    for ch in channels:
        status = "🟢" if ch.enabled else "⚪️"
        label = f"@{ch.username}" if ch.username else (ch.title or str(ch.telegram_id))
        lines.append(f"{status} {label} ({ch.telegram_id})")
    return "\n".join(lines)


# ---- keyword commands -------------------------------------------------------

async def _add_keyword(keyword_service: KeywordService, arg: str) -> str:
    if not arg:
        return "Usage: /addkeyword <keyword>"
    await keyword_service.add_keyword(arg)
    return f"✅ Keyword added: {arg}"


async def _remove_keyword(keyword_service: KeywordService, arg: str) -> str:
    if not arg:
        return "Usage: /removekeyword <keyword>"
    removed = await keyword_service.remove_keyword(arg)
    return "✅ Keyword removed." if removed else "⚠️ That keyword wasn't found."


async def _list_keywords(keyword_service: KeywordService) -> str:
    keywords = await keyword_service.list_keywords()
    if not keywords:
        return "No include keywords configured yet."
    lines = ["🔑 Include keywords:"]
    for kw in keywords:
        status = "🟢" if kw.enabled else "⚪️"
        lines.append(f"{status} {kw.keyword}")
    return "\n".join(lines)


async def _add_exclude(keyword_service: KeywordService, arg: str) -> str:
    if not arg:
        return "Usage: /addexclude <keyword>"
    await keyword_service.add_exclude_keyword(arg)
    return f"✅ Exclude keyword added: {arg}"


async def _remove_exclude(keyword_service: KeywordService, arg: str) -> str:
    if not arg:
        return "Usage: /removeexclude <keyword>"
    removed = await keyword_service.remove_exclude_keyword(arg)
    return "✅ Exclude keyword removed." if removed else "⚠️ That keyword wasn't found."


async def _list_excludes(keyword_service: KeywordService) -> str:
    keywords = await keyword_service.list_exclude_keywords()
    if not keywords:
        return "No exclude keywords configured yet."
    lines = ["🚫 Exclude keywords:"]
    for kw in keywords:
        status = "🟢" if kw.enabled else "⚪️"
        lines.append(f"{status} {kw.keyword}")
    return "\n".join(lines)


# ---- filter toggle / match mode --------------------------------------------

async def _set_filter(keyword_service: KeywordService, arg: str) -> str:
    value = arg.strip().lower()
    if value not in ("on", "off"):
        return "Usage: /filter on | /filter off"
    await keyword_service.set_filtering_enabled(value == "on")
    return f"✅ Filtering turned {value}."


async def _set_mode(keyword_service: KeywordService, arg: str) -> str:
    value = arg.strip().upper()
    if value not in (MatchMode.AND.value, MatchMode.OR.value):
        return "Usage: /mode and | /mode or"
    await keyword_service.set_match_mode(MatchMode(value))
    return f"✅ Match mode set to {value}."
