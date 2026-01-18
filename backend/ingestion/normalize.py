from typing import Dict, List


def combine_character_tags(car: Dict) -> List[str]:
    tags = []
    tags.extend(car.get("emotional_tags", []))
    tags.extend(car.get("driving_feel_tags", []))
    tags.extend(car.get("class_tags", []))
    return sorted({t.strip().lower() for t in tags if isinstance(t, str) and t.strip()})


def normalize_car_spec(car: Dict) -> Dict:
    return {
        "make": car["make"],
        "model": car["model"],
        "trim": car["trim"],
        "year": car["year"],
        "drivetrain": car.get("drivetrain"),
        "body_type": car.get("body_type"),
        "power_hp": car.get("power_hp"),
        "torque_lb_ft": car.get("torque_lb_ft"),
        "mpg_combined": car.get("fuel_economy_mpg"),
        "zero_to_sixty": car.get("zero_to_sixty"),
        "reliability_score": car.get("reliability_score"),
        "ownership_cost_score": car.get("ownership_cost_score"),
        "character_tags": combine_character_tags(car),
    }


def normalize_listing(listing: Dict) -> Dict:
    # MarketCheck uses city/state fields directly, fallback to "location"
    if listing.get("city") and listing.get("state"):
        city = listing.get("city")
        state = listing.get("state")
    else:
        city, state = None, None
    location = listing.get("location", "")
    if not city and "," in location:
        parts = [p.strip() for p in location.split(",", 1)]
        if len(parts) == 2:
            city, state = parts
    return {
        "source": listing.get("source", "mock"),
        "source_listing_id": listing.get("id") or listing.get("vin") or listing.get("url") or listing.get("title"),
        "title": listing.get("title"),
        "price": listing.get("price") or listing.get("list_price"),
        "mileage": listing.get("mileage") or listing.get("miles"),
        "location_city": city,
        "location_state": state,
        "condition": listing.get("condition") or listing.get("dom"),
        "url": listing.get("url") or listing.get("vdp_url"),
        "listed_at": listing.get("listed_at") or listing.get("first_seen_at"),
        "last_seen_at": listing.get("last_seen_at"),
        "status": "active",
    }

