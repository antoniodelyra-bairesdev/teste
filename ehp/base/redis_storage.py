import redis
from redis.exceptions import ConnectionError

from ehp.config import settings


redis_client = redis.Redis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True
)


def get_redis_client() -> redis.Redis:
    global redis_client
    if not redis_client:
        raise ConnectionError("Redis client not initialized")
    return redis_client
