"""
SQLAlchemy models for FindingMyCar data layer.

Tables:
- cars_master: Canonical list of all cars from NHTSA
- car_listings: Live used car listings from Marketcheck
- car_profiles: Aggregated stats per master car
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    ForeignKey, Text, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.postgresql import ARRAY
import os

Base = declarative_base()


class CarMaster(Base):
    """
    Master list of all cars from NHTSA VPIC API.
    One row per unique make/model/year/trim combination.
    """
    __tablename__ = "cars_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    make = Column(String(100), nullable=False, index=True)
    model = Column(String(200), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    trim = Column(String(200), nullable=True)
    body_type = Column(String(100), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    listings = relationship("CarListing", back_populates="master_car")
    profile = relationship("CarProfile", back_populates="master_car", uselist=False)
    
    __table_args__ = (
        UniqueConstraint("make", "model", "year", "trim", name="uq_car_master"),
        Index("ix_cars_master_make_model_year", "make", "model", "year"),
    )

    def __repr__(self):
        return f"<CarMaster {self.year} {self.make} {self.model}>"


class CarListing(Base):
    """
    Live used car listings from Marketcheck API.
    Each row is a real listing with price, mileage, dealer info.
    """
    __tablename__ = "car_listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vin = Column(String(17), unique=True, nullable=False, index=True)
    
    # Car details
    make = Column(String(100), nullable=False, index=True)
    model = Column(String(200), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    trim = Column(String(200), nullable=True)
    
    # Listing details
    price = Column(Integer, nullable=True, index=True)  # USD
    mileage = Column(Integer, nullable=True, index=True)
    
    # Location
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True, index=True)
    zip_code = Column(String(10), nullable=True)
    
    # Dealer
    dealer_name = Column(String(200), nullable=True)
    dealer_id = Column(String(100), nullable=True)
    
    # Specs
    drivetrain = Column(String(20), nullable=True)  # AWD, RWD, FWD, 4WD
    engine = Column(String(200), nullable=True)
    transmission = Column(String(100), nullable=True)
    exterior_color = Column(String(50), nullable=True)
    interior_color = Column(String(50), nullable=True)
    
    # Fuel economy
    mpg_city = Column(Integer, nullable=True)
    mpg_hwy = Column(Integer, nullable=True)
    
    # Body
    body_type = Column(String(100), nullable=True)
    doors = Column(Integer, nullable=True)
    
    # Listing metadata
    listing_url = Column(Text, nullable=True)
    photo_url = Column(Text, nullable=True)
    source = Column(String(50), default="marketcheck")
    
    # Timestamps
    scraped_at = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Foreign key to master car
    master_car_id = Column(Integer, ForeignKey("cars_master.id"), nullable=True, index=True)
    master_car = relationship("CarMaster", back_populates="listings")
    
    __table_args__ = (
        Index("ix_car_listings_price_mileage", "price", "mileage"),
        Index("ix_car_listings_make_model_year", "make", "model", "year"),
    )

    def __repr__(self):
        return f"<CarListing {self.year} {self.make} {self.model} ${self.price}>"


class CarProfile(Base):
    """
    Aggregated stats for each master car.
    Built from grouping all listings by master_car_id.
    """
    __tablename__ = "car_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    master_car_id = Column(Integer, ForeignKey("cars_master.id"), unique=True, nullable=False)
    
    # Price stats
    avg_price = Column(Float, nullable=True)
    min_price = Column(Integer, nullable=True)
    max_price = Column(Integer, nullable=True)
    median_price = Column(Float, nullable=True)
    
    # Mileage stats
    avg_mileage = Column(Float, nullable=True)
    min_mileage = Column(Integer, nullable=True)
    max_mileage = Column(Integer, nullable=True)
    
    # Count
    count_listings = Column(Integer, default=0)
    
    # Available options (stored as JSON arrays)
    drivetrain_options = Column(JSON, default=list)  # ["AWD", "RWD", "FWD"]
    engine_options = Column(JSON, default=list)  # ["2.0L Turbo", "3.0L V6"]
    transmission_options = Column(JSON, default=list)
    color_options = Column(JSON, default=list)
    
    # MPG range
    mpg_city_min = Column(Integer, nullable=True)
    mpg_city_max = Column(Integer, nullable=True)
    mpg_hwy_min = Column(Integer, nullable=True)
    mpg_hwy_max = Column(Integer, nullable=True)
    
    # Timestamps
    computed_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    master_car = relationship("CarMaster", back_populates="profile")

    def __repr__(self):
        return f"<CarProfile master_car_id={self.master_car_id} count={self.count_listings}>"


# Database connection utilities
def get_database_url() -> str:
    """Get database URL from environment or use default."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/findingmycar"
    )


def get_engine():
    """Create SQLAlchemy engine."""
    url = get_database_url()
    # Handle Render's postgres:// vs postgresql:// URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return create_engine(url, echo=False, pool_pre_ping=True)


def get_session():
    """Create a new database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    """Create all tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    init_db()

