"""
Build Master Cars Database from NHTSA VPIC API.

This script pulls all makes and models from NHTSA for the last 25 years
and populates the cars_master table.

NHTSA VPIC API docs: https://vpic.nhtsa.dot.gov/api/

Usage:
    python build_master_cars.py
    python build_master_cars.py --year-start 2015 --year-end 2024
"""
import argparse
import time
from datetime import datetime
from typing import List, Dict, Optional
import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import get_session, CarMaster, init_db


# NHTSA API endpoints
NHTSA_BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles"
RATE_LIMIT_DELAY = 0.5  # seconds between requests


def get_all_makes() -> List[Dict]:
    """
    Fetch all vehicle makes from NHTSA.
    Returns list of {'Make_ID': int, 'Make_Name': str}
    """
    url = f"{NHTSA_BASE_URL}/GetAllMakes?format=json"
    
    with httpx.Client(timeout=30) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
    
    results = data.get("Results", [])
    print(f"Found {len(results)} total makes from NHTSA")
    return results


def get_models_for_make_year(make_id: int, year: int) -> List[Dict]:
    """
    Fetch all models for a specific make and year.
    Returns list of models with details.
    """
    url = f"{NHTSA_BASE_URL}/GetModelsForMakeIdYear/makeId/{make_id}/modelyear/{year}?format=json"
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        
        return data.get("Results", [])
    except Exception as e:
        print(f"  Error fetching models for make_id={make_id}, year={year}: {e}")
        return []


def get_vehicle_types_for_make(make_id: int) -> List[Dict]:
    """
    Get vehicle types (body types) for a make.
    """
    url = f"{NHTSA_BASE_URL}/GetVehicleTypesForMakeId/{make_id}?format=json"
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        
        return data.get("Results", [])
    except Exception:
        return []


# Common passenger vehicle makes to prioritize
PRIORITY_MAKES = {
    "ACURA", "ALFA ROMEO", "ASTON MARTIN", "AUDI", "BENTLEY", "BMW", "BUICK",
    "CADILLAC", "CHEVROLET", "CHRYSLER", "DODGE", "FERRARI", "FIAT", "FORD",
    "GENESIS", "GMC", "HONDA", "HYUNDAI", "INFINITI", "JAGUAR", "JEEP", "KIA",
    "LAMBORGHINI", "LAND ROVER", "LEXUS", "LINCOLN", "LOTUS", "MASERATI",
    "MAZDA", "MCLAREN", "MERCEDES-BENZ", "MINI", "MITSUBISHI", "NISSAN",
    "POLESTAR", "PORSCHE", "RAM", "RIVIAN", "ROLLS-ROYCE", "SUBARU", "SUZUKI",
    "TESLA", "TOYOTA", "VOLKSWAGEN", "VOLVO"
}


def filter_passenger_makes(makes: List[Dict]) -> List[Dict]:
    """
    Filter to common passenger vehicle makes.
    """
    filtered = [
        m for m in makes 
        if m.get("Make_Name", "").upper() in PRIORITY_MAKES
    ]
    print(f"Filtered to {len(filtered)} passenger vehicle makes")
    return filtered


def normalize_body_type(vehicle_type: str) -> Optional[str]:
    """
    Normalize NHTSA vehicle types to standard body types.
    """
    if not vehicle_type:
        return None
    
    vt = vehicle_type.upper()
    
    if "SEDAN" in vt or "PASSENGER" in vt:
        return "Sedan"
    elif "COUPE" in vt:
        return "Coupe"
    elif "HATCHBACK" in vt:
        return "Hatchback"
    elif "WAGON" in vt or "ESTATE" in vt:
        return "Wagon"
    elif "SUV" in vt or "UTILITY" in vt or "MULTIPURPOSE" in vt:
        return "SUV"
    elif "TRUCK" in vt or "PICKUP" in vt:
        return "Truck"
    elif "VAN" in vt or "MINIVAN" in vt:
        return "Van"
    elif "CONVERTIBLE" in vt:
        return "Convertible"
    elif "CROSSOVER" in vt:
        return "Crossover"
    else:
        return None


def build_master_cars(
    year_start: int = 2000,
    year_end: int = None,
    priority_only: bool = True
):
    """
    Main function to build the master cars database.
    
    Args:
        year_start: First model year to include
        year_end: Last model year to include (defaults to current year)
        priority_only: If True, only include common passenger vehicle makes
    """
    if year_end is None:
        year_end = datetime.now().year + 1  # Include next model year
    
    print(f"Building master cars database for years {year_start}-{year_end}")
    print("=" * 60)
    
    # Initialize database
    init_db()
    session = get_session()
    
    try:
        # Get all makes
        all_makes = get_all_makes()
        
        if priority_only:
            makes = filter_passenger_makes(all_makes)
        else:
            makes = all_makes
        
        total_inserted = 0
        total_updated = 0
        
        for make in makes:
            make_id = make.get("Make_ID")
            make_name = make.get("Make_Name", "").strip()
            
            if not make_id or not make_name:
                continue
            
            print(f"\nProcessing: {make_name}")
            
            # Get vehicle types for body type info
            vehicle_types = get_vehicle_types_for_make(make_id)
            default_body = None
            if vehicle_types:
                default_body = normalize_body_type(
                    vehicle_types[0].get("VehicleTypeName", "")
                )
            
            make_count = 0
            
            for year in range(year_start, year_end + 1):
                models = get_models_for_make_year(make_id, year)
                
                for model_data in models:
                    model_name = model_data.get("Model_Name", "").strip()
                    
                    if not model_name:
                        continue
                    
                    # Normalize make name (title case)
                    normalized_make = make_name.title()
                    if normalized_make.upper() == "BMW":
                        normalized_make = "BMW"
                    elif normalized_make.upper() == "GMC":
                        normalized_make = "GMC"
                    
                    # Check if exists
                    existing = session.execute(
                        select(CarMaster).where(
                            CarMaster.make == normalized_make,
                            CarMaster.model == model_name,
                            CarMaster.year == year,
                            CarMaster.trim.is_(None)
                        )
                    ).scalar_one_or_none()
                    
                    if existing:
                        # Update if needed
                        if default_body and not existing.body_type:
                            existing.body_type = default_body
                            total_updated += 1
                    else:
                        # Insert new
                        car = CarMaster(
                            make=normalized_make,
                            model=model_name,
                            year=year,
                            trim=None,
                            body_type=default_body
                        )
                        session.add(car)
                        total_inserted += 1
                        make_count += 1
                
                # Rate limiting
                time.sleep(RATE_LIMIT_DELAY)
            
            # Commit per make
            session.commit()
            print(f"  Added {make_count} models")
        
        print("\n" + "=" * 60)
        print(f"Build complete!")
        print(f"  New records inserted: {total_inserted}")
        print(f"  Existing records updated: {total_updated}")
        
        # Final count
        total_count = session.query(CarMaster).count()
        print(f"  Total cars in database: {total_count}")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build master cars database from NHTSA"
    )
    parser.add_argument(
        "--year-start", type=int, default=2000,
        help="First model year (default: 2000)"
    )
    parser.add_argument(
        "--year-end", type=int, default=None,
        help="Last model year (default: current year + 1)"
    )
    parser.add_argument(
        "--all-makes", action="store_true",
        help="Include all makes, not just common passenger vehicles"
    )
    
    args = parser.parse_args()
    
    build_master_cars(
        year_start=args.year_start,
        year_end=args.year_end,
        priority_only=not args.all_makes
    )

