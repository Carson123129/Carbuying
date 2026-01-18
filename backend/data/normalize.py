"""
Normalization Layer for FindingMyCar.

This script matches car_listings to cars_master records,
normalizing make/model/year differences.

Handles:
- Case normalization
- Abbreviation expansion
- Trim naming differences
- Fuzzy matching for near-matches

Usage:
    python normalize.py
    python normalize.py --threshold 0.85
"""
import argparse
import re
from datetime import datetime
from typing import Optional, Tuple, List
from difflib import SequenceMatcher
from sqlalchemy import select, func, and_

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import get_session, CarMaster, CarListing, init_db


# Common abbreviations and aliases
MAKE_ALIASES = {
    "MERCEDES": "Mercedes-Benz",
    "MERCEDES BENZ": "Mercedes-Benz",
    "MERCEDES-BENZ": "Mercedes-Benz",
    "MB": "Mercedes-Benz",
    "VW": "Volkswagen",
    "CHEVY": "Chevrolet",
    "LAND ROVER": "Land Rover",
    "LANDROVER": "Land Rover",
    "ALFA ROMEO": "Alfa Romeo",
    "ALFA": "Alfa Romeo",
    "ASTON MARTIN": "Aston Martin",
    "ROLLS ROYCE": "Rolls-Royce",
    "ROLLS-ROYCE": "Rolls-Royce",
}

MODEL_ALIASES = {
    # BMW
    "3 SERIES": "3 Series",
    "4 SERIES": "4 Series",
    "5 SERIES": "5 Series",
    "7 SERIES": "7 Series",
    "X3": "X3",
    "X5": "X5",
    # Mercedes
    "C CLASS": "C-Class",
    "C-CLASS": "C-Class",
    "E CLASS": "E-Class",
    "E-CLASS": "E-Class",
    "S CLASS": "S-Class",
    "S-CLASS": "S-Class",
    "GLC CLASS": "GLC-Class",
    "GLC-CLASS": "GLC-Class",
    "GLE CLASS": "GLE-Class",
    "GLE-CLASS": "GLE-Class",
    # Common normalizations
    "CIVIC SI": "Civic Si",
    "CIVIC TYPE R": "Civic Type R",
    "MUSTANG GT": "Mustang",  # Base model
}


def normalize_make(make: str) -> str:
    """
    Normalize make name to standard format.
    """
    if not make:
        return make
    
    upper_make = make.upper().strip()
    
    # Check aliases
    if upper_make in MAKE_ALIASES:
        return MAKE_ALIASES[upper_make]
    
    # Title case with special handling
    normalized = make.strip().title()
    
    # Fix specific brands
    if normalized.upper() == "BMW":
        return "BMW"
    elif normalized.upper() == "GMC":
        return "GMC"
    elif normalized.upper() == "RAM":
        return "Ram"
    elif normalized.upper() == "MINI":
        return "MINI"
    
    return normalized


def normalize_model(model: str) -> str:
    """
    Normalize model name.
    """
    if not model:
        return model
    
    upper_model = model.upper().strip()
    
    # Check aliases
    if upper_model in MODEL_ALIASES:
        return MODEL_ALIASES[upper_model]
    
    # Clean up
    normalized = model.strip()
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized


def similarity_score(s1: str, s2: str) -> float:
    """
    Calculate similarity between two strings.
    Returns 0-1 score.
    """
    if not s1 or not s2:
        return 0.0
    
    return SequenceMatcher(
        None, 
        s1.upper(), 
        s2.upper()
    ).ratio()


def find_master_car(
    session,
    make: str,
    model: str,
    year: int,
    trim: Optional[str] = None,
    threshold: float = 0.8
) -> Optional[Tuple[int, float]]:
    """
    Find the best matching master car for a listing.
    
    Returns (master_car_id, confidence_score) or None.
    """
    normalized_make = normalize_make(make)
    normalized_model = normalize_model(model)
    
    # Try exact match first
    exact_match = session.execute(
        select(CarMaster).where(
            and_(
                func.upper(CarMaster.make) == normalized_make.upper(),
                func.upper(CarMaster.model) == normalized_model.upper(),
                CarMaster.year == year
            )
        )
    ).scalars().first()
    
    if exact_match:
        return (exact_match.id, 1.0)
    
    # Try fuzzy match on model
    candidates = session.execute(
        select(CarMaster).where(
            and_(
                func.upper(CarMaster.make) == normalized_make.upper(),
                CarMaster.year == year
            )
        )
    ).scalars().all()
    
    best_match = None
    best_score = 0.0
    
    for candidate in candidates:
        score = similarity_score(normalized_model, candidate.model)
        
        if score > best_score and score >= threshold:
            best_score = score
            best_match = candidate
    
    if best_match:
        return (best_match.id, best_score)
    
    # Try same make, any model (for new models not in NHTSA yet)
    # Lower confidence
    any_model_match = session.execute(
        select(CarMaster).where(
            and_(
                func.upper(CarMaster.make) == normalized_make.upper(),
                CarMaster.year == year
            )
        ).limit(1)
    ).scalars().first()
    
    if any_model_match:
        # Very low confidence - just same make/year
        return (any_model_match.id, 0.3)
    
    return None


def normalize_listings(
    threshold: float = 0.8,
    batch_size: int = 500,
    force_rematch: bool = False
):
    """
    Main function to normalize all listings and match to master cars.
    
    Args:
        threshold: Minimum similarity score for fuzzy matching (0-1)
        batch_size: Number of listings to process before committing
        force_rematch: If True, re-match all listings even if already matched
    """
    print("Normalizing car listings")
    print("=" * 60)
    print(f"Match threshold: {threshold}")
    print(f"Force rematch: {force_rematch}")
    print()
    
    init_db()
    session = get_session()
    
    try:
        # Get listings to process
        if force_rematch:
            query = select(CarListing)
        else:
            query = select(CarListing).where(CarListing.master_car_id.is_(None))
        
        listings = session.execute(query).scalars().all()
        total = len(listings)
        
        print(f"Listings to process: {total}")
        
        matched = 0
        unmatched = 0
        high_confidence = 0
        low_confidence = 0
        
        for i, listing in enumerate(listings):
            result = find_master_car(
                session,
                make=listing.make,
                model=listing.model,
                year=listing.year,
                trim=listing.trim,
                threshold=threshold
            )
            
            if result:
                master_id, confidence = result
                listing.master_car_id = master_id
                matched += 1
                
                if confidence >= 0.9:
                    high_confidence += 1
                else:
                    low_confidence += 1
            else:
                listing.master_car_id = None
                unmatched += 1
            
            # Commit batch
            if (i + 1) % batch_size == 0:
                session.commit()
                print(f"  Processed {i + 1}/{total} listings...")
        
        # Final commit
        session.commit()
        
        print("\n" + "=" * 60)
        print("Normalization complete!")
        print(f"  Matched listings: {matched}")
        print(f"    High confidence (≥90%): {high_confidence}")
        print(f"    Lower confidence: {low_confidence}")
        print(f"  Unmatched listings: {unmatched}")
        
        if total > 0:
            print(f"  Match rate: {matched/total*100:.1f}%")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


def get_match_stats(session) -> dict:
    """Get current matching statistics."""
    total = session.query(CarListing).count()
    matched = session.query(CarListing).filter(
        CarListing.master_car_id.isnot(None)
    ).count()
    unmatched = total - matched
    
    return {
        "total_listings": total,
        "matched": matched,
        "unmatched": unmatched,
        "match_rate": matched / total if total > 0 else 0
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Normalize listings and match to master cars"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.8,
        help="Minimum similarity score for fuzzy matching (default: 0.8)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=500,
        help="Batch size for commits (default: 500)"
    )
    parser.add_argument(
        "--force-rematch", action="store_true",
        help="Re-match all listings, even those already matched"
    )
    
    args = parser.parse_args()
    
    normalize_listings(
        threshold=args.threshold,
        batch_size=args.batch_size,
        force_rematch=args.force_rematch
    )

