"""
tests/test_message_service.py

Exercises KeywordService + MessageService against a real (temp) SQLite
database - verifies that adding/removing keywords, switching AND/OR mode,
and toggling filtering on/off actually take effect live, and that
duplicate-forward prevention (Section 13) works.
"""

import pytest

from filters.rules import MatchMode
from services.keyword_service import KeywordService
from services.message_service import MessageService

pytestmark = pytest.mark.usefixtures("test_db")


async def test_no_keywords_configured_never_matches():
    keyword_service = KeywordService()
    await keyword_service.load_cache()
    message_service = MessageService(keyword_service)

    result = message_service.evaluate("React Native Developer needed")
    assert not result.matched


async def test_added_keyword_takes_effect_immediately():
    keyword_service = KeywordService()
    await keyword_service.load_cache()
    message_service = MessageService(keyword_service)

    await keyword_service.add_keyword("React Native")
    result = message_service.evaluate("React Native Developer needed")
    assert result.matched
    assert "React Native" in result.matched_include_keywords


async def test_exclude_keyword_takes_effect_immediately():
    keyword_service = KeywordService()
    await keyword_service.load_cache()
    message_service = MessageService(keyword_service)

    await keyword_service.add_keyword("React Native")
    await keyword_service.add_exclude_keyword("Senior")

    result = message_service.evaluate("Senior React Native Developer")
    assert not result.matched
    assert result.reason == "excluded"


async def test_removing_keyword_takes_effect_immediately():
    keyword_service = KeywordService()
    await keyword_service.load_cache()
    message_service = MessageService(keyword_service)

    await keyword_service.add_keyword("React Native")
    assert message_service.evaluate("React Native Developer").matched

    await keyword_service.remove_keyword("React Native")
    assert not message_service.evaluate("React Native Developer").matched


async def test_and_or_mode_switch_takes_effect_immediately():
    keyword_service = KeywordService()
    await keyword_service.load_cache()
    message_service = MessageService(keyword_service)

    await keyword_service.add_keyword("React Native")
    await keyword_service.add_keyword("Expo")

    # default mode is OR
    assert message_service.evaluate("React Native Developer").matched

    await keyword_service.set_match_mode(MatchMode.AND)
    assert not message_service.evaluate("React Native Developer").matched
    assert message_service.evaluate("React Native Developer, must know Expo").matched


async def test_filter_off_disables_all_matching():
    keyword_service = KeywordService()
    await keyword_service.load_cache()
    message_service = MessageService(keyword_service)

    await keyword_service.add_keyword("React Native")
    await keyword_service.set_filtering_enabled(False)

    result = message_service.evaluate("React Native Developer needed")
    assert not result.matched
    assert result.reason == "filtering_disabled"


async def test_duplicate_prevention():
    keyword_service = KeywordService()
    await keyword_service.load_cache()
    message_service = MessageService(keyword_service)

    channel_id, message_id = -1001234567890, 42

    assert not await message_service.is_already_forwarded(channel_id, message_id)

    await message_service.mark_forwarded(channel_id, message_id, "React Native Developer")
    assert await message_service.is_already_forwarded(channel_id, message_id)

    # A different message in the same channel is not considered a duplicate.
    assert not await message_service.is_already_forwarded(channel_id, message_id + 1)


async def test_marking_forwarded_twice_does_not_raise():
    keyword_service = KeywordService()
    await keyword_service.load_cache()
    message_service = MessageService(keyword_service)

    await message_service.mark_forwarded(-100999, 1, "text")
    # UNIQUE(channel_id, message_id) + INSERT OR IGNORE - must be a no-op.
    await message_service.mark_forwarded(-100999, 1, "text")
