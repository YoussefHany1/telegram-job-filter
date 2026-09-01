"""
services/message_service.py

Thin orchestration layer between the listener and the filter engine: pulls
the current include/exclude keywords + mode from KeywordService's cache and
runs FilterEngine.evaluate(). Kept separate from FilterEngine itself so the
engine stays pure/testable (Section 28) while this layer owns the
"is filtering even turned on" business rule.

Also owns duplicate-prevention (Section 13): the pipeline in
tg/listeners.py only calls into ProcessedMessageRepository through here,
matching the "database access layer, not raw SQL in Telegram handlers"
rule from Section 19.
"""

from __future__ import annotations

import hashlib

from database.repositories import ProcessedMessageRepository
from filters.engine import FilterEngine, FilterResult
from services.keyword_service import KeywordService


class MessageService:
    def __init__(
        self,
        keyword_service: KeywordService,
        engine: FilterEngine | None = None,
        processed_repo: ProcessedMessageRepository | None = None,
    ) -> None:
        self._keyword_service = keyword_service
        self._engine = engine or FilterEngine()
        self._processed_repo = processed_repo or ProcessedMessageRepository()

    def evaluate(self, original_text: str) -> FilterResult:
        if not self._keyword_service.is_filtering_enabled():
            return FilterResult(matched=False, normalized_text="", reason="filtering_disabled")

        return self._engine.evaluate(
            original_text=original_text,
            include_keywords=self._keyword_service.get_include_keywords(),
            exclude_keywords=self._keyword_service.get_exclude_keywords(),
            mode=self._keyword_service.get_match_mode(),
        )

    # ---- duplicate prevention (Section 13) -----------------------------

    async def is_already_forwarded(self, channel_id: int, message_id: int) -> bool:
        """UNIQUE(channel_id, message_id) in SQLite is the real guard; this
        is the pre-check so we can skip re-sending and just log instead of
        relying on a DB error to catch it."""
        return await self._processed_repo.is_processed(channel_id, message_id)

    async def mark_forwarded(self, channel_id: int, message_id: int, original_text: str) -> None:
        message_hash = hashlib.sha256(original_text.encode("utf-8")).hexdigest()
        await self._processed_repo.mark_processed(
            channel_id=channel_id,
            message_id=message_id,
            message_hash=message_hash,
            matched=True,
            forwarded=True,
        )
