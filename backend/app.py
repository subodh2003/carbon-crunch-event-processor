from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aggregation import get_aggregates
from database import get_connection
from processor import process_event


app = FastAPI(title="Carbon Crunch Event Processor")


class EventRequest(BaseModel):
    event: dict
    simulate_failure: bool = False


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/events")
def ingest_event(request: EventRequest):
    try:
        return process_event(
            request.event,
            request.simulate_failure,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@app.get("/aggregates")
def aggregates(
    client_id: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
):
    if start_time and end_time and start_time > end_time:
        raise HTTPException(
            status_code=400,
            detail="start_time must be before end_time",
        )

    return get_aggregates(
        client_id=client_id,
        start_time=start_time,
        end_time=end_time,
    )


@app.get("/attempts")
def get_attempts(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = """
        SELECT
            id,
            source,
            status,
            error_message,
            created_at
        FROM event_attempts
        ORDER BY created_at DESC, id DESC
        LIMIT %s
        OFFSET %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (limit + 1, offset))
            rows = cur.fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]

    return {
        "items": [
            {
                "id": row[0],
                "source": row[1],
                "status": row[2],
                "error_message": row[3],
                "created_at": row[4],
            }
            for row in rows
        ],
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
    }


@app.get("/events")
def get_events(
    client_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = """
        SELECT
            id,
            client_id,
            metric,
            amount,
            event_timestamp,
            processed_at
        FROM processed_events
        WHERE 1 = 1
    """

    params = []

    if client_id:
        query += " AND client_id = %s"
        params.append(client_id)

    query += """
        ORDER BY processed_at DESC, id DESC
        LIMIT %s
        OFFSET %s
    """
    params.extend((limit + 1, offset))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]

    return {
        "items": [
            {
                "id": row[0],
                "client_id": row[1],
                "metric": row[2],
                "amount": float(row[3]),
                "timestamp": row[4],
                "processed_at": row[5],
            }
            for row in rows
        ],
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
    }


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

app.mount(
    "/",
    StaticFiles(directory=frontend_dir, html=True),
    name="frontend",
)
