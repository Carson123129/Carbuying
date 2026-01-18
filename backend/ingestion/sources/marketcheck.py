from typing import Dict, List
import httpx

from ingestion.config import marketcheck_config


def fetch() -> Dict[str, List[Dict]]:
    config = marketcheck_config()
    api_key = config["api_key"]
    if not api_key:
        raise ValueError("MARKETCHECK_API_KEY is missing in .env")

    params = {
        "api_key": api_key,
        "country": config["country"],
        "radius": config["radius"],
        "rows": config["rows"],
        "start": config["start"],
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.get(f"{config['base_url']}/search", params=params)
        response.raise_for_status()
        data = response.json()

    listings = data.get("listings", [])
    return {"cars": [], "listings": listings}

