# skeleton/cache.py
import json
import redis
import logging
from skeleton.config import REDIS_HOST, REDIS_PORT

logger = logging.getLogger(__name__)

try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        decode_responses=True,
        socket_timeout=2.0,
        socket_connect_timeout=2.0
    )
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

def get_cache(key: str):
    """Retrieve cache value by key. Failsafe."""
    if redis_client is None:
        return None
    try:
        value = redis_client.get(key)
        return json.loads(value) if value else None
    except Exception as e:
        logger.warning(f"Redis get error: {e}")
        return None

def set_cache(key: str, value, ttl_seconds=300):
    """Set cache value with key and TTL. Failsafe."""
    if redis_client is None:
        return False
    try:
        redis_client.setex(
            key,
            ttl_seconds,
            json.dumps(value, default=str)
        )
        return True
    except Exception as e:
        logger.warning(f"Redis set error: {e}")
        return False

def invalidate_cache(pattern: str):
    """Invalidate all keys matching the glob pattern. Failsafe."""
    if redis_client is None:
        return
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
    except Exception as e:
        logger.warning(f"Redis delete/keys error: {e}")
