"""
Redis caching service for event listings.

CACHING STRATEGY
================

What we cache:
  - Event listing responses (paginated, JSON-serialized)
  - Cache key pattern: "events:list:page={page}&size={size}&upcoming={upcoming}"

Why:
  - Event listings are the most frequent read operation
  - The data changes infrequently (only on new events or bookings)
  - Serving from Redis: ~1ms vs PostgreSQL: ~15-50ms

Invalidation strategy:
  - On booking: Delete all event list cache keys (booking changes available_seats)
  - On event creation: Delete all event list cache keys
  - TTL-based expiry as safety net (5 minutes)

  We use key-prefix-based invalidation:
  All event list keys start with "events:list:" so we can SCAN and delete them.

  Trade-off: SCAN is O(N) on Redis keyspace but with our small keyspace
  (maybe 50-100 cached pages max) this is negligible (~0.1ms).

  For production at massive scale, you'd use Redis pub/sub or a message queue
  for cache invalidation instead of SCAN.

Why NOT cache individual events:
  - Individual event reads are less frequent
  - Booking service needs real-time seat counts (stale data = overbooking)
  - The complexity of keeping per-event cache consistent isn't worth it
"""

import json
from typing import Optional

import redis.asyncio as redis
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    """Get or create Redis connection. Returns None if Redis is disabled."""
    global _redis_client

    if not settings.REDIS_ENABLED:
        return None

    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            # Test connection
            await _redis_client.ping()
            logger.info("redis_connected", url=settings.REDIS_URL)
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            _redis_client = None
            return None

    return _redis_client


async def close_redis() -> None:
    """Close Redis connection on shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


def _make_event_list_key(page: int, page_size: int, upcoming_only: bool) -> str:
    return f"events:list:page={page}&size={page_size}&upcoming={upcoming_only}"


async def get_cached_events(page: int, page_size: int, upcoming_only: bool) -> Optional[dict]:
    """Retrieve cached event list response."""
    client = await get_redis()
    if not client:
        return None

    key = _make_event_list_key(page, page_size, upcoming_only)
    try:
        data = await client.get(key)
        if data:
            logger.debug("cache_hit", key=key)
            return json.loads(data)
        logger.debug("cache_miss", key=key)
    except Exception as e:
        logger.error("cache_get_error", key=key, error=str(e))

    return None


async def set_cached_events(
    page: int,
    page_size: int,
    upcoming_only: bool,
    data: dict,
) -> None:
    """Cache event list response with TTL."""
    client = await get_redis()
    if not client:
        return

    key = _make_event_list_key(page, page_size, upcoming_only)
    try:
        await client.setex(key, settings.REDIS_CACHE_TTL, json.dumps(data, default=str))
        logger.debug("cache_set", key=key, ttl=settings.REDIS_CACHE_TTL)
    except Exception as e:
        logger.error("cache_set_error", key=key, error=str(e))


async def invalidate_event_cache() -> None:
    """
    Invalidate all cached event listings.
    Uses SCAN to find and delete all keys matching the prefix.
    """
    client = await get_redis()
    if not client:
        return

    try:
        deleted = 0
        async for key in client.scan_iter(match="events:list:*", count=100):
            await client.delete(key)
            deleted += 1
        logger.info("cache_invalidated", keys_deleted=deleted)
    except Exception as e:
        logger.error("cache_invalidation_error", error=str(e))


async def get_cache_stats() -> dict:
    """Get Redis cache statistics for monitoring."""
    client = await get_redis()
    if not client:
        return {"status": "disabled"}

    try:
        info = await client.info("stats")
        keyspace = await client.info("keyspace")
        return {
            "status": "connected",
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                round(
                    info.get("keyspace_hits", 0)
                    / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                    * 100,
                    2,
                )
            ),
            "keys": keyspace,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
