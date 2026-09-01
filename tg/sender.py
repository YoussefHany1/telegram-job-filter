"""
tg/sender.py

Formats a matched job (Section 11 template) and sends it to the configured
destination (Saved Messages, "me", by default - see config.settings.destination).

Preserves `original_text` verbatim; only adds the header/footer around it.
"""

from __future__ import annotations

from datetime import datetime

from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.utils import resolve_id

from utils.helpers import call_with_flood_wait_retry
from utils.logger import get_logger

logger = get_logger(__name__)


def build_message_link(
    username: str | None,
    telegram_channel_id: int,
    message_id: int,
) -> str | None:
    """
    Public channels: https://t.me/<username>/<message_id>
    Private channels (account is a member): https://t.me/c/<internal_id>/<message_id>,
    Telegram's "member deep link" format - resolves for anyone who already
    has access, does nothing for anyone who doesn't (no permission bypass).
    Returns None if a link can't be built - caller falls back to
    "original post unavailable" rather than crashing.
    """
    try:
        if username:
            return f"https://t.me/{username}/{message_id}"
        internal_id, _peer_type = resolve_id(telegram_channel_id)
        return f"https://t.me/c/{internal_id}/{message_id}"
    except Exception:
        logger.warning("Could not build message link for chat_id=%s", telegram_channel_id, exc_info=True)
        return None


def format_job_message(
    *,
    source_label: str,
    matched_keywords: list[str],
    message_date: datetime,
    original_text: str,
    message_link: str | None,
) -> str:
    keyword_line = ", ".join(matched_keywords) if matched_keywords else "-"
    link_line = message_link or "Original post unavailable"

    return (
        "🔥 MATCHED JOB\n\n"
        f"📢 Source: {source_label}\n"
        f"🔑 Matched Keyword: {keyword_line}\n\n"
        f"🕒 {message_date.strftime('%Y-%m-%d %H:%M')}\n\n"
        "--------------------\n\n"
        f"{original_text}\n\n"
        "--------------------\n\n"
        f"🔗 Original Post:\n{link_line}"
    )


async def send_matched_job(client: TelegramClient, destination: str, formatted_text: str) -> None:
    """Sends with FloodWait-aware retry (Section 22: wait it out, don't
    crash). Any other RPC/network error is logged with context and
    re-raised - the listener's per-message try/except (Section 21: "one
    problematic message must not stop the entire application") is what
    actually keeps the app alive."""
    try:
        await call_with_flood_wait_retry(
            client.send_message, destination, formatted_text, link_preview=False
        )
        logger.info("Job forwarded successfully")
    except RPCError:
        logger.error("Telegram rejected the forward to %s", destination, exc_info=True)
        raise
    except Exception:
        logger.error("Failed to send matched job to %s", destination, exc_info=True)
        raise
