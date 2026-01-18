"""
Query API Routes for FindingMyCar AI Layer.

Provides endpoints for:
- Searching cars with filters
- Getting car profiles with listings
- Stats and metadata

These endpoints power the AI recommendation system.
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import joinedload
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import get_session, CarMaster, CarListing, CarProfile


# Pydantic models for API responses
class CarProfileSummary(BaseModel):
    """Summary of a car profile for search results."""
    id: int
    master_car_id: int
    make: str
    model: str
    year: int
    trim: Optional[str] = None
    body_type: Optional[str] = None
    
    # Stats
    avg_price: Optional[float] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    avg_mileage: Optional[float] = None
    count_listings: int = 0
    
    # Options
    drivetrain_options: List[str] = []
    engine_options: List[str] = []
    
    # MPG
    mpg_city_range: Optional[str] = None
    mpg_hwy_range: Optional[str] = None
    
    class Config:
        from_attributes = True


class ListingSummary(BaseModel):
    """Individual listing details."""
    id: int
    vin: str
    price: Optional[int] = None
    mileage: Optional[int] = None
    trim: Optional[str] = None
    
    # Location
    city: Optional[str] = None
    state: Optional[str] = None
    
    # Specs
    drivetrain: Optional[str] = None
    engine: Optional[str] = None
    exterior_color: Optional[str] = None
    
    # Links
    listing_url: Optional[str] = None
    photo_url: Optional[str] = None
    
    # Dealer
    dealer_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class CarProfileDetail(BaseModel):
    """Full car profile with listings."""
    id: int
    master_car_id: int
    make: str
    model: str
    year: int
    trim: Optional[str] = None
    body_type: Optional[str] = None
    
    # Full stats
    avg_price: Optional[float] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    median_price: Optional[float] = None
    
    avg_mileage: Optional[float] = None
    min_mileage: Optional[int] = None
    max_mileage: Optional[int] = None
    
    count_listings: int = 0
    
    # All options
    drivetrain_options: List[str] = []
    engine_options: List[str] = []
    transmission_options: List[str] = []
    color_options: List[str] = []
    
    # MPG
    mpg_city_min: Optional[int] = None
    mpg_city_max: Optional[int] = None
    mpg_hwy_min: Optional[int] = None
    mpg_hwy_max: Optional[int] = None
    
    # Live listings
    listings: List[ListingSummary] = []
    
    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Response for car search."""
    total: int
    page: int
    page_size: int
    results: List[CarProfileSummary]


class StatsResponse(BaseModel):
    """Database statistics."""
    master_cars: int
    listings: int
    profiles: int
    makes: List[str]
    year_range: dict


# Router
router = APIRouter(prefix="/cars", tags=["cars"])


def get_db():
    """Dependency for database session."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


@router.get("/search", response_model=SearchResponse)
async def search_cars(
    make: Optional[str] = Query(None, description="Filter by make"),
    model: Optional[str] = Query(None, description="Filter by model"),
    year_min: Optional[int] = Query(None, ge=1990, le=2030, description="Minimum year"),
    year_max: Optional[int] = Query(None, ge=1990, le=2030, description="Maximum year"),
    price_max: Optional[int] = Query(None, ge=0, description="Maximum average price"),
    price_min: Optional[int] = Query(None, ge=0, description="Minimum average price"),
    mileage_max: Optional[int] = Query(None, ge=0, description="Maximum average mileage"),
    drivetrain: Optional[str] = Query(None, description="Drivetrain (AWD, RWD, FWD, 4WD)"),
    body_type: Optional[str] = Query(None, description="Body type (Sedan, SUV, Truck, etc.)"),
    min_listings: int = Query(1, ge=1, description="Minimum number of listings"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    session=Depends(get_db)
):
    """
    Search car profiles with optional filters.
    
    Returns paginated list of car profiles with summary stats.
    Used by AI layer to find matching cars.
    """
    # Build query
    query = (
        select(CarProfile, CarMaster)
        .join(CarMaster, CarProfile.master_car_id == CarMaster.id)
        .where(CarProfile.count_listings >= min_listings)
    )
    
    # Apply filters
    if make:
        query = query.where(func.upper(CarMaster.make) == make.upper())
    
    if model:
        query = query.where(func.upper(CarMaster.model).contains(model.upper()))
    
    if year_min:
        query = query.where(CarMaster.year >= year_min)
    
    if year_max:
        query = query.where(CarMaster.year <= year_max)
    
    if price_max:
        query = query.where(CarProfile.avg_price <= price_max)
    
    if price_min:
        query = query.where(CarProfile.avg_price >= price_min)
    
    if mileage_max:
        query = query.where(CarProfile.avg_mileage <= mileage_max)
    
    if drivetrain:
        # Check if drivetrain is in the options array
        query = query.where(
            CarProfile.drivetrain_options.contains([drivetrain.upper()])
        )
    
    if body_type:
        query = query.where(
            func.upper(CarMaster.body_type) == body_type.upper()
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = session.execute(count_query).scalar() or 0
    
    # Apply pagination and ordering
    query = (
        query
        .order_by(CarProfile.count_listings.desc(), CarProfile.avg_price.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    
    results = session.execute(query).all()
    
    # Build response
    profiles = []
    for profile, master in results:
        mpg_city_range = None
        mpg_hwy_range = None
        
        if profile.mpg_city_min and profile.mpg_city_max:
            mpg_city_range = f"{profile.mpg_city_min}-{profile.mpg_city_max}"
        if profile.mpg_hwy_min and profile.mpg_hwy_max:
            mpg_hwy_range = f"{profile.mpg_hwy_min}-{profile.mpg_hwy_max}"
        
        profiles.append(CarProfileSummary(
            id=profile.id,
            master_car_id=master.id,
            make=master.make,
            model=master.model,
            year=master.year,
            trim=master.trim,
            body_type=master.body_type,
            avg_price=profile.avg_price,
            min_price=profile.min_price,
            max_price=profile.max_price,
            avg_mileage=profile.avg_mileage,
            count_listings=profile.count_listings,
            drivetrain_options=profile.drivetrain_options or [],
            engine_options=profile.engine_options or [],
            mpg_city_range=mpg_city_range,
            mpg_hwy_range=mpg_hwy_range,
        ))
    
    return SearchResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=profiles
    )


@router.get("/{car_id}", response_model=CarProfileDetail)
async def get_car_profile(
    car_id: int,
    max_listings: int = Query(20, ge=1, le=100, description="Max listings to return"),
    session=Depends(get_db)
):
    """
    Get full car profile with live listings.
    
    Returns complete stats and actual listings for a specific car.
    """
    # Get profile and master car
    result = session.execute(
        select(CarProfile, CarMaster)
        .join(CarMaster, CarProfile.master_car_id == CarMaster.id)
        .where(CarProfile.id == car_id)
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Car profile not found")
    
    profile, master = result
    
    # Get listings
    listings_query = (
        select(CarListing)
        .where(CarListing.master_car_id == master.id)
        .where(CarListing.price.isnot(None))
        .order_by(CarListing.price.asc())
        .limit(max_listings)
    )
    
    listings = session.execute(listings_query).scalars().all()
    
    listing_summaries = [
        ListingSummary(
            id=l.id,
            vin=l.vin,
            price=l.price,
            mileage=l.mileage,
            trim=l.trim,
            city=l.city,
            state=l.state,
            drivetrain=l.drivetrain,
            engine=l.engine,
            exterior_color=l.exterior_color,
            listing_url=l.listing_url,
            photo_url=l.photo_url,
            dealer_name=l.dealer_name,
        )
        for l in listings
    ]
    
    return CarProfileDetail(
        id=profile.id,
        master_car_id=master.id,
        make=master.make,
        model=master.model,
        year=master.year,
        trim=master.trim,
        body_type=master.body_type,
        avg_price=profile.avg_price,
        min_price=profile.min_price,
        max_price=profile.max_price,
        median_price=profile.median_price,
        avg_mileage=profile.avg_mileage,
        min_mileage=profile.min_mileage,
        max_mileage=profile.max_mileage,
        count_listings=profile.count_listings,
        drivetrain_options=profile.drivetrain_options or [],
        engine_options=profile.engine_options or [],
        transmission_options=profile.transmission_options or [],
        color_options=profile.color_options or [],
        mpg_city_min=profile.mpg_city_min,
        mpg_city_max=profile.mpg_city_max,
        mpg_hwy_min=profile.mpg_hwy_min,
        mpg_hwy_max=profile.mpg_hwy_max,
        listings=listing_summaries,
    )


@router.get("/by-master/{master_id}", response_model=CarProfileDetail)
async def get_car_by_master_id(
    master_id: int,
    max_listings: int = Query(20, ge=1, le=100),
    session=Depends(get_db)
):
    """
    Get car profile by master car ID.
    """
    result = session.execute(
        select(CarProfile, CarMaster)
        .join(CarMaster, CarProfile.master_car_id == CarMaster.id)
        .where(CarProfile.master_car_id == master_id)
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Car profile not found")
    
    profile, master = result
    
    # Reuse the same logic
    return await get_car_profile(profile.id, max_listings, session)


@router.get("/stats/overview", response_model=StatsResponse)
async def get_stats(session=Depends(get_db)):
    """
    Get database statistics.
    
    Useful for health checks and understanding data coverage.
    """
    master_count = session.query(CarMaster).count()
    listing_count = session.query(CarListing).count()
    profile_count = session.query(CarProfile).count()
    
    # Get unique makes
    makes = session.execute(
        select(CarMaster.make)
        .distinct()
        .order_by(CarMaster.make)
    ).scalars().all()
    
    # Year range
    min_year = session.query(func.min(CarMaster.year)).scalar()
    max_year = session.query(func.max(CarMaster.year)).scalar()
    
    return StatsResponse(
        master_cars=master_count,
        listings=listing_count,
        profiles=profile_count,
        makes=list(makes),
        year_range={"min": min_year, "max": max_year}
    )


@router.get("/makes", response_model=List[str])
async def get_makes(session=Depends(get_db)):
    """Get list of all available makes."""
    makes = session.execute(
        select(CarMaster.make)
        .distinct()
        .order_by(CarMaster.make)
    ).scalars().all()
    
    return list(makes)


@router.get("/models/{make}", response_model=List[str])
async def get_models_for_make(
    make: str,
    session=Depends(get_db)
):
    """Get list of models for a specific make."""
    models = session.execute(
        select(CarMaster.model)
        .where(func.upper(CarMaster.make) == make.upper())
        .distinct()
        .order_by(CarMaster.model)
    ).scalars().all()
    
    if not models:
        raise HTTPException(status_code=404, detail=f"No models found for make: {make}")
    
    return list(models)

