"""
Similarity & Scoring Engine
Computes match scores between user intent and cars
"""
from typing import List, Dict, Tuple, Set
from models import UserIntent, Car, MatchResult, CarListing
from database import get_database


class ScoringEngine:
    """
    Scores cars based on how well they match user intent.
    Uses weighted multi-factor scoring with 0-100 scale.
    """
    
    # Emotional tag similarity mappings (which tags are related)
    EMOTIONAL_SIMILARITIES = {
        'fun': {'exciting', 'sporty', 'engaging', 'playful', 'thrilling'},
        'exciting': {'fun', 'aggressive', 'powerful', 'thrilling', 'passionate'},
        'aggressive': {'exciting', 'powerful', 'bold', 'mean'},
        'sporty': {'fun', 'engaging', 'athletic', 'dynamic'},
        'luxurious': {'sophisticated', 'premium', 'refined', 'prestigious', 'classy'},
        'sophisticated': {'luxurious', 'refined', 'elegant', 'classy'},
        'reliable': {'dependable', 'trustworthy', 'sensible'},
        'practical': {'sensible', 'useful', 'value'},
        'comfortable': {'smooth', 'refined', 'relaxing'},
        'value': {'practical', 'sensible', 'surprising'},
        'fast': {'powerful', 'quick', 'exciting'},
        'unique': {'special', 'passionate', 'distinctive'},
    }
    
    # Driving feel to emotional mapping
    DRIVING_FEEL_TO_EMOTION = {
        'sporty': {'fun', 'exciting', 'sporty'},
        'responsive': {'fun', 'engaging', 'sporty'},
        'engaging': {'fun', 'exciting', 'sporty'},
        'raw': {'exciting', 'passionate', 'aggressive'},
        'sharp': {'sporty', 'engaging', 'exciting'},
        'refined': {'sophisticated', 'luxurious', 'comfortable'},
        'smooth': {'comfortable', 'luxurious', 'refined'},
        'composed': {'reliable', 'sophisticated', 'comfortable'},
        'powerful': {'fast', 'exciting', 'aggressive'},
        'balanced': {'practical', 'reliable', 'sporty'},
        'comfortable': {'comfortable', 'practical', 'reliable'},
        'planted': {'reliable', 'sophisticated', 'sporty'},
        'precise': {'sporty', 'engaging', 'sophisticated'},
        'instant': {'fast', 'exciting', 'modern'},
        'quiet': {'comfortable', 'luxurious', 'refined'},
        'playful': {'fun', 'exciting', 'sporty'},
        'direct': {'engaging', 'sporty', 'raw'},
    }
    
    # Negative tag opposites
    NEGATIVE_OPPOSITES = {
        'boring': {'fun', 'exciting', 'engaging', 'sporty', 'aggressive'},
        'slow': {'fast', 'powerful', 'exciting'},
        'unreliable': {'reliable', 'dependable'},
        'expensive': {'value', 'practical'},
        'uncomfortable': {'comfortable', 'luxurious', 'refined'},
        'numb': {'engaging', 'raw', 'sporty'},
    }
    
    def __init__(self):
        self.db = get_database()
        self.stats = self.db.get_feature_stats()
    
    def score_all_cars(self, intent: UserIntent) -> List[MatchResult]:
        """
        Score all cars against the user intent.
        Returns sorted list of MatchResults (highest score first).
        """
        cars = self.db.get_all_cars()
        reference_car = None
        
        # Find reference car if specified
        if intent.reference_car:
            reference_car = self.db.find_reference_car(intent.reference_car)
        
        results = []
        for car in cars:
            score, reasons, tradeoffs = self._score_car(car, intent, reference_car)
            
            # Get listings for this car
            listings = self.db.get_listings_for_car(car.id)
            
            results.append(MatchResult(
                car=car,
                match_score=round(score, 1),
                match_reasons=reasons,
                tradeoffs=tradeoffs,
                listings=listings
            ))
        
        # Sort by score descending
        results.sort(key=lambda x: x.match_score, reverse=True)
        
        return results
    
    def _score_car(self, car: Car, intent: UserIntent, reference_car: Car = None) -> Tuple[float, List[str], List[str]]:
        """
        Calculate match score for a single car.
        Returns (score, reasons, tradeoffs)
        """
        scores = {}
        reasons = []
        tradeoffs = []
        
        # 1. Price Score (0-100)
        price_score, price_reason, price_tradeoff = self._score_price(car, intent)
        scores['price'] = price_score
        if price_reason:
            reasons.append(price_reason)
        if price_tradeoff:
            tradeoffs.append(price_tradeoff)
        
        # 2. Performance Score (0-100)
        perf_score, perf_reason, perf_tradeoff = self._score_performance(car, intent)
        scores['performance'] = perf_score
        if perf_reason:
            reasons.append(perf_reason)
        if perf_tradeoff:
            tradeoffs.append(perf_tradeoff)
        
        # 3. Reliability Score (0-100)
        rel_score, rel_reason, rel_tradeoff = self._score_reliability(car, intent)
        scores['reliability'] = rel_score
        if rel_reason:
            reasons.append(rel_reason)
        if rel_tradeoff:
            tradeoffs.append(rel_tradeoff)
        
        # 4. Drivetrain Score (0-100)
        drive_score, drive_reason, drive_tradeoff = self._score_drivetrain(car, intent)
        scores['drivetrain'] = drive_score
        if drive_reason:
            reasons.append(drive_reason)
        if drive_tradeoff:
            tradeoffs.append(drive_tradeoff)
        
        # 5. Body Style Score (0-100)
        body_score = self._score_body_style(car, intent)
        scores['body_style'] = body_score
        
        # 6. Emotional Match Score (0-100)
        emo_score, emo_reasons, emo_tradeoffs = self._score_emotional(car, intent)
        scores['emotional'] = emo_score
        reasons.extend(emo_reasons)
        tradeoffs.extend(emo_tradeoffs)
        
        # 7. Reference Car Similarity (0-100) - bonus if provided
        if reference_car and car.id != reference_car.id:
            ref_score, ref_reason = self._score_reference_similarity(car, reference_car)
            scores['reference'] = ref_score
            if ref_reason:
                reasons.append(ref_reason)
        
        # 8. Ownership Cost (0-100)
        cost_score = self._score_ownership_cost(car, intent)
        scores['ownership'] = cost_score
        
        # Calculate weighted final score
        final_score = self._calculate_weighted_score(scores, intent, bool(reference_car))
        
        # Limit reasons and tradeoffs to top items
        reasons = reasons[:4]
        tradeoffs = tradeoffs[:3]
        
        return final_score, reasons, tradeoffs
    
    def _score_price(self, car: Car, intent: UserIntent) -> Tuple[float, str, str]:
        """Score based on price fit"""
        if not intent.budget_max:
            return 80.0, None, None  # Neutral if no budget specified
        
        avg_price = car.avg_price
        budget = intent.budget_max
        
        if avg_price <= budget:
            # Under budget - excellent
            headroom = (budget - avg_price) / budget
            if headroom > 0.2:
                return 100.0, f"Well under budget at ~${avg_price:,}", None
            else:
                return 95.0, f"Fits your ${budget:,} budget nicely", None
        else:
            # Over budget
            over_percent = (avg_price - budget) / budget
            if over_percent < 0.1:
                return 75.0, None, f"Slightly over budget (~${avg_price:,})"
            elif over_percent < 0.2:
                return 50.0, None, f"Above budget at ~${avg_price:,}"
            else:
                return 20.0, None, f"Significantly over budget at ~${avg_price:,}"
    
    def _score_performance(self, car: Car, intent: UserIntent) -> Tuple[float, str, str]:
        """Score based on performance metrics"""
        perf_priority = intent.performance_priority
        
        # Normalize car performance (using 0-60 as primary metric)
        # Lower 0-60 = better performance
        zero_sixty = car.zero_to_sixty
        
        # Calculate performance tier
        if zero_sixty <= 4.5:
            perf_tier = 'excellent'
            base_score = 100
        elif zero_sixty <= 5.0:
            perf_tier = 'great'
            base_score = 85
        elif zero_sixty <= 5.5:
            perf_tier = 'good'
            base_score = 70
        elif zero_sixty <= 6.0:
            perf_tier = 'decent'
            base_score = 55
        else:
            perf_tier = 'moderate'
            base_score = 40
        
        # Adjust based on priority
        if perf_priority > 0.7:
            # High performance priority
            if perf_tier in ['excellent', 'great']:
                return base_score, f"Seriously quick (0-60 in {zero_sixty}s)", None
            else:
                return base_score, None, f"Not the quickest ({zero_sixty}s 0-60)"
        elif perf_priority < 0.4:
            # Low performance priority - don't penalize slower cars
            return max(base_score, 70), None, None
        else:
            # Moderate priority
            if perf_tier in ['excellent', 'great']:
                return base_score, f"{car.power_hp}hp provides plenty of power", None
            return base_score, None, None
    
    def _score_reliability(self, car: Car, intent: UserIntent) -> Tuple[float, str, str]:
        """Score based on reliability"""
        rel_priority = intent.reliability_priority
        rel_score = car.reliability_score  # 0-10 scale
        
        # Convert to 0-100
        base_score = rel_score * 10
        
        if rel_priority > 0.7:
            # High reliability priority
            if rel_score >= 8:
                return base_score, "Excellent reliability record", None
            elif rel_score >= 7:
                return base_score, "Good reliability reputation", None
            else:
                return base_score, None, f"Reliability could be a concern ({rel_score}/10)"
        elif rel_priority < 0.4:
            # Low priority - don't penalize much
            return max(base_score, 60), None, None
        else:
            # Moderate priority
            if rel_score >= 8:
                return base_score, "Known for being dependable", None
            return base_score, None, None
    
    def _score_drivetrain(self, car: Car, intent: UserIntent) -> Tuple[float, str, str]:
        """Score based on drivetrain match"""
        if not intent.drivetrain:
            return 80.0, None, None  # Neutral if not specified
        
        if car.drivetrain.upper() == intent.drivetrain.upper():
            return 100.0, f"{car.drivetrain} as requested", None
        
        # Partial matches
        if intent.drivetrain.upper() == 'AWD' and car.drivetrain.upper() != 'AWD':
            return 40.0, None, f"Only available in {car.drivetrain}"
        
        return 60.0, None, f"{car.drivetrain} instead of {intent.drivetrain}"
    
    def _score_body_style(self, car: Car, intent: UserIntent) -> float:
        """Score based on body style match"""
        if not intent.body_style:
            return 80.0  # Neutral if not specified
        
        car_body = car.body_type.lower()
        pref_body = intent.body_style.lower()
        
        if car_body == pref_body:
            return 100.0
        
        # Similar body styles
        similar_groups = [
            {'sedan', 'liftback'},
            {'coupe', 'convertible'},
            {'hatchback', 'liftback', 'hot-hatch'},
            {'suv', 'crossover'},
        ]
        
        for group in similar_groups:
            if car_body in group and pref_body in group:
                return 80.0
        
        return 50.0
    
    def _score_emotional(self, car: Car, intent: UserIntent) -> Tuple[float, List[str], List[str]]:
        """Score based on emotional tag matching"""
        reasons = []
        tradeoffs = []
        
        # Build car's emotional profile from multiple sources
        car_emotions: Set[str] = set(tag.lower() for tag in car.emotional_tags)
        
        # Add emotions derived from driving feel
        for feel in car.driving_feel_tags:
            feel_lower = feel.lower()
            if feel_lower in self.DRIVING_FEEL_TO_EMOTION:
                car_emotions.update(self.DRIVING_FEEL_TO_EMOTION[feel_lower])
        
        # Add class-based emotions
        for class_tag in car.class_tags:
            class_lower = class_tag.lower()
            if class_lower == 'luxury':
                car_emotions.update({'luxurious', 'sophisticated', 'premium'})
            elif class_lower == 'performance':
                car_emotions.update({'exciting', 'fast', 'fun'})
            elif class_lower == 'sport':
                car_emotions.update({'sporty', 'fun', 'engaging'})
        
        # Score positive emotional matches
        positive_score = 0
        positive_matches = []
        
        for wanted_tag in intent.emotional_tags:
            wanted_lower = wanted_tag.lower()
            
            # Direct match
            if wanted_lower in car_emotions:
                positive_score += 20
                positive_matches.append(wanted_tag)
                continue
            
            # Similar match
            if wanted_lower in self.EMOTIONAL_SIMILARITIES:
                similar = self.EMOTIONAL_SIMILARITIES[wanted_lower]
                if car_emotions & similar:
                    positive_score += 12
                    positive_matches.append(wanted_tag)
        
        if positive_matches:
            reasons.append(f"Matches your vibe: {', '.join(positive_matches[:3])}")
        
        # Score negative tag avoidance
        negative_penalty = 0
        
        for avoid_tag in intent.negative_tags:
            avoid_lower = avoid_tag.lower()
            
            # Check if car has this negative trait
            if avoid_lower in car_emotions:
                negative_penalty += 25
                tradeoffs.append(f"May feel {avoid_lower}")
                continue
            
            # Check if car has opposites of what to avoid (good!)
            if avoid_lower in self.NEGATIVE_OPPOSITES:
                opposites = self.NEGATIVE_OPPOSITES[avoid_lower]
                if car_emotions & opposites:
                    positive_score += 10
                    reasons.append(f"Definitely not {avoid_lower}")
        
        # Base emotional score
        if not intent.emotional_tags and not intent.negative_tags:
            return 70.0, reasons, tradeoffs
        
        # Calculate final emotional score
        max_positive = len(intent.emotional_tags) * 20 if intent.emotional_tags else 50
        max_negative = len(intent.negative_tags) * 25 if intent.negative_tags else 0
        
        final_score = 50 + min(positive_score, 50) - min(negative_penalty, 40)
        final_score = max(0, min(100, final_score))
        
        return final_score, reasons, tradeoffs
    
    def _score_reference_similarity(self, car: Car, reference: Car) -> Tuple[float, str]:
        """Score similarity to reference car"""
        score = 0
        
        # Same drivetrain
        if car.drivetrain == reference.drivetrain:
            score += 15
        
        # Similar power (within 20%)
        power_diff = abs(car.power_hp - reference.power_hp) / reference.power_hp
        if power_diff < 0.1:
            score += 20
        elif power_diff < 0.2:
            score += 12
        elif power_diff < 0.3:
            score += 5
        
        # Similar 0-60
        zero_diff = abs(car.zero_to_sixty - reference.zero_to_sixty)
        if zero_diff < 0.3:
            score += 15
        elif zero_diff < 0.6:
            score += 10
        elif zero_diff < 1.0:
            score += 5
        
        # Same body type
        if car.body_type == reference.body_type:
            score += 15
        
        # Similar price
        price_diff = abs(car.avg_price - reference.avg_price) / reference.avg_price
        if price_diff < 0.1:
            score += 15
        elif price_diff < 0.2:
            score += 10
        elif price_diff < 0.3:
            score += 5
        
        # Similar class tags
        common_classes = set(car.class_tags) & set(reference.class_tags)
        score += len(common_classes) * 10
        
        # Similar emotional profile
        common_emotions = set(car.emotional_tags) & set(reference.emotional_tags)
        score += len(common_emotions) * 5
        
        # Normalize to 0-100
        final_score = min(100, score)
        
        reason = None
        if final_score > 70:
            reason = f"Very similar to the {reference.make} {reference.model}"
        elif final_score > 50:
            reason = f"Comparable to the {reference.make} {reference.model}"
        
        return final_score, reason
    
    def _score_ownership_cost(self, car: Car, intent: UserIntent) -> float:
        """Score based on ownership cost"""
        cost_score = car.ownership_cost_score  # 0-10 scale
        
        # Higher score = lower cost = better
        # Normalize to 0-100
        return cost_score * 10
    
    def _calculate_weighted_score(self, scores: Dict[str, float], intent: UserIntent, has_reference: bool) -> float:
        """Calculate final weighted score"""
        
        # Base weights
        weights = {
            'price': 0.20,
            'performance': 0.15,
            'reliability': 0.15,
            'drivetrain': 0.10,
            'body_style': 0.10,
            'emotional': 0.20,
            'ownership': 0.10,
        }
        
        # Add reference weight if applicable
        if has_reference and 'reference' in scores:
            weights['reference'] = 0.15
            # Reduce others proportionally
            for key in weights:
                if key != 'reference':
                    weights[key] *= 0.85
        
        # Adjust weights based on intent priorities
        if intent.performance_priority > 0.7:
            weights['performance'] = 0.25
            weights['emotional'] = 0.15
        
        if intent.reliability_priority > 0.7:
            weights['reliability'] = 0.22
            weights['ownership'] = 0.15
        
        if intent.drivetrain:
            weights['drivetrain'] = 0.15
        
        # Calculate weighted sum
        total_weight = sum(weights.get(k, 0) for k in scores.keys())
        weighted_sum = sum(scores[k] * weights.get(k, 0.1) for k in scores.keys())
        
        if total_weight > 0:
            return (weighted_sum / total_weight) * (total_weight)
        return 50.0


# Singleton instance
_engine_instance = None

def get_scoring_engine() -> ScoringEngine:
    """Get or create the scoring engine singleton"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ScoringEngine()
    return _engine_instance


