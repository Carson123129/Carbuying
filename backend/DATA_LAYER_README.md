# FindingMyCar Data Layer

Production-quality MVP data layer for the AI car recommendation system.

## Architecture

```
/backend
├── /db                     # Database models and utilities
│   └── models.py           # SQLAlchemy models (CarMaster, CarListing, CarProfile)
├── /data                   # Data pipeline scripts
│   ├── build_master_cars.py    # NHTSA API → cars_master
│   ├── import_marketcheck.py   # Marketcheck API → car_listings
│   ├── normalize.py            # Match listings to master cars
│   └── build_profiles.py       # Compute aggregated stats
├── /api                    # Query API for AI layer
│   └── routes.py           # FastAPI routes
└── main.py                 # Main app (includes data layer routes)
```

## Database Schema

### cars_master
Canonical list of all cars from NHTSA (25 years of makes/models).

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| make | str | e.g., "Toyota" |
| model | str | e.g., "Camry" |
| year | int | Model year |
| trim | str? | Trim level |
| body_type | str? | Sedan, SUV, etc. |

### car_listings
Live used car listings from Marketcheck API.

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| vin | str | Vehicle ID (unique) |
| make, model, year, trim | str/int | Car info |
| price | int | USD |
| mileage | int | Miles |
| city, state, zip_code | str | Location |
| dealer_name, dealer_id | str | Dealer info |
| drivetrain | str | AWD, RWD, FWD, 4WD |
| engine, transmission | str | Powertrain |
| mpg_city, mpg_hwy | int | Fuel economy |
| body_type | str | Body style |
| listing_url, photo_url | str | Links |
| master_car_id | int? | FK to cars_master |

### car_profiles
Aggregated stats per master car.

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| master_car_id | int | FK to cars_master |
| avg_price, min_price, max_price, median_price | float/int | Price stats |
| avg_mileage, min_mileage, max_mileage | float/int | Mileage stats |
| count_listings | int | Number of listings |
| drivetrain_options | json | Available drivetrains |
| engine_options | json | Available engines |
| mpg_city_min/max, mpg_hwy_min/max | int | MPG ranges |

## Setup

### 1. Environment Variables

Create `.env` in `/backend`:

```env
# PostgreSQL connection
DATABASE_URL=postgresql://user:password@localhost:5432/findingmycar

# Marketcheck API (get at https://www.marketcheck.com/apis)
MARKETCHECK_API_KEY=your_api_key_here

# OpenAI (for intent engine)
OPENAI_API_KEY=your_openai_key
```

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Create Database

```sql
CREATE DATABASE findingmycar;
```

Or use the Python script:
```bash
python -c "from db.models import init_db; init_db()"
```

### 4. Build Master Cars Database

Pull all makes/models from NHTSA (takes ~30 mins):

```bash
cd backend
python data/build_master_cars.py
```

Options:
```bash
# Specific year range
python data/build_master_cars.py --year-start 2015 --year-end 2024

# Include all makes (not just common passenger vehicles)
python data/build_master_cars.py --all-makes
```

### 5. Import Listings from Marketcheck

```bash
python data/import_marketcheck.py --limit 5000
```

Options:
```bash
# Filter by make/model
python data/import_marketcheck.py --make Toyota --model Camry

# Filter by year range
python data/import_marketcheck.py --year-min 2018 --year-max 2024

# Filter by price/mileage
python data/import_marketcheck.py --price-max 35000 --mileage-max 60000

# Filter by state
python data/import_marketcheck.py --state CA
```

### 6. Normalize Listings

Match listings to master cars:

```bash
python data/normalize.py
```

Options:
```bash
# Adjust match threshold (0-1)
python data/normalize.py --threshold 0.85

# Re-match all listings
python data/normalize.py --force-rematch
```

### 7. Build Profiles

Compute aggregated stats:

```bash
python data/build_profiles.py
```

Options:
```bash
# Require minimum listings per profile
python data/build_profiles.py --min-listings 3
```

## API Endpoints

### Search Cars

```
GET /api/cars/search
```

Query params:
- `make` - Filter by make
- `model` - Filter by model (partial match)
- `year_min`, `year_max` - Year range
- `price_min`, `price_max` - Price range
- `mileage_max` - Maximum avg mileage
- `drivetrain` - AWD, RWD, FWD, 4WD
- `body_type` - Sedan, SUV, Truck, etc.
- `min_listings` - Minimum listing count
- `page`, `page_size` - Pagination

Example:
```bash
curl "http://localhost:8000/api/cars/search?make=Toyota&year_min=2018&price_max=35000"
```

### Get Car Profile

```
GET /api/cars/{profile_id}
```

Returns full profile with live listings.

### Get Stats

```
GET /api/cars/stats/overview
```

Returns database statistics (counts, makes list, year range).

### Get Makes

```
GET /api/cars/makes
```

Returns list of all available makes.

### Get Models for Make

```
GET /api/cars/models/{make}
```

Returns models for a specific make.

## Data Pipeline Schedule

Recommended cron jobs:

```bash
# Daily: Import new listings
0 2 * * * cd /app/backend && python data/import_marketcheck.py --limit 10000

# Daily: Normalize new listings
0 3 * * * cd /app/backend && python data/normalize.py

# Daily: Rebuild profiles
0 4 * * * cd /app/backend && python data/build_profiles.py

# Monthly: Refresh master cars (new model years)
0 5 1 * * cd /app/backend && python data/build_master_cars.py
```

## Integration with AI Layer

The scoring engine can query car profiles:

```python
from api.routes import search_cars

# Find cars matching user intent
results = await search_cars(
    make=intent.reference_make,
    year_min=2018,
    price_max=intent.budget_max,
    drivetrain=intent.drivetrain,
    session=db_session
)

# Get detailed profile with listings
profile = await get_car_profile(car_id=42, session=db_session)
```

## Notes

- NHTSA API is free, no key required
- Marketcheck API requires subscription for production use
- Rate limiting is built into all scripts
- All scripts support incremental updates (upserts)

