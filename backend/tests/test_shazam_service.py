import pytest
from fakeredis import aioredis

from src.services.shazam_service import ShazamService


@pytest.mark.asyncio
async def test_recognition_rate_limit_blocks_after_ten_requests():
    """Ensure normal users hit the 10 req/min recognition limit."""

    redis_client = aioredis.FakeRedis(decode_responses=True, encoding="utf-8")
    service = ShazamService(redis_client=redis_client)

    for _ in range(10):
        allowed, retry_after = await service.consume_rate_limit(user_id=123)
        assert allowed is True
        assert retry_after == 0

    allowed, retry_after = await service.consume_rate_limit(user_id=123)
    assert allowed is False
    assert retry_after > 0


@pytest.mark.asyncio
async def test_is_rate_limited_matches_consume_state():
    """Boolean helper should reflect counter state after limit is exceeded."""

    redis_client = aioredis.FakeRedis(decode_responses=True, encoding="utf-8")
    service = ShazamService(redis_client=redis_client)

    for _ in range(11):
        await service.consume_rate_limit(user_id=456)

    assert await service.is_rate_limited(user_id=456) is True


@pytest.mark.asyncio
async def test_vip_users_receive_higher_recognition_limit():
    """VIP roles should have a larger allowance (100 req/min)."""

    redis_client = aioredis.FakeRedis(decode_responses=True, encoding="utf-8")
    service = ShazamService(redis_client=redis_client)

    for _ in range(50):
        allowed, retry_after = await service.consume_rate_limit(user_id=789, user_role="vip")
        assert allowed is True
        assert retry_after == 0

    assert await service.is_rate_limited(user_id=789, user_role="vip") is False