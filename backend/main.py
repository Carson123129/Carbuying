"""
FindingMyCar API
Main FastAPI application
"""
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from typing import List, Optional
import uvicorn

from models import (
    SearchRequest, SearchResponse, RefinementRequest,
    UserIntent, MatchResult, Car
)
from intent_engine import get_intent_engine
from scoring_engine import get_scoring_engine
from database import get_database
from ingestion.query import list_runs, get_latest_run, list_live_listings
from waitlist import add_waitlist_email

app = FastAPI(
    title="FindingMyCar",
    description="AI-driven intent-to-match system for finding your next car",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR = STATIC_DIR.resolve()  # Resolve to absolute path
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page"""
    try:
        index_path = STATIC_DIR / "index.html"
        index_path = index_path.resolve()
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HTMLResponse(content=content)
    except Exception as e:
        pass
    return HTMLResponse(content="<h1>FindingMyCar API is running</h1><p>Static files not found.</p>", status_code=200)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "message": "FindingMyCar API is running"}


@app.post("/api/waitlist")
async def waitlist_signup(request: Request):
    """Capture waitlist signups from the landing fallback or JSON clients."""
    content_type = request.headers.get("content-type", "")
    email = ""
    source = "landing"

    if "application/json" in content_type:
        payload = await request.json()
        if isinstance(payload, dict):
            email = str(payload.get("email", "")).strip()
            source = str(payload.get("source", "landing")).strip()
    else:
        form = await request.form()
        email = str(form.get("email", "")).strip()
        source = str(form.get("source", "landing")).strip()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")

    added = add_waitlist_email(email=email, source=source)

    if "text/html" in request.headers.get("accept", ""):
        message = "You're on the list." if added else "You're already on the list."
        return HTMLResponse(
            content=(
                "<!doctype html><html><head><title>FindingMyCar</title>"
                "<meta charset='utf-8'></head><body style='font-family:Outfit,Arial,sans-serif;"
                "background:#0a0a0f;color:#f8fafc;display:flex;align-items:center;justify-content:center;"
                "min-height:100vh;margin:0;'><div style='text-align:center;max-width:480px;padding:32px;'>"
                f"<h1 style='margin-bottom:12px;'>{message}</h1>"
                "<p style='color:#94a3b8;'>We will email you when early access is ready.</p>"
                "<a href='/' style='color:#fbbf24;'>Back to FindingMyCar</a>"
                "</div></body></html>"
            ),
            status_code=200,
        )

    return {"status": "ok", "added": added}


@app.post("/api/search", response_model=SearchResponse)
async def search_cars(request: SearchRequest):
    """
    Main search endpoint.
    Takes a natural language query and returns matched cars.
    """
    intent_engine = get_intent_engine()
    scoring_engine = get_scoring_engine()
    
    # Extract intent from query
    intent = intent_engine.extract_intent(request.query)
    
    # Apply any refinements from previous searches
    if request.refinements:
        for refinement in request.refinements:
            intent = intent_engine.refine_intent(intent, refinement)
    
    # Generate human-readable summary
    intent_summary = intent_engine.generate_summary(intent)
    
    # Score and rank all cars
    matches = scoring_engine.score_all_cars(intent)
    
    # Return top matches (limit to 10)
    top_matches = matches[:10]
    
    # Generate refinement suggestions based on results
    suggestions = _generate_suggestions(intent, top_matches)
    
    return SearchResponse(
        interpreted_intent=intent,
        intent_summary=intent_summary,
        matches=top_matches,
        suggestions=suggestions
    )


@app.post("/api/refine", response_model=SearchResponse)
async def refine_search(request: RefinementRequest):
    """
    Refine an existing search with a modifier.
    """
    intent_engine = get_intent_engine()
    scoring_engine = get_scoring_engine()
    
    # Apply refinement to previous intent
    refined_intent = intent_engine.refine_intent(
        request.previous_intent,
        request.refinement
    )
    
    # Update raw query to reflect refinement
    refined_intent.raw_query = f"{request.original_query} ({request.refinement})"
    
    # Generate new summary
    intent_summary = intent_engine.generate_summary(refined_intent)
    
    # Re-score all cars with refined intent
    matches = scoring_engine.score_all_cars(refined_intent)
    
    # Return top matches
    top_matches = matches[:10]
    
    # Generate new suggestions
    suggestions = _generate_suggestions(refined_intent, top_matches)
    
    return SearchResponse(
        interpreted_intent=refined_intent,
        intent_summary=intent_summary,
        matches=top_matches,
        suggestions=suggestions
    )


@app.get("/api/cars", response_model=List[Car])
async def get_all_cars():
    """Get all cars in the database"""
    db = get_database()
    return db.get_all_cars()


@app.get("/api/cars/{car_id}", response_model=Car)
async def get_car(car_id: str):
    """Get a specific car by ID"""
    db = get_database()
    car = db.get_car_by_id(car_id)
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    return car


@app.get("/api/ingestion/runs")
async def ingestion_runs():
    return {"runs": list_runs(limit=25)}


@app.get("/api/ingestion/latest")
async def ingestion_latest():
    return get_latest_run()


@app.get("/api/listings/live")
async def listings_live():
    return {"listings": list_live_listings(limit=50)}


def _generate_suggestions(intent: UserIntent, matches: List[MatchResult]) -> List[str]:
    """Generate contextual refinement suggestions"""
    suggestions = []
    
    # Always offer these common refinements
    base_suggestions = [
        "Cheaper",
        "More reliable",
        "Sportier",
        "More practical"
    ]
    
    # Context-aware suggestions
    if not intent.drivetrain:
        suggestions.append("AWD")
    elif intent.drivetrain == "RWD":
        suggestions.append("AWD instead")
    
    if intent.budget_max and intent.budget_max > 30000:
        suggestions.append("Cheaper")
    
    if intent.performance_priority < 0.7:
        suggestions.append("Faster")
    
    if intent.reliability_priority < 0.7:
        suggestions.append("More reliable")
    
    if 'luxurious' not in intent.emotional_tags:
        suggestions.append("More luxurious")
    
    if intent.comfort_priority < 0.6:
        suggestions.append("More comfortable")
    
    # Check top matches for common tradeoffs
    if matches:
        top_tradeoffs = []
        for match in matches[:3]:
            top_tradeoffs.extend(match.tradeoffs)
        
        if any('budget' in t.lower() for t in top_tradeoffs):
            if "Cheaper" not in suggestions:
                suggestions.append("Cheaper")
        
        if any('reliable' in t.lower() for t in top_tradeoffs):
            if "More reliable" not in suggestions:
                suggestions.append("More reliable")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_suggestions = []
    for s in suggestions:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique_suggestions.append(s)
    
    # Add base suggestions that aren't already included
    for s in base_suggestions:
        if s.lower() not in seen:
            unique_suggestions.append(s)
            seen.add(s.lower())
    
    return unique_suggestions[:6]


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

