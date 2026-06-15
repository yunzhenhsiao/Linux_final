# skeleton/cache.py
import json
import redis
import logging
from skeleton.config import REDIS_HOST, REDIS_PORT

logger = logging.getLogger(__name__)

# ── Redis client initialisation ────────────────────────────────────────────────
# Build the client and immediately ping to confirm the connection is live.
# redis.Redis() only creates an object; the actual TCP handshake happens on
# the first command, so without ping() a misconfigured host would go undetected.
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        decode_responses=True,
        socket_timeout=2.0,
        socket_connect_timeout=2.0
    )
    redis_client.ping()
    logger.info(f"Redis connected at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e} — cache layer disabled")
    redis_client = None


def get_cache(key: str):
    """Retrieve a cached value by key. Returns None on miss or error."""
    if redis_client is None:
        return None
    try:
        value = redis_client.get(key)
        return json.loads(value) if value else None
    except Exception as e:
        logger.warning(f"Redis get error: {e}")
        return None


def set_cache(key: str, value, ttl_seconds: int = 300) -> bool:
    """Persist a value under *key* for *ttl_seconds*. Returns True on success."""
    if redis_client is None:
        return False
    try:
        redis_client.setex(key, ttl_seconds, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.warning(f"Redis set error: {e}")
        return False


def invalidate_cache(pattern: str) -> None:
    """
    Delete all keys matching *pattern*.

    Uses SCAN instead of KEYS to avoid blocking the Redis event loop on
    large datasets. KEYS is O(N) and holds the server lock for its entire
    duration; SCAN iterates incrementally and is safe in production.
    """
    if redis_client is None:
        return
    try:
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        logger.warning(f"Redis scan/delete error: {e}")
