import json
import sqlite3
from pathlib import Path
from typing import Dict, Optional


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        conn.commit()


def upsert_make(conn: sqlite3.Connection, make_name: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO car_make (name) VALUES (?)",
        (make_name,),
    )
    row = conn.execute(
        "SELECT id FROM car_make WHERE name = ?",
        (make_name,),
    ).fetchone()
    return int(row["id"])


def upsert_model(conn: sqlite3.Connection, make_id: int, model_name: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO car_model (make_id, name) VALUES (?, ?)",
        (make_id, model_name),
    )
    row = conn.execute(
        "SELECT id FROM car_model WHERE make_id = ? AND name = ?",
        (make_id, model_name),
    ).fetchone()
    return int(row["id"])


def upsert_trim(
    conn: sqlite3.Connection,
    model_id: int,
    trim_name: str,
    year_start: Optional[int],
    year_end: Optional[int],
) -> int:
    conn.execute(
        """
        INSERT OR IGNORE INTO car_trim (model_id, name, year_start, year_end)
        VALUES (?, ?, ?, ?)
        """,
        (model_id, trim_name, year_start, year_end),
    )
    row = conn.execute(
        """
        SELECT id FROM car_trim
        WHERE model_id = ? AND name = ? AND year_start IS ? AND year_end IS ?
        """,
        (model_id, trim_name, year_start, year_end),
    ).fetchone()
    return int(row["id"])


def upsert_car_spec(conn: sqlite3.Connection, spec: Dict) -> int:
    conn.execute(
        """
        INSERT OR IGNORE INTO car_spec (
            trim_id, year, drivetrain, body_type, power_hp, torque_lb_ft,
            mpg_city, mpg_highway, mpg_combined, zero_to_sixty,
            reliability_score, ownership_cost_score, character_tags
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            spec["trim_id"],
            spec["year"],
            spec.get("drivetrain"),
            spec.get("body_type"),
            spec.get("power_hp"),
            spec.get("torque_lb_ft"),
            spec.get("mpg_city"),
            spec.get("mpg_highway"),
            spec.get("mpg_combined"),
            spec.get("zero_to_sixty"),
            spec.get("reliability_score"),
            spec.get("ownership_cost_score"),
            json.dumps(spec.get("character_tags", [])),
        ),
    )
    row = conn.execute(
        "SELECT id FROM car_spec WHERE trim_id = ? AND year = ?",
        (spec["trim_id"], spec["year"]),
    ).fetchone()
    return int(row["id"])


def upsert_listing(conn: sqlite3.Connection, listing: Dict) -> int:
    conn.execute(
        """
        INSERT OR IGNORE INTO listing (
            source, source_listing_id, car_spec_id, title, price, mileage,
            location_city, location_state, condition, url, listed_at, last_seen_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            listing["source"],
            listing["source_listing_id"],
            listing["car_spec_id"],
            listing.get("title"),
            listing.get("price"),
            listing.get("mileage"),
            listing.get("location_city"),
            listing.get("location_state"),
            listing.get("condition"),
            listing.get("url"),
            listing.get("listed_at"),
            listing.get("last_seen_at"),
            listing.get("status", "active"),
        ),
    )
    row = conn.execute(
        """
        SELECT id, price FROM listing
        WHERE source = ? AND source_listing_id = ?
        """,
        (listing["source"], listing["source_listing_id"]),
    ).fetchone()
    listing_id = int(row["id"])
    if row["price"] != listing.get("price") and listing.get("price") is not None:
        conn.execute(
            "INSERT INTO listing_price_history (listing_id, price) VALUES (?, ?)",
            (listing_id, listing["price"]),
        )
    conn.execute(
        """
        UPDATE listing
        SET price = ?, mileage = ?, last_seen_at = ?, status = 'active', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            listing.get("price"),
            listing.get("mileage"),
            listing.get("last_seen_at"),
            listing_id,
        ),
    )
    return listing_id


def mark_missing_listings_inactive(conn: sqlite3.Connection, source: str, seen_ids: set) -> int:
    if not seen_ids:
        return 0
    placeholders = ",".join(["?"] * len(seen_ids))
    params = [source, *seen_ids]
    cursor = conn.execute(
        f"""
        UPDATE listing
        SET status = 'inactive', updated_at = CURRENT_TIMESTAMP
        WHERE source = ?
        AND id NOT IN ({placeholders})
        """,
        params,
    )
    return cursor.rowcount

