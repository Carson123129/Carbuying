"""
Intent Extraction Engine
Uses LLM to convert natural language queries into structured car preferences
"""
import os
import json
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
from models import UserIntent

load_dotenv()

# System prompt for intent extraction
INTENT_EXTRACTION_PROMPT = """You are a car preference extraction system. Your job is to analyze natural language car queries and extract structured preferences.

Given a user's query about what kind of car they want, extract the following information:

1. Budget: Look for explicit price mentions ("under 35k", "around 30,000") or infer from context
2. Performance priority (0-1): How important is speed/power? ("fast", "quick", "performance" = high)
3. Reliability priority (0-1): How important is reliability? ("reliable", "won't break down" = high)
4. Comfort priority (0-1): How important is comfort? ("comfortable", "daily driver" = high)
5. Drivetrain preference: AWD, RWD, FWD, or null if not specified
6. Body style: sedan, coupe, hatchback, SUV, etc. or null
7. Emotional tags: What feelings/vibes they want (fun, exciting, aggressive, smooth, luxurious, etc.)
8. Negative tags: What they want to AVOID (boring, unreliable, expensive, slow)
9. Reference car: If they mention a specific car ("like a BMW M3", "similar to Audi S4")
10. Usage: How they'll use it (daily, track, winter, road trip, etc.)

IMPORTANT: 
- Be generous with interpreting emotional intent
- "Not boring" should become negative_tag "boring" and emotional_tag "fun" or "exciting"
- "Something like X but cheaper" means reference_car is X and budget should be lower
- "Fun" cars typically have high performance_priority
- Winter/snow mentions suggest AWD preference

Respond ONLY with valid JSON matching this schema:
{
  "budget_min": number or null,
  "budget_max": number or null,
  "performance_priority": number (0-1),
  "reliability_priority": number (0-1),
  "comfort_priority": number (0-1),
  "drivetrain": "AWD" | "RWD" | "FWD" | null,
  "body_style": string or null,
  "emotional_tags": string[],
  "negative_tags": string[],
  "reference_car": string or null,
  "usage": string[]
}"""

REFINEMENT_PROMPT = """You are refining a car search. The user has an existing set of preferences and wants to adjust them.

Current preferences:
{current_intent}

The user wants to refine with: "{refinement}"

Common refinements and their effects:
- "cheaper" / "less expensive": lower budget_max by 15-20%, increase ownership_cost importance
- "more reliable": increase reliability_priority significantly (add 0.2-0.3)
- "sportier" / "more fun": increase performance_priority, add "sporty"/"fun" to emotional_tags
- "bigger": change body_style preference toward larger vehicles
- "more practical": increase comfort_priority, add "practical" to emotional_tags
- "more power" / "faster": increase performance_priority, emphasize power in emotional_tags
- "better in snow" / "winter capable": set drivetrain to AWD if not already
- "more comfortable": increase comfort_priority
- "more luxurious": add "luxury" to emotional_tags

Apply the refinement intelligently and return the updated preferences as JSON.
Respond ONLY with valid JSON matching the same schema as the input."""

INTENT_SUMMARY_PROMPT = """Given these car preferences, write a casual, friendly one-sentence summary of what the user is looking for. Be conversational and use natural language.

Preferences:
{intent}

Write a summary like: "You want a fast, reliable AWD sedan under $35k that's actually fun to drive."
Just the summary, nothing else."""


class IntentEngine:
    """Extracts structured intent from natural language queries"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
    
    def extract_intent(self, query: str) -> UserIntent:
        """
        Extract structured intent from a natural language query
        Falls back to heuristic extraction if no API key
        """
        if self.client:
            return self._extract_with_llm(query)
        else:
            return self._extract_heuristic(query)
    
    def _extract_with_llm(self, query: str) -> UserIntent:
        """Use OpenAI to extract intent"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": INTENT_EXTRACTION_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return UserIntent(
                budget_min=result.get("budget_min"),
                budget_max=result.get("budget_max"),
                performance_priority=result.get("performance_priority", 0.5),
                reliability_priority=result.get("reliability_priority", 0.5),
                comfort_priority=result.get("comfort_priority", 0.5),
                drivetrain=result.get("drivetrain"),
                body_style=result.get("body_style"),
                emotional_tags=result.get("emotional_tags", []),
                negative_tags=result.get("negative_tags", []),
                reference_car=result.get("reference_car"),
                usage=result.get("usage", []),
                raw_query=query
            )
        except Exception as e:
            print(f"LLM extraction failed: {e}")
            return self._extract_heuristic(query)
    
    def _extract_heuristic(self, query: str) -> UserIntent:
        """
        Fallback heuristic-based intent extraction
        Works without API key for development/testing
        """
        query_lower = query.lower()
        
        # Extract budget
        budget_max = None
        budget_min = None
        import re
        
        # Match patterns like "under 35k", "below $40,000", "around 30k"
        budget_patterns = [
            r'under\s*\$?(\d+)k?\b',
            r'below\s*\$?(\d+)k?\b',
            r'less than\s*\$?(\d+)k?\b',
            r'\$?(\d+)k?\s*(?:max|budget)',
            r'around\s*\$?(\d+)k?\b',
            r'\$(\d{2,3}),?(\d{3})',
        ]
        
        for pattern in budget_patterns:
            match = re.search(pattern, query_lower)
            if match:
                amount = match.group(1)
                if len(match.groups()) > 1 and match.group(2):
                    budget_max = int(amount + match.group(2))
                elif 'k' in query_lower[match.end():match.end()+2] or len(amount) <= 3:
                    budget_max = int(amount) * 1000
                else:
                    budget_max = int(amount)
                break
        
        # Performance indicators
        performance_words = ['fast', 'quick', 'powerful', 'sporty', 'speed', 'performance', 'fun', 'exciting', 'thrilling']
        performance_priority = 0.5
        if any(word in query_lower for word in performance_words):
            performance_priority = 0.8
        
        # Reliability indicators
        reliability_words = ['reliable', 'dependable', 'won\'t break', 'low maintenance', 'bulletproof']
        reliability_priority = 0.5
        if any(word in query_lower for word in reliability_words):
            reliability_priority = 0.8
        
        # Comfort indicators
        comfort_words = ['comfortable', 'comfy', 'smooth', 'daily', 'daily driver', 'commute']
        comfort_priority = 0.5
        if any(word in query_lower for word in comfort_words):
            comfort_priority = 0.7
        
        # Drivetrain
        drivetrain = None
        if 'awd' in query_lower or 'all wheel' in query_lower or 'snow' in query_lower or 'winter' in query_lower:
            drivetrain = 'AWD'
        elif 'rwd' in query_lower or 'rear wheel' in query_lower:
            drivetrain = 'RWD'
        elif 'fwd' in query_lower or 'front wheel' in query_lower:
            drivetrain = 'FWD'
        
        # Body style
        body_style = None
        body_types = ['sedan', 'coupe', 'hatchback', 'suv', 'truck', 'wagon', 'convertible']
        for bt in body_types:
            if bt in query_lower:
                body_style = bt
                break
        
        # Emotional tags
        emotional_tags = []
        emotion_words = {
            'fun': ['fun', 'enjoyable', 'blast'],
            'exciting': ['exciting', 'thrilling', 'exhilarating'],
            'aggressive': ['aggressive', 'mean', 'intimidating'],
            'luxurious': ['luxury', 'luxurious', 'premium', 'fancy'],
            'sporty': ['sporty', 'athletic', 'dynamic'],
            'comfortable': ['comfortable', 'comfy', 'relaxing'],
            'practical': ['practical', 'sensible', 'useful'],
            'unique': ['unique', 'different', 'special', 'stand out'],
            'value': ['value', 'deal', 'worth', 'bang for buck'],
        }
        
        for tag, words in emotion_words.items():
            if any(word in query_lower for word in words):
                emotional_tags.append(tag)
        
        # Negative tags
        negative_tags = []
        negative_words = {
            'boring': ['boring', 'dull', 'bland'],
            'slow': ['slow', 'sluggish'],
            'unreliable': ['unreliable', 'breaks down', 'problematic'],
            'expensive': ['expensive', 'costly', 'pricey'],
            'old': ['old', 'dated', 'ancient'],
        }
        
        for tag, words in negative_words.items():
            if any(word in query_lower for word in words):
                negative_tags.append(tag)
        
        # Check for "not boring" type phrases
        if 'not boring' in query_lower:
            negative_tags.append('boring')
            if 'fun' not in emotional_tags:
                emotional_tags.append('fun')
        
        # Reference car extraction
        reference_car = None
        car_brands = ['bmw', 'audi', 'mercedes', 'lexus', 'porsche', 'tesla', 'genesis', 'kia', 'honda', 'toyota', 
                      'ford', 'chevrolet', 'dodge', 'subaru', 'volkswagen', 'mazda', 'infiniti', 'acura', 'alfa romeo', 'cadillac']
        
        like_patterns = [
            r'(?:like|similar to|something like)\s+(?:a\s+)?(?:the\s+)?(.+?)(?:\s+but|\s*,|$)',
            r'(?:like|similar to)\s+(?:an?\s+)?(\w+\s+\w+)',
        ]
        
        for pattern in like_patterns:
            match = re.search(pattern, query_lower)
            if match:
                ref = match.group(1).strip()
                if any(brand in ref for brand in car_brands):
                    reference_car = ref
                    break
        
        # Usage patterns
        usage = []
        if 'daily' in query_lower or 'commute' in query_lower or 'everyday' in query_lower:
            usage.append('daily')
        if 'track' in query_lower or 'race' in query_lower:
            usage.append('track')
        if 'winter' in query_lower or 'snow' in query_lower:
            usage.append('winter')
        if 'road trip' in query_lower or 'long distance' in query_lower:
            usage.append('road-trip')
        if 'weekend' in query_lower:
            usage.append('weekend')
        
        return UserIntent(
            budget_min=budget_min,
            budget_max=budget_max,
            performance_priority=performance_priority,
            reliability_priority=reliability_priority,
            comfort_priority=comfort_priority,
            drivetrain=drivetrain,
            body_style=body_style,
            emotional_tags=emotional_tags,
            negative_tags=negative_tags,
            reference_car=reference_car,
            usage=usage,
            raw_query=query
        )
    
    def refine_intent(self, current_intent: UserIntent, refinement: str) -> UserIntent:
        """Apply a refinement to existing intent"""
        if self.client:
            return self._refine_with_llm(current_intent, refinement)
        else:
            return self._refine_heuristic(current_intent, refinement)
    
    def _refine_with_llm(self, current_intent: UserIntent, refinement: str) -> UserIntent:
        """Use LLM to apply refinement"""
        try:
            prompt = REFINEMENT_PROMPT.format(
                current_intent=current_intent.model_dump_json(indent=2),
                refinement=refinement
            )
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Apply this refinement: {refinement}"}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return UserIntent(
                budget_min=result.get("budget_min"),
                budget_max=result.get("budget_max"),
                performance_priority=result.get("performance_priority", 0.5),
                reliability_priority=result.get("reliability_priority", 0.5),
                comfort_priority=result.get("comfort_priority", 0.5),
                drivetrain=result.get("drivetrain"),
                body_style=result.get("body_style"),
                emotional_tags=result.get("emotional_tags", []),
                negative_tags=result.get("negative_tags", []),
                reference_car=result.get("reference_car"),
                usage=result.get("usage", []),
                raw_query=current_intent.raw_query
            )
        except Exception as e:
            print(f"LLM refinement failed: {e}")
            return self._refine_heuristic(current_intent, refinement)
    
    def _refine_heuristic(self, current_intent: UserIntent, refinement: str) -> UserIntent:
        """Apply refinement without LLM"""
        refinement_lower = refinement.lower()
        
        # Create a copy of the intent
        new_intent = UserIntent(
            budget_min=current_intent.budget_min,
            budget_max=current_intent.budget_max,
            performance_priority=current_intent.performance_priority,
            reliability_priority=current_intent.reliability_priority,
            comfort_priority=current_intent.comfort_priority,
            drivetrain=current_intent.drivetrain,
            body_style=current_intent.body_style,
            emotional_tags=list(current_intent.emotional_tags),
            negative_tags=list(current_intent.negative_tags),
            reference_car=current_intent.reference_car,
            usage=list(current_intent.usage),
            raw_query=current_intent.raw_query
        )
        
        # Apply common refinements
        if 'cheaper' in refinement_lower or 'less expensive' in refinement_lower:
            if new_intent.budget_max:
                new_intent.budget_max = int(new_intent.budget_max * 0.8)
        
        elif 'more reliable' in refinement_lower or 'reliable' in refinement_lower:
            new_intent.reliability_priority = min(1.0, new_intent.reliability_priority + 0.25)
        
        elif 'sportier' in refinement_lower or 'more fun' in refinement_lower:
            new_intent.performance_priority = min(1.0, new_intent.performance_priority + 0.2)
            if 'sporty' not in new_intent.emotional_tags:
                new_intent.emotional_tags.append('sporty')
        
        elif 'faster' in refinement_lower or 'more power' in refinement_lower:
            new_intent.performance_priority = min(1.0, new_intent.performance_priority + 0.25)
            if 'fast' not in new_intent.emotional_tags:
                new_intent.emotional_tags.append('fast')
        
        elif 'bigger' in refinement_lower:
            # Shift toward larger body styles
            if new_intent.body_style == 'coupe':
                new_intent.body_style = 'sedan'
            elif new_intent.body_style == 'sedan':
                new_intent.body_style = 'suv'
        
        elif 'more practical' in refinement_lower or 'practical' in refinement_lower:
            new_intent.comfort_priority = min(1.0, new_intent.comfort_priority + 0.2)
            if 'practical' not in new_intent.emotional_tags:
                new_intent.emotional_tags.append('practical')
        
        elif 'more comfortable' in refinement_lower:
            new_intent.comfort_priority = min(1.0, new_intent.comfort_priority + 0.25)
        
        elif 'awd' in refinement_lower or 'all wheel' in refinement_lower:
            new_intent.drivetrain = 'AWD'
        
        elif 'snow' in refinement_lower or 'winter' in refinement_lower:
            new_intent.drivetrain = 'AWD'
            if 'winter' not in new_intent.usage:
                new_intent.usage.append('winter')
        
        elif 'more luxurious' in refinement_lower or 'luxury' in refinement_lower:
            if 'luxurious' not in new_intent.emotional_tags:
                new_intent.emotional_tags.append('luxurious')
        
        return new_intent
    
    def generate_summary(self, intent: UserIntent) -> str:
        """Generate a human-readable summary of the intent"""
        if self.client:
            try:
                prompt = INTENT_SUMMARY_PROMPT.format(
                    intent=intent.model_dump_json(indent=2)
                )
                
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=100
                )
                
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"Summary generation failed: {e}")
        
        # Fallback to heuristic summary
        return self._generate_heuristic_summary(intent)
    
    def _generate_heuristic_summary(self, intent: UserIntent) -> str:
        """Generate summary without LLM"""
        parts = ["You want"]
        
        # Performance description
        if intent.performance_priority > 0.7:
            parts.append("a fast")
        elif intent.performance_priority > 0.5:
            parts.append("a sporty")
        else:
            parts.append("a")
        
        # Reliability
        if intent.reliability_priority > 0.7:
            parts.append("reliable")
        
        # Drivetrain
        if intent.drivetrain:
            parts.append(intent.drivetrain)
        
        # Body style
        if intent.body_style:
            parts.append(intent.body_style)
        else:
            parts.append("car")
        
        # Budget
        if intent.budget_max:
            parts.append(f"under ${intent.budget_max:,}")
        
        # Emotional tags
        if intent.emotional_tags:
            if 'fun' in intent.emotional_tags or 'exciting' in intent.emotional_tags:
                parts.append("that's actually fun to drive")
            elif 'luxurious' in intent.emotional_tags:
                parts.append("with a premium feel")
            elif 'practical' in intent.emotional_tags:
                parts.append("that's practical")
        
        # Negative tags
        if 'boring' in intent.negative_tags:
            parts.append("(definitely not boring)")
        
        # Reference
        if intent.reference_car:
            parts.append(f"— something like a {intent.reference_car}")
        
        return " ".join(parts) + "."


# Singleton instance
_engine_instance = None

def get_intent_engine() -> IntentEngine:
    """Get or create the intent engine singleton"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = IntentEngine()
    return _engine_instance


