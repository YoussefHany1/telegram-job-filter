"""
services/keyword_service.py

Business logic for include/exclude keywords, the AND/OR match mode, and the
global filter on/off toggle. Same caching pattern as ChannelService: the
listener calls this on every matched-channel message, so the keyword lists
and mode are cached in memory and only reloaded from SQLite when something
actually changes (add/remove/enable/disable/mode change), or on startup.
"""

from __future__ import annotations

from filters.rules import MatchMode
from database.repositories import ExcludeKeywordRepository, KeywordRepository, SettingsRepository
from utils.logger import get_logger

logger = get_logger(__name__)

_SETTING_MATCH_MODE = "keyword_match_mode"
_SETTING_FILTER_ENABLED = "filter_enabled"


class KeywordService:
    def __init__(
        self,
        keyword_repo: KeywordRepository | None = None,
        exclude_repo: ExcludeKeywordRepository | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        self._keyword_repo = keyword_repo or KeywordRepository()
        self._exclude_repo = exclude_repo or ExcludeKeywordRepository()
        self._settings_repo = settings_repo or SettingsRepository()

        self._include_cache: list[str] = []
        self._exclude_cache: list[str] = []
        self._mode_cache: MatchMode = MatchMode.OR
        self._filter_enabled_cache: bool = True

    # ---- cache -----------------------------------------------------

    async def load_cache(self) -> None:
        self._include_cache = await self._keyword_repo.list_enabled()
        self._exclude_cache = await self._exclude_repo.list_enabled()

        mode_raw = await self._settings_repo.get(_SETTING_MATCH_MODE, MatchMode.OR.value)
        self._mode_cache = (
            MatchMode(mode_raw) if mode_raw in (m.value for m in MatchMode) else MatchMode.OR
        )

        enabled_raw = await self._settings_repo.get(_SETTING_FILTER_ENABLED, "1")
        self._filter_enabled_cache = enabled_raw == "1"

        logger.info(
            "Loaded %d include keyword(s), %d exclude keyword(s), mode=%s, filter_enabled=%s",
            len(self._include_cache),
            len(self._exclude_cache),
            self._mode_cache.value,
            self._filter_enabled_cache,
        )

    def get_include_keywords(self) -> list[str]:
        return list(self._include_cache)

    def get_exclude_keywords(self) -> list[str]:
        return list(self._exclude_cache)

    def get_match_mode(self) -> MatchMode:
        return self._mode_cache

    def is_filtering_enabled(self) -> bool:
        return self._filter_enabled_cache

    # ---- include keyword mutations ----------------------------------

    async def add_keyword(self, keyword: str) -> None:
        await self._keyword_repo.add(keyword.strip())
        await self.load_cache()

    async def remove_keyword(self, keyword: str) -> bool:
        removed = await self._keyword_repo.remove(keyword.strip())
        await self.load_cache()
        return removed

    async def list_keywords(self):
        return await self._keyword_repo.list_all()

    # ---- exclude keyword mutations -----------------------------------

    async def add_exclude_keyword(self, keyword: str) -> None:
        await self._exclude_repo.add(keyword.strip())
        await self.load_cache()

    async def remove_exclude_keyword(self, keyword: str) -> bool:
        removed = await self._exclude_repo.remove(keyword.strip())
        await self.load_cache()
        return removed

    async def list_exclude_keywords(self):
        return await self._exclude_repo.list_all()

    # ---- mode / on-off -----------------------------------------------

    async def set_match_mode(self, mode: MatchMode) -> None:
        await self._settings_repo.set(_SETTING_MATCH_MODE, mode.value)
        await self.load_cache()

    async def set_filtering_enabled(self, enabled: bool) -> None:
        await self._settings_repo.set(_SETTING_FILTER_ENABLED, "1" if enabled else "0")
        await self.load_cache()
