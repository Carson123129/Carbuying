import argparse
import json
from datetime import datetime, timezone

from ingestion.db import (
    get_connection,
    init_db,
    mark_missing_listings_inactive,
    upsert_car_spec,
    upsert_listing,
    upsert_make,
    upsert_model,
    upsert_trim,
)
from ingestion.normalize import normalize_car_spec, normalize_listing
from ingestion.sources import mock_source, marketcheck


SOURCES = {
    "mock": mock_source,
    "marketcheck": marketcheck,
}


def run(source_name: str) -> None:
    if source_name not in SOURCES:
        raise ValueError(f"Unknown source: {source_name}")

    init_db()
    source = SOURCES[source_name]
    payload = source.fetch()
    cars = payload.get("cars", [])
    listings = payload.get("listings", [])

    seen_listing_ids = set()
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        run_id = conn.execute(
            "INSERT INTO ingestion_run (source, status) VALUES (?, ?)",
            (source_name, "running"),
        ).lastrowid

        records_fetched = len(cars) + len(listings)
        records_ingested = 0
        records_failed = 0

        for car in cars:
            try:
                norm = normalize_car_spec(car)
                make_id = upsert_make(conn, norm["make"])
                model_id = upsert_model(conn, make_id, norm["model"])
                trim_id = upsert_trim(conn, model_id, norm["trim"], None, None)
                spec = {
                    "trim_id": trim_id,
                    "year": norm["year"],
                    "drivetrain": norm.get("drivetrain"),
                    "body_type": norm.get("body_type"),
                    "power_hp": norm.get("power_hp"),
                    "torque_lb_ft": norm.get("torque_lb_ft"),
                    "mpg_combined": norm.get("mpg_combined"),
                    "zero_to_sixty": norm.get("zero_to_sixty"),
                    "reliability_score": norm.get("reliability_score"),
                    "ownership_cost_score": norm.get("ownership_cost_score"),
                    "character_tags": norm.get("character_tags", []),
                }
                upsert_car_spec(conn, spec)
                records_ingested += 1
            except Exception:
                records_failed += 1

        for listing in listings:
            try:
                norm = normalize_listing(listing)
                source_id = norm["source_listing_id"]
                if not source_id:
                    raise ValueError("Missing source_listing_id")

                car_id = listing.get("car_id")
                if not car_id:
                    raise ValueError("Missing car_id")

                car_match = next((c for c in cars if c.get("id") == car_id), None)
                if not car_match:
                    raise ValueError("No matching car for listing")

                norm_car = normalize_car_spec(car_match)
                make_id = upsert_make(conn, norm_car["make"])
                model_id = upsert_model(conn, make_id, norm_car["model"])
                trim_id = upsert_trim(conn, model_id, norm_car["trim"], None, None)
                spec_id = upsert_car_spec(
                    conn,
                    {
                        "trim_id": trim_id,
                        "year": norm_car["year"],
                        "drivetrain": norm_car.get("drivetrain"),
                        "body_type": norm_car.get("body_type"),
                        "power_hp": norm_car.get("power_hp"),
                        "torque_lb_ft": norm_car.get("torque_lb_ft"),
                        "mpg_combined": norm_car.get("mpg_combined"),
                        "zero_to_sixty": norm_car.get("zero_to_sixty"),
                        "reliability_score": norm_car.get("reliability_score"),
                        "ownership_cost_score": norm_car.get("ownership_cost_score"),
                        "character_tags": norm_car.get("character_tags", []),
                    },
                )

                norm["car_spec_id"] = spec_id
                norm["last_seen_at"] = now_iso
                listing_id = upsert_listing(conn, norm)
                seen_listing_ids.add(listing_id)
                records_ingested += 1
            except Exception:
                records_failed += 1

        marked = mark_missing_listings_inactive(conn, source_name, seen_listing_ids)
        conn.execute(
            """
            UPDATE ingestion_run
            SET finished_at = ?, status = ?, records_fetched = ?, records_ingested = ?, records_failed = ?, notes = ?
            WHERE id = ?
            """,
            (
                now_iso,
                "completed",
                records_fetched,
                records_ingested,
                records_failed,
                f"Marked inactive: {marked}",
                run_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO source_raw_payload (source, source_listing_id, payload_json)
            VALUES (?, ?, ?)
            """,
            (source_name, None, json.dumps({"cars": len(cars), "listings": len(listings)})),
        )
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ingestion pipeline")
    parser.add_argument("--source", default="mock", help="Source name")
    args = parser.parse_args()
    run(args.source)


if __name__ == "__main__":
    main()

