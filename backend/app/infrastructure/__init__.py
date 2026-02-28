"""
Infrastructure layer - external system integrations.
Keeps business logic clean from implementation details.
"""

from .redis_client import get_redis, RedisClient

__all__ = ['get_redis', 'RedisClient']
