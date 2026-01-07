import os
import logging
from serpapi import GoogleSearch
from models.serp import GoogleFlightsSearchParams

logger = logging.getLogger(__name__)

API_KEY = os.getenv("SERPAPI_KEY")

def search_google_flights(params: GoogleFlightsSearchParams):
    """Search Google Flights using SerpAPI with the given parameters."""
    if not API_KEY:
        raise ValueError("SERPAPI_KEY environment variable is not set.")
    payload = params.dict(exclude_none=True)
    payload["api_key"] = API_KEY
    search = GoogleSearch(payload)
    results = search.get_dict()
    logger.debug(f"SerpAPI response: {results}")
    return results
