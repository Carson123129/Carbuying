"""
Build Aggregated Car Profiles.

This script computes summary statistics for each master car
based on its associated listings.

Creates/updates car_profiles table with:
- Price stats (avg, min, max, median)
- Mileage stats
- Available options (drivetrains, engines, colors)
- MPG ranges
- Listing counts

Usage:
    python build_profiles.py
    python build_profiles.py --min-listings 3
"""
import argparse
from datetime import datetime
from typing import List, Dict, Optional
from statistics import median
from collections import Counter
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import get_session, CarMaster, CarListing, CarProfile, init_db


def compute_profile_for_master_car(
    session,
    master_car_id: int,
    min_listings: int = 1
) -> Optional[Dict]:
    """
    Compute profile stats for a single master car.
    
    Returns profile data dict or None if not enough listings.
    """
    # Get all listings for this master car
    listings = session.execute(
        select(CarListing).where(
            and_(
                CarListing.master_car_id == master_car_id,
                CarListing.price.isnot(None),
                CarListing.price > 0
            )
        )
    ).scalars().all()
    
    if len(listings) < min_listings:
        return None
    
    # Extract values
    prices = [l.price for l in listings if l.price and l.price > 0]
    mileages = [l.mileage for l in listings if l.mileage and l.mileage > 0]
    
    drivetrains = [l.drivetrain for l in listings if l.drivetrain]
    engines = [l.engine for l in listings if l.engine]
    transmissions = [l.transmission for l in listings if l.transmission]
    colors = [l.exterior_color for l in listings if l.exterior_color]
    
    mpg_city = [l.mpg_city for l in listings if l.mpg_city and l.mpg_city > 0]
    mpg_hwy = [l.mpg_hwy for l in listings if l.mpg_hwy and l.mpg_hwy > 0]
    
    # Compute stats
    profile_data = {
        "master_car_id": master_car_id,
        "count_listings": len(listings),
        "computed_at": datetime.utcnow(),
    }
    
    # Price stats
    if prices:
        profile_data["avg_price"] = sum(prices) / len(prices)
        profile_data["min_price"] = min(prices)
        profile_data["max_price"] = max(prices)
        profile_data["median_price"] = median(prices)
    
    # Mileage stats
    if mileages:
        profile_data["avg_mileage"] = sum(mileages) / len(mileages)
        profile_data["min_mileage"] = min(mileages)
        profile_data["max_mileage"] = max(mileages)
    
    # Options - get unique values, sorted by frequency
    def get_top_options(values: List[str], limit: int = 10) -> List[str]:
        if not values:
            return []
        counts = Counter(values)
        return [v for v, _ in counts.most_common(limit)]
    
    profile_data["drivetrain_options"] = get_top_options(drivetrains, 5)
    profile_data["engine_options"] = get_top_options(engines, 10)
    profile_data["transmission_options"] = get_top_options(transmissions, 5)
    profile_data["color_options"] = get_top_options(colors, 15)
    
    # MPG ranges
    if mpg_city:
        profile_data["mpg_city_min"] = min(mpg_city)
        profile_data["mpg_city_max"] = max(mpg_city)
    
    if mpg_hwy:
        profile_data["mpg_hwy_min"] = min(mpg_hwy)
        profile_data["mpg_hwy_max"] = max(mpg_hwy)
    
    return profile_data


def upsert_profile(session, profile_data: Dict) -> str:
    """
    Insert or update a car profile.
    
    Returns "inserted" or "updated".
    """
    master_car_id = profile_data["master_car_id"]
    
    existing = session.execute(
        select(CarProfile).where(CarProfile.master_car_id == master_car_id)
    ).scalar_one_or_none()
    
    if existing:
        for key, value in profile_data.items():
            if key != "master_car_id":
                setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        return "updated"
    else:
        profile = CarProfile(**profile_data)
        session.add(profile)
        return "inserted"


def build_profiles(
    min_listings: int = 1,
    batch_size: int = 100
):
    """
    Main function to build all car profiles.
    
    Args:
        min_listings: Minimum listings required to create a profile
        batch_size: Number of profiles to batch before committing
    """
    print("Building car profiles")
    print("=" * 60)
    print(f"Minimum listings per profile: {min_listings}")
    print()
    
    init_db()
    session = get_session()
    
    try:
        # Get all master cars that have listings
        master_cars_with_listings = session.execute(
            select(CarMaster.id).where(
                CarMaster.id.in_(
                    select(CarListing.master_car_id).where(
                        CarListing.master_car_id.isnot(None)
                    ).distinct()
                )
            )
        ).scalars().all()
        
        total = len(master_cars_with_listings)
        print(f"Master cars with listings: {total}")
        
        inserted = 0
        updated = 0
        skipped = 0
        
        for i, master_id in enumerate(master_cars_with_listings):
            profile_data = compute_profile_for_master_car(
                session,
                master_id,
                min_listings=min_listings
            )
            
            if profile_data:
                result = upsert_profile(session, profile_data)
                if result == "inserted":
                    inserted += 1
                else:
                    updated += 1
            else:
                skipped += 1
            
            # Commit batch
            if (i + 1) % batch_size == 0:
                session.commit()
                print(f"  Processed {i + 1}/{total} cars...")
        
        # Final commit
        session.commit()
        
        print("\n" + "=" * 60)
        print("Profile build complete!")
        print(f"  Profiles inserted: {inserted}")
        print(f"  Profiles updated: {updated}")
        print(f"  Skipped (< {min_listings} listings): {skipped}")
        
        # Final count
        total_profiles = session.query(CarProfile).count()
        print(f"  Total profiles in database: {total_profiles}")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


def get_profile_stats(session) -> dict:
    """Get current profile statistics."""
    total_profiles = session.query(CarProfile).count()
    
    # Avg listings per profile
    avg_listings = session.query(
        func.avg(CarProfile.count_listings)
    ).scalar() or 0
    
    # Price range
    min_price = session.query(func.min(CarProfile.min_price)).scalar()
    max_price = session.query(func.max(CarProfile.max_price)).scalar()
    
    return {
        "total_profiles": total_profiles,
        "avg_listings_per_profile": round(avg_listings, 1),
        "price_range": {
            "min": min_price,
            "max": max_price
        }
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build aggregated car profiles from listings"
    )
    parser.add_argument(
        "--min-listings", type=int, default=1,
        help="Minimum listings required to create a profile (default: 1)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=100,
        help="Batch size for commits (default: 100)"
    )
    
    args = parser.parse_args()
    
    build_profiles(
        min_listings=args.min_listings,
        batch_size=args.batch_size
    )

