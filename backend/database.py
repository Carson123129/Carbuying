"""
Database handler for the FindingMyCar app
Loads and provides access to the car knowledge base
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from models import Car, CarListing, PriceRange


class CarDatabase:
    """Handles loading and querying the car database"""
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = Path(__file__).parent / "data" / "cars_database.json"
        self.data_path = Path(data_path)
        self._cars: List[Car] = []
        self._listings: List[CarListing] = []
        self._cars_by_id: Dict[str, Car] = {}
        self._load_data()
    
    def _load_data(self):
        """Load cars and listings from JSON file"""
        with open(self.data_path, 'r') as f:
            data = json.load(f)
        
        # Parse cars
        for car_data in data.get('cars', []):
            car = Car(
                id=car_data['id'],
                make=car_data['make'],
                model=car_data['model'],
                year=car_data['year'],
                trim=car_data['trim'],
                price_range=PriceRange(**car_data['price_range']),
                avg_price=car_data['avg_price'],
                power_hp=car_data['power_hp'],
                torque_lb_ft=car_data['torque_lb_ft'],
                drivetrain=car_data['drivetrain'],
                body_type=car_data['body_type'],
                reliability_score=car_data['reliability_score'],
                ownership_cost_score=car_data['ownership_cost_score'],
                driving_feel_tags=car_data['driving_feel_tags'],
                class_tags=car_data['class_tags'],
                emotional_tags=car_data['emotional_tags'],
                fuel_economy_mpg=car_data['fuel_economy_mpg'],
                zero_to_sixty=car_data['zero_to_sixty']
            )
            self._cars.append(car)
            self._cars_by_id[car.id] = car
        
        # Parse listings
        for listing_data in data.get('listings', []):
            listing = CarListing(**listing_data)
            self._listings.append(listing)
    
    def get_all_cars(self) -> List[Car]:
        """Get all cars in the database"""
        return self._cars
    
    def get_car_by_id(self, car_id: str) -> Optional[Car]:
        """Get a specific car by ID"""
        return self._cars_by_id.get(car_id)
    
    def get_listings_for_car(self, car_id: str) -> List[CarListing]:
        """Get all listings for a specific car"""
        return [l for l in self._listings if l.car_id == car_id]
    
    def get_all_listings(self) -> List[CarListing]:
        """Get all listings"""
        return self._listings
    
    def find_reference_car(self, reference: str) -> Optional[Car]:
        """
        Find a car matching a reference string like "BMW 340i 2018"
        Uses fuzzy matching on make, model, and year
        """
        if not reference:
            return None
        
        reference_lower = reference.lower()
        best_match = None
        best_score = 0
        
        for car in self._cars:
            score = 0
            car_str = f"{car.make} {car.model} {car.year}".lower()
            
            # Check if make is mentioned
            if car.make.lower() in reference_lower:
                score += 3
            
            # Check if model is mentioned
            if car.model.lower() in reference_lower:
                score += 3
            
            # Check if year is mentioned
            if str(car.year) in reference:
                score += 2
            
            # Check for trim
            if car.trim.lower() in reference_lower:
                score += 1
            
            if score > best_score:
                best_score = score
                best_match = car
        
        # Only return if we have a reasonable match
        if best_score >= 4:
            return best_match
        return None
    
    def get_feature_stats(self) -> Dict:
        """Get statistics about car features for normalization"""
        if not self._cars:
            return {}
        
        prices = [c.avg_price for c in self._cars]
        powers = [c.power_hp for c in self._cars]
        torques = [c.torque_lb_ft for c in self._cars]
        zero_sixties = [c.zero_to_sixty for c in self._cars]
        
        return {
            'price': {'min': min(prices), 'max': max(prices)},
            'power': {'min': min(powers), 'max': max(powers)},
            'torque': {'min': min(torques), 'max': max(torques)},
            'zero_to_sixty': {'min': min(zero_sixties), 'max': max(zero_sixties)},
        }


# Singleton instance
_db_instance = None

def get_database() -> CarDatabase:
    """Get or create the database singleton"""
    global _db_instance
    if _db_instance is None:
        _db_instance = CarDatabase()
    return _db_instance

