"""
utils/helpers.py

Small shared helpers that don't belong to any one module.
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeVar

from telethon.errors import FloodWaitError

from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


async def call_with_flood_wait_retry(
    func: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = 3,
    **kwargs,
) -> T:
    """
    Run an async Telethon call, and if Telegram responds with FloodWaitError
    (Section 22 - "wait the required amount of time, then resume; do not
    crash"), sleep for the requested duration and retry, up to
    `max_retries` times. Any other exception propagates immediately - this
    helper only exists for FloodWait.
    """
    last_exc: FloodWaitError | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except FloodWaitError as exc:
            last_exc = exc
            wait_seconds = exc.seconds + 1
            logger.warning(
                "FloodWaitError: Telegram asked us to wait %ds (attempt %d/%d)",
                wait_seconds,
                attempt,
                max_retries,
            )
            await asyncio.sleep(wait_seconds)

    # Ran out of retries - let the last FloodWaitError surface so the
    # caller's own error handling (which already exists everywhere this is
    # used) can log/report it rather than us swallowing it silently.
    assert last_exc is not None
    raise last_exc
