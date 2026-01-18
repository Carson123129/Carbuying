"""
Pydantic models for the FindingMyCar API
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class UserIntent(BaseModel):
    """Structured representation of user's car preferences"""
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    performance_priority: float = Field(default=0.5, ge=0, le=1)
    reliability_priority: float = Field(default=0.5, ge=0, le=1)
    comfort_priority: float = Field(default=0.5, ge=0, le=1)
    drivetrain: Optional[str] = None  # AWD, RWD, FWD
    body_style: Optional[str] = None  # sedan, coupe, hatchback, etc.
    emotional_tags: List[str] = Field(default_factory=list)
    negative_tags: List[str] = Field(default_factory=list)  # things to avoid
    reference_car: Optional[str] = None  # e.g., "BMW 340i 2018"
    usage: List[str] = Field(default_factory=list)  # daily, track, winter, etc.
    raw_query: str = ""


class PriceRange(BaseModel):
    min: int
    max: int


class Car(BaseModel):
    """Car model from the database"""
    id: str
    make: str
    model: str
    year: int
    trim: str
    price_range: PriceRange
    avg_price: int
    power_hp: int
    torque_lb_ft: int
    drivetrain: str
    body_type: str
    reliability_score: float
    ownership_cost_score: float
    driving_feel_tags: List[str]
    class_tags: List[str]
    emotional_tags: List[str]
    fuel_economy_mpg: int
    zero_to_sixty: float


class CarListing(BaseModel):
    """Individual listing for a car"""
    car_id: str
    price: int
    mileage: int
    location: str
    condition: str
    source: str
    url: str
    title: str


class MatchResult(BaseModel):
    """A car match with its score and reasoning"""
    car: Car
    match_score: float  # 0-100
    match_reasons: List[str]  # Why it matches
    tradeoffs: List[str]  # Where it differs
    listings: List[CarListing] = Field(default_factory=list)


class SearchRequest(BaseModel):
    """User's search query"""
    query: str
    refinements: Optional[List[str]] = None  # e.g., ["cheaper", "more reliable"]


class SearchResponse(BaseModel):
    """Response containing interpreted intent and matches"""
    interpreted_intent: UserIntent
    intent_summary: str  # Human-readable summary of what we understood
    matches: List[MatchResult]
    suggestions: List[str]  # Refinement suggestions


class RefinementRequest(BaseModel):
    """Request to refine existing search"""
    original_query: str
    previous_intent: UserIntent
    refinement: str  # e.g., "cheaper", "more reliable", "sportier"

