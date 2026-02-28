"""
Redis client for admission control and caching.
Separated from business logic for clean architecture.
"""

import redis
from typing import Optional
from app.core.config import settings

class RedisClient:
    """Singleton Redis client with connection pooling."""
    
    _instance: Optional[redis.Redis] = None
    
    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get or create Redis client instance."""
        if cls._instance is None:
            cls._instance = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
        return cls._instance
    
    @classmethod
    def close(cls):
        """Close Redis connection."""
        if cls._instance:
            cls._instance.close()
            cls._instance = None

# Convenience function
def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    return RedisClient.get_client()
