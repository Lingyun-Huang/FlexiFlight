import os
import redis
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

redis_url = os.getenv("REDIS_URL")


@lru_cache(maxsize=1)
def get_redis_client():
    client = redis.from_url(redis_url)
    client.ping()
    return client