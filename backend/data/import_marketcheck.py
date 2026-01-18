"""
Import Used Car Listings from Marketcheck API.

This script pulls live used car listings and stores them in car_listings table.
Supports pagination, rate limiting, and incremental updates.

Marketcheck API docs: https://apidocs.marketcheck.com/

Usage:
    python import_marketcheck.py
    python import_marketcheck.py --make Toyota --year-min 2018
    python import_marketcheck.py --limit 1000

Environment:
    MARKETCHECK_API_KEY - Your Marketcheck API key
"""
import argparse
import os
import time
from datetime import datetime
from typing import List, Dict, Optional, Generator
import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import get_session, CarListing, init_db


# Marketcheck API configuration
MARKETCHECK_BASE_URL = "https://mc-api.marketcheck.com/v2"
RATE_LIMIT_DELAY = 0.25  # 4 requests per second max
PAGE_SIZE = 50  # Max items per page


def get_api_key() -> str:
    """Get Marketcheck API key from environment."""
    key = os.getenv("MARKETCHECK_API_KEY")
    if not key:
        raise ValueError(
            "MARKETCHECK_API_KEY environment variable is required. "
            "Get your key at https://www.marketcheck.com/apis"
        )
    return key


def fetch_listings_page(
    api_key: str,
    start: int = 0,
    rows: int = PAGE_SIZE,
    make: Optional[str] = None,
    model: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    mileage_max: Optional[int] = None,
    state: Optional[str] = None,
) -> Dict:
    """
    Fetch a single page of listings from Marketcheck.
    
    Returns the full API response including metadata and listings.
    """
    url = f"{MARKETCHECK_BASE_URL}/search/car/active"
    
    params = {
        "api_key": api_key,
        "start": start,
        "rows": rows,
        "country": "US",
        "sold_status": "active",
    }
    
    # Optional filters
    if make:
        params["make"] = make
    if model:
        params["model"] = model
    if year_min:
        params["year_gte"] = year_min
    if year_max:
        params["year_lte"] = year_max
    if price_min:
        params["price_gte"] = price_min
    if price_max:
        params["price_lte"] = price_max
    if mileage_max:
        params["miles_lte"] = mileage_max
    if state:
        params["state"] = state
    
    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def fetch_all_listings(
    api_key: str,
    max_listings: int = 10000,
    **filters
) -> Generator[Dict, None, None]:
    """
    Generator that fetches all listings with pagination.
    
    Yields individual listing dictionaries.
    """
    start = 0
    total_fetched = 0
    
    while total_fetched < max_listings:
        print(f"  Fetching listings {start} to {start + PAGE_SIZE}...")
        
        try:
            data = fetch_listings_page(
                api_key=api_key,
                start=start,
                rows=PAGE_SIZE,
                **filters
            )
        except httpx.HTTPStatusError as e:
            print(f"  API error: {e.response.status_code} - {e.response.text}")
            break
        except Exception as e:
            print(f"  Request error: {e}")
            break
        
        listings = data.get("listings", [])
        num_found = data.get("num_found", 0)
        
        if not listings:
            print(f"  No more listings. Total available: {num_found}")
            break
        
        for listing in listings:
            yield listing
            total_fetched += 1
            
            if total_fetched >= max_listings:
                break
        
        start += PAGE_SIZE
        
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)
        
        # Check if we've fetched all available
        if start >= num_found:
            break
    
    print(f"  Total listings fetched: {total_fetched}")


def normalize_drivetrain(drivetrain: Optional[str]) -> Optional[str]:
    """Normalize drivetrain values to standard format."""
    if not drivetrain:
        return None
    
    dt = drivetrain.upper().replace("-", "").replace(" ", "")
    
    if dt in ("AWD", "ALWHEELDRIVE", "ALLWHEELDRIVE"):
        return "AWD"
    elif dt in ("4WD", "4X4", "FOURWHEELDRIVE"):
        return "4WD"
    elif dt in ("FWD", "FRONTWHEELDRIVE"):
        return "FWD"
    elif dt in ("RWD", "REARWHEELDRIVE"):
        return "RWD"
    else:
        return drivetrain[:20] if drivetrain else None


def normalize_body_type(body_type: Optional[str]) -> Optional[str]:
    """Normalize body type to standard format."""
    if not body_type:
        return None
    
    bt = body_type.upper()
    
    if "SEDAN" in bt:
        return "Sedan"
    elif "COUPE" in bt:
        return "Coupe"
    elif "HATCH" in bt:
        return "Hatchback"
    elif "WAGON" in bt or "ESTATE" in bt:
        return "Wagon"
    elif "SUV" in bt or "UTILITY" in bt:
        return "SUV"
    elif "TRUCK" in bt or "PICKUP" in bt:
        return "Truck"
    elif "VAN" in bt or "MINIVAN" in bt:
        return "Van"
    elif "CONVERTIBLE" in bt or "ROADSTER" in bt:
        return "Convertible"
    elif "CROSSOVER" in bt:
        return "Crossover"
    else:
        return body_type.title()[:100] if body_type else None


def parse_listing(listing: Dict) -> Optional[Dict]:
    """
    Parse a Marketcheck listing into our database format.
    
    Returns None if the listing is invalid/incomplete.
    """
    vin = listing.get("vin")
    if not vin or len(vin) != 17:
        return None
    
    # Required fields
    make = listing.get("make")
    model = listing.get("model")
    year = listing.get("year")
    
    if not all([make, model, year]):
        return None
    
    # Build details from nested objects
    build = listing.get("build", {}) or {}
    dealer = listing.get("dealer", {}) or {}
    
    # Extract MPG - might be in different places
    mpg_city = None
    mpg_hwy = None
    if build.get("city_mpg"):
        mpg_city = int(build["city_mpg"])
    if build.get("highway_mpg"):
        mpg_hwy = int(build["highway_mpg"])
    
    # Parse scraped timestamp
    scraped_at = None
    if listing.get("scraped_at_date"):
        try:
            scraped_at = datetime.fromisoformat(
                listing["scraped_at_date"].replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            pass
    
    return {
        "vin": vin.upper(),
        "make": make.strip().title(),
        "model": model.strip(),
        "year": int(year),
        "trim": listing.get("trim", "")[:200] if listing.get("trim") else None,
        "price": int(listing["price"]) if listing.get("price") else None,
        "mileage": int(listing["miles"]) if listing.get("miles") else None,
        "city": dealer.get("city", "")[:100] if dealer.get("city") else None,
        "state": dealer.get("state", "")[:50] if dealer.get("state") else None,
        "zip_code": dealer.get("zip", "")[:10] if dealer.get("zip") else None,
        "dealer_name": dealer.get("name", "")[:200] if dealer.get("name") else None,
        "dealer_id": str(dealer.get("id", ""))[:100] if dealer.get("id") else None,
        "drivetrain": normalize_drivetrain(build.get("drivetrain")),
        "engine": build.get("engine", "")[:200] if build.get("engine") else None,
        "transmission": build.get("transmission", "")[:100] if build.get("transmission") else None,
        "exterior_color": listing.get("exterior_color", "")[:50] if listing.get("exterior_color") else None,
        "interior_color": listing.get("interior_color", "")[:50] if listing.get("interior_color") else None,
        "mpg_city": mpg_city,
        "mpg_hwy": mpg_hwy,
        "body_type": normalize_body_type(build.get("body_type")),
        "doors": int(build["doors"]) if build.get("doors") else None,
        "listing_url": listing.get("vdp_url", "")[:2000] if listing.get("vdp_url") else None,
        "photo_url": listing.get("media", {}).get("photo_links", [""])[0][:2000] if listing.get("media") else None,
        "source": "marketcheck",
        "scraped_at": scraped_at,
    }


def upsert_listings(session, listings: List[Dict]) -> tuple:
    """
    Upsert listings into database.
    
    Returns (inserted_count, updated_count).
    """
    if not listings:
        return 0, 0
    
    inserted = 0
    updated = 0
    
    for listing_data in listings:
        vin = listing_data["vin"]
        
        # Check if exists
        existing = session.execute(
            select(CarListing).where(CarListing.vin == vin)
        ).scalar_one_or_none()
        
        if existing:
            # Update existing
            for key, value in listing_data.items():
                if value is not None:
                    setattr(existing, key, value)
            existing.last_updated = datetime.utcnow()
            updated += 1
        else:
            # Insert new
            listing = CarListing(**listing_data)
            session.add(listing)
            inserted += 1
    
    session.commit()
    return inserted, updated


def import_marketcheck_listings(
    max_listings: int = 10000,
    batch_size: int = 100,
    make: Optional[str] = None,
    model: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    price_max: Optional[int] = None,
    mileage_max: Optional[int] = None,
    state: Optional[str] = None,
):
    """
    Main function to import listings from Marketcheck.
    
    Args:
        max_listings: Maximum number of listings to import
        batch_size: Number of listings to batch before committing
        make: Filter by make
        model: Filter by model
        year_min: Minimum year filter
        year_max: Maximum year filter
        price_max: Maximum price filter
        mileage_max: Maximum mileage filter
        state: State filter (e.g., "CA", "TX")
    """
    print("Importing listings from Marketcheck API")
    print("=" * 60)
    
    api_key = get_api_key()
    
    # Initialize database
    init_db()
    session = get_session()
    
    filters = {
        k: v for k, v in {
            "make": make,
            "model": model,
            "year_min": year_min,
            "year_max": year_max,
            "price_max": price_max,
            "mileage_max": mileage_max,
            "state": state,
        }.items() if v is not None
    }
    
    if filters:
        print(f"Filters: {filters}")
    
    print(f"Max listings: {max_listings}")
    print()
    
    try:
        total_inserted = 0
        total_updated = 0
        total_skipped = 0
        batch = []
        
        for listing in fetch_all_listings(api_key, max_listings, **filters):
            parsed = parse_listing(listing)
            
            if parsed:
                batch.append(parsed)
            else:
                total_skipped += 1
            
            # Commit batch
            if len(batch) >= batch_size:
                inserted, updated = upsert_listings(session, batch)
                total_inserted += inserted
                total_updated += updated
                print(f"    Batch: +{inserted} new, ~{updated} updated")
                batch = []
        
        # Final batch
        if batch:
            inserted, updated = upsert_listings(session, batch)
            total_inserted += inserted
            total_updated += updated
        
        print("\n" + "=" * 60)
        print("Import complete!")
        print(f"  New listings inserted: {total_inserted}")
        print(f"  Existing listings updated: {total_updated}")
        print(f"  Invalid listings skipped: {total_skipped}")
        
        # Final count
        total_count = session.query(CarListing).count()
        print(f"  Total listings in database: {total_count}")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import used car listings from Marketcheck API"
    )
    parser.add_argument(
        "--limit", type=int, default=10000,
        help="Maximum listings to import (default: 10000)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=100,
        help="Batch size for database commits (default: 100)"
    )
    parser.add_argument(
        "--make", type=str,
        help="Filter by make (e.g., Toyota)"
    )
    parser.add_argument(
        "--model", type=str,
        help="Filter by model (e.g., Camry)"
    )
    parser.add_argument(
        "--year-min", type=int,
        help="Minimum model year"
    )
    parser.add_argument(
        "--year-max", type=int,
        help="Maximum model year"
    )
    parser.add_argument(
        "--price-max", type=int,
        help="Maximum price"
    )
    parser.add_argument(
        "--mileage-max", type=int,
        help="Maximum mileage"
    )
    parser.add_argument(
        "--state", type=str,
        help="State filter (e.g., CA)"
    )
    
    args = parser.parse_args()
    
    import_marketcheck_listings(
        max_listings=args.limit,
        batch_size=args.batch_size,
        make=args.make,
        model=args.model,
        year_min=args.year_min,
        year_max=args.year_max,
        price_max=args.price_max,
        mileage_max=args.mileage_max,
        state=args.state,
    )

