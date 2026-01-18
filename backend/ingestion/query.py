from typing import List, Dict
from ingestion.db import get_connection


def list_runs(limit: int = 20) -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, source, started_at, finished_at, status,
                   records_fetched, records_ingested, records_failed, notes
            FROM ingestion_run
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_latest_run() -> Dict:
    runs = list_runs(limit=1)
    return runs[0] if runs else {}


def list_live_listings(limit: int = 50) -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT l.id, l.source, l.source_listing_id, l.title, l.price, l.mileage,
                   l.location_city, l.location_state, l.condition, l.url, l.status,
                   cs.year, cm.name AS model, mk.name AS make, ct.name AS trim
            FROM listing l
            JOIN car_spec cs ON l.car_spec_id = cs.id
            JOIN car_trim ct ON cs.trim_id = ct.id
            JOIN car_model cm ON ct.model_id = cm.id
            JOIN car_make mk ON cm.make_id = mk.id
            WHERE l.status = 'active'
            ORDER BY l.updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


