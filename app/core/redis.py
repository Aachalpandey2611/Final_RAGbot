import redis
from app.core.config import settings

# Create a connection pool for Redis to reuse connections efficiently
redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

def get_redis_client() -> redis.Redis:
    """
    Returns a Redis client instance.
    """
    return redis.Redis(connection_pool=redis_pool)
