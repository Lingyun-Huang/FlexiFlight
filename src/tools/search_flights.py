import os
import json
import logging
import hashlib
from serpapi import GoogleSearch
from models.serp import GoogleFlightsSearchParams
from clients.redis import get_redis_client


logger = logging.getLogger(__name__)

API_KEY = os.getenv("SERPAPI_KEY")


def _generate_cache_key(params: GoogleFlightsSearchParams) -> str:
    """Generate a cache key from search parameters."""
    payload = params.dict(exclude_none=True)
    # Sort keys for consistent hashing
    params_str = json.dumps(payload, sort_keys=True, default=str)
    param_hash = hashlib.sha256(params_str.encode()).hexdigest()
    return f"flight_search:{param_hash}"


def search_google_flights(params: GoogleFlightsSearchParams):
    """Search Google Flights using SerpAPI with the given parameters.

    Results are cached in Redis for the configured TTL (FLIGHT_CACHE_TTL).
    If Redis is unavailable, caching is skipped gracefully.
    """
    if not API_KEY:
        raise ValueError("SERPAPI_KEY environment variable is not set.")

    # Try to get from cache
    cache_key = _generate_cache_key(params)
    redis_client = get_redis_client()

    if redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for {cache_key}")
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}. Proceeding without cache.")

    # Perform API call if not cached
    payload = params.dict(exclude_none=True)
    payload["api_key"] = API_KEY
    payload["engine"] = "google_flights"
    search = GoogleSearch(payload)
    results = search.get_dict()
    logger.info(f"SerpAPI response: {results}")

    # Store in cache
    if redis_client:
        try:
            redis_client.set(cache_key, json.dumps(results))
            logger.debug(f"Cached result for {cache_key}")
        except Exception as e:
            logger.warning(
                f"Cache storage failed: {e}. Returning result without caching."
            )

    return results
