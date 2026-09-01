"""
app.py

Entry point. Run with:

    python app.py

Full pipeline wired up through Phase 9: auth + client, database + channel
management, real-time listener with dynamic enabled-channel checking,
keyword filtering (include/exclude, AND/OR, on/off), job formatting +
forwarding to Saved Messages, duplicate prevention, Saved-Messages-only
admin commands, and FloodWait/RPC/connection-error handling with automatic
reconnection. Testing + full README (Phase 10) still to come.
"""

from __future__ import annotations

import asyncio
import os
from aiohttp import web
from telethon.errors import RPCError

from config import settings
from database.db import close_db, init_db
from services.channel_service import ChannelService
from services.keyword_service import KeywordService
from services.message_service import MessageService
from tg.client import build_client, connect_and_login
from tg.commands import register_commands
from tg.listeners import register_listeners
from utils.logger import configure_logging, get_logger

logger = get_logger(__name__)

# Section 23: if the connection drops and even Telethon's own
# auto_reconnect gives up (e.g. the client object itself needs rebuilding
# after a fatal-looking disconnect), how many times to rebuild the client
# and try again before actually giving up.
_MAX_RECONNECT_ATTEMPTS = 10
_RECONNECT_BACKOFF_SECONDS = 10


async def handle(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info("Web server started on port %s", port)


async def _run_once() -> None:
    """One full connect -> run -> (disconnect) cycle. Raised exceptions are
    handled by the retry loop in main()."""
    logger.info("Connecting to Telegram...")
    client = build_client()
    logger.info("Checking session...")
    await connect_and_login(client)
    logger.info("Connected successfully")

    logger.info("Initializing database...")
    await init_db()

    channel_service = ChannelService()
    logger.info("Loading enabled channels...")
    await channel_service.load_cache()

    keyword_service = KeywordService()
    logger.info("Loading filters...")
    await keyword_service.load_cache()
    message_service = MessageService(keyword_service)

    logger.info("Starting listeners...")
    register_listeners(client, channel_service, message_service, settings.destination)
    register_commands(client, channel_service, keyword_service)

    logger.info("System is running.")
    print("\nWaiting for new jobs...\n")

    try:
        await client.run_until_disconnected()
    finally:
        await close_db()
        if client.is_connected():
            await client.disconnect()


async def main() -> None:
    configure_logging(settings.log_level)
    logger.info("Loading configuration...")

    # Start the web server in the background
    asyncio.create_task(web_server())

    attempt = 0
    while True:
        try:
            await _run_once()
            # run_until_disconnected() returned normally (clean disconnect,
            # e.g. session revoked elsewhere) - don't loop forever on that.
            break
        except (OSError, ConnectionError, RPCError) as exc:
            attempt += 1
            if attempt > _MAX_RECONNECT_ATTEMPTS:
                logger.error("Giving up after %d reconnect attempts", attempt - 1)
                raise
            logger.error(
                "Connection problem (%s) - reconnecting in %ds (attempt %d/%d)",
                exc,
                _RECONNECT_BACKOFF_SECONDS,
                attempt,
                _MAX_RECONNECT_ATTEMPTS,
                exc_info=True,
            )
            await asyncio.sleep(_RECONNECT_BACKOFF_SECONDS)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
