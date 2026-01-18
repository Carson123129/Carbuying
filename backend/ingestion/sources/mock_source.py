import json
from pathlib import Path
from typing import Dict, List


DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "cars_database.json"


def fetch() -> Dict[str, List[Dict]]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    cars = data.get("cars", [])
    listings = data.get("listings", [])
    for listing in listings:
        listing["source"] = listing.get("source", "mock")
    return {"cars": cars, "listings": listings}


