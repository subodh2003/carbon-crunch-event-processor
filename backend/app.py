from pathlib import Path

from fastapi.staticfiles import StaticFiles

from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
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
def get_attempts():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    source,
                    status,
                    error_message,
                    created_at
                FROM event_attempts
                ORDER BY created_at DESC
                """
            )

            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "source": row[1],
            "status": row[2],
            "error_message": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]

@app.get("/events")
def get_events(
    client_id: str | None = Query(default=None),
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

    query += " ORDER BY processed_at DESC"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "client_id": row[1],
            "metric": row[2],
            "amount": float(row[3]),
            "timestamp": row[4],
            "processed_at": row[5],
        }
        for row in rows
    ]

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

app.mount(
    "/",
    StaticFiles(directory=frontend_dir, html=True),
    name="frontend",
)