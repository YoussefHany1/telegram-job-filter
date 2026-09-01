"""
tg/client.py

Owns the single Telethon client for the whole app. This is a *user* session
(Telethon), not a Bot API client - it logs in as your personal account so it
can read channels you're a member of but don't administrate.

On first run, `client.start(phone=...)` will interactively prompt in the
console for the verification code (and 2FA password if enabled). Telethon
persists the resulting session to a local `<SESSION_NAME>.session` file, so
every run after that reuses it silently - no code/password is ever stored
in source code, only in that local session file (which .gitignore excludes).
"""

from __future__ import annotations

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, RPCError, SessionPasswordNeededError

from config import settings
from utils.helpers import call_with_flood_wait_retry
from utils.logger import get_logger

logger = get_logger(__name__)


def build_client() -> TelegramClient:
    """Construct the client. Does not connect yet.

    `auto_reconnect=True` (the default) plus explicit `connection_retries`
    and `retry_delay` (Section 23) means Telethon will keep retrying to
    reconnect on its own after a dropped connection, without tearing down
    `run_until_disconnected()` - normal processing resumes automatically
    once the connection is back, no restart needed.
    """
    session = StringSession(settings.string_session) if settings.string_session else settings.session_name
    return TelegramClient(
        session,
        settings.api_id,
        settings.api_hash,
        connection_retries=None,  # retry forever
        retry_delay=5,
        auto_reconnect=True,
        request_retries=5,
    )


async def connect_and_login(client: TelegramClient) -> None:
    """
    Connect and, if there's no valid saved session, walk through the
    interactive login flow (phone -> code -> optional 2FA password).
    Safe to call on every startup: if a valid session already exists,
    this is a no-op beyond connecting.
    """
    await client.connect()

    if await client.is_user_authorized():
        logger.info("Existing session is valid - skipping login")
        return

    logger.info("No valid session found - starting login flow")
    try:
        await call_with_flood_wait_retry(client.send_code_request, settings.phone)
        code = input("Enter the Telegram verification code you received: ").strip()
        try:
            await client.sign_in(settings.phone, code)
        except SessionPasswordNeededError:
            password = input("Two-factor authentication is enabled. Enter your password: ").strip()
            await client.sign_in(password=password)
    except FloodWaitError as exc:
        logger.error("Telegram is rate-limiting login attempts - try again in %ds", exc.seconds)
        raise
    except RPCError:
        logger.error("Login failed due to a Telegram API error", exc_info=True)
        raise
    except Exception:
        logger.error("Login failed", exc_info=True)
        raise

    if isinstance(client.session, StringSession):
        logger.info("Login successful. Your StringSession is:\n%s\nSave this as STRING_SESSION in your .env", client.session.save())
    else:
        logger.info("Login successful - session saved as %s.session", settings.session_name)
