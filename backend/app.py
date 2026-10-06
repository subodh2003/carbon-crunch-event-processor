import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.responses import Response

from aggregation import get_aggregates
from database import close_pool, get_connection, open_pool
from processor import process_event


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": datetime.now().astimezone().isoformat(),
        }

        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        return json.dumps(payload, separators=(",", ":"))


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())

logger = logging.getLogger("carbon_crunch")
logger.setLevel(logging.INFO)
logger.handlers.clear()
logger.addHandler(handler)
logger.propagate = False


@asynccontextmanager
async def lifespan(_app: FastAPI):
    open_pool()
    try:
        yield
    finally:
        close_pool()


app = FastAPI(
    title="Carbon Crunch Event Processor",
    lifespan=lifespan,
)


class EventPayload(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    payload: dict[str, Any]


class EventRequest(BaseModel):
    event: EventPayload


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadyResponse(BaseModel):
    status: Literal["ready"]
    database: Literal["ok"]


class ProcessEventResponse(BaseModel):
    status: Literal["processed", "duplicate"]
    message: str


class EventItem(BaseModel):
    id: int
    client_id: str
    metric: str
    amount: str
    timestamp: datetime
    processed_at: datetime


class AttemptItem(BaseModel):
    id: int
    source: str | None
    status: str
    error_message: str | None
    created_at: datetime


class AggregateItem(BaseModel):
    client_id: str
    count: int
    total_amount: str


class EventPage(BaseModel):
    items: list[EventItem]
    limit: int
    offset: int
    has_more: bool


class AttemptPage(BaseModel):
    items: list[AttemptItem]
    limit: int
    offset: int
    has_more: bool


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    start = time.perf_counter()

    try:
        response: Response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.exception(
            "request_failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": duration_ms,
            },
        )
        raise

    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


@app.get("/ready", response_model=ReadyResponse)
def ready():
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
    except Exception:
        logger.exception("database_readiness_check_failed")
        raise HTTPException(
            status_code=503,
            detail="Database is not ready",
        )

    return {
        "status": "ready",
        "database": "ok",
    }


@app.post("/events", response_model=ProcessEventResponse)
def ingest_event(request: EventRequest):
    try:
        return process_event(request.event.model_dump())

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


@app.get("/aggregates", response_model=list[AggregateItem])
def aggregates(
    client_id: str | None = Query(default=None, min_length=1, max_length=255),
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


@app.get("/attempts", response_model=AttemptPage)
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


@app.get("/events", response_model=EventPage)
def get_events(
    client_id: str | None = Query(default=None, min_length=1, max_length=255),
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
                "amount": str(row[3]),
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
