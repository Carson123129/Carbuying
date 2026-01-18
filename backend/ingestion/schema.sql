-- Core specs
CREATE TABLE IF NOT EXISTS car_make (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS car_model (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    make_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    UNIQUE(make_id, name),
    FOREIGN KEY(make_id) REFERENCES car_make(id)
);

CREATE TABLE IF NOT EXISTS car_trim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    year_start INTEGER,
    year_end INTEGER,
    UNIQUE(model_id, name, year_start, year_end),
    FOREIGN KEY(model_id) REFERENCES car_model(id)
);

CREATE TABLE IF NOT EXISTS car_spec (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trim_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    drivetrain TEXT,
    body_type TEXT,
    power_hp INTEGER,
    torque_lb_ft INTEGER,
    mpg_city INTEGER,
    mpg_highway INTEGER,
    mpg_combined INTEGER,
    zero_to_sixty REAL,
    reliability_score REAL,
    ownership_cost_score REAL,
    character_tags TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trim_id, year),
    FOREIGN KEY(trim_id) REFERENCES car_trim(id)
);

-- Listings
CREATE TABLE IF NOT EXISTS listing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_listing_id TEXT NOT NULL,
    car_spec_id INTEGER NOT NULL,
    title TEXT,
    price INTEGER,
    mileage INTEGER,
    location_city TEXT,
    location_state TEXT,
    condition TEXT,
    url TEXT,
    listed_at TEXT,
    last_seen_at TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, source_listing_id),
    FOREIGN KEY(car_spec_id) REFERENCES car_spec(id)
);

CREATE TABLE IF NOT EXISTS listing_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    price INTEGER NOT NULL,
    seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(listing_id) REFERENCES listing(id)
);

-- Ingestion audit
CREATE TABLE IF NOT EXISTS ingestion_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    status TEXT,
    records_fetched INTEGER DEFAULT 0,
    records_ingested INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS source_raw_payload (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_listing_id TEXT,
    payload_json TEXT NOT NULL,
    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP
);

