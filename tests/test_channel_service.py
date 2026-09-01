"""
tests/test_channel_service.py

Exercises ChannelService's in-memory cache against a real (temp) SQLite
database. Doesn't exercise add_channel() itself since that requires a live
Telethon client/connection - it goes through ChannelRepository directly
to seed data, the same way the real add_channel() would after resolving
an entity, and checks that the service's cache reflects it correctly.
"""

import pytest

from database.repositories import ChannelRepository
from services.channel_service import ChannelService

pytestmark = pytest.mark.usefixtures("test_db")


async def test_cache_only_contains_enabled_channels():
    repo = ChannelRepository()
    await repo.add(-1001111111111, "chan_one", "Channel One")
    await repo.add(-1001222222222, "chan_two", "Channel Two")
    await repo.set_enabled(-1001222222222, False)

    service = ChannelService(repo)
    await service.load_cache()

    assert service.is_enabled(-1001111111111)
    assert not service.is_enabled(-1001222222222)


async def test_get_channel_returns_cached_metadata():
    repo = ChannelRepository()
    await repo.add(-1001111111111, "chan_one", "Channel One")

    service = ChannelService(repo)
    await service.load_cache()

    channel = service.get_channel(-1001111111111)
    assert channel is not None
    assert channel.username == "chan_one"
    assert channel.title == "Channel One"


async def test_unknown_channel_is_not_enabled():
    service = ChannelService(ChannelRepository())
    await service.load_cache()
    assert not service.is_enabled(-1009999999999)
    assert service.get_channel(-1009999999999) is None


async def test_remove_channel_updates_cache():
    repo = ChannelRepository()
    await repo.add(-1001111111111, "chan_one", "Channel One")

    service = ChannelService(repo)
    await service.load_cache()
    assert service.is_enabled(-1001111111111)

    removed = await service.remove_channel(-1001111111111)
    assert removed
    assert not service.is_enabled(-1001111111111)


async def test_disable_then_enable_channel_updates_cache():
    repo = ChannelRepository()
    await repo.add(-1001111111111, "chan_one", "Channel One")

    service = ChannelService(repo)
    await service.load_cache()

    await service.set_enabled(-1001111111111, False)
    assert not service.is_enabled(-1001111111111)

    await service.set_enabled(-1001111111111, True)
    assert service.is_enabled(-1001111111111)
