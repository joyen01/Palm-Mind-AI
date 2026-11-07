"""Shared Redis connection used for chat memory and booking drafts."""

from functools import lru_cache

from django.conf import settings
from redis import Redis


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)
