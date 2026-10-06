# Carbon Crunch Event Processor

Transactional event-ingestion service built with **FastAPI + PostgreSQL**.

The service accepts loosely shaped events, normalizes them into a canonical form, prevents duplicate processing with a deterministic fingerprint and a database-level uniqueness constraint, records processing attempts, and exposes aggregation APIs.

## Architecture

```
Client
  |
  v
FastAPI
  |
  +--> Request validation
  |
  +--> Event normalization
  |      |
  |      +--> aliases -> canonical fields
  |      +--> UTC timestamp
  |      +--> Decimal amount
  |
  +--> PostgreSQL transaction
         |
         +--> raw_events
         |
         +--> processed_events
         |      |
         |      +--> UNIQUE(fingerprint)
         |
         +--> event_attempts
                |
                +--> processed / duplicate / failed / rejected

Aggregation APIs
  |
  v
PostgreSQL
```

## Core guarantees

### Duplicate suppression

A normalized event is identified by:

- `client_id`
- `metric`
- canonical `amount`
- normalized UTC `timestamp`

Those fields are serialized deterministically and hashed with SHA-256.

The fingerprint has a PostgreSQL `UNIQUE` constraint, so concurrent identical submissions are resolved by the database rather than a non-atomic application-side "check then insert".

### Transactional processing

A successful request commits:

1. the raw event
2. the normalized/processed event
3. the successful processing-attempt record

as one transaction.

If processing fails before commit, the raw and processed records are rolled back. The failure/duplicate audit record is written separately after rollback so the attempt remains observable without contaminating processed data.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/ready` | PostgreSQL readiness check |
| POST | `/events` | Ingest and process an event |
| GET | `/events` | List processed events with pagination |
| GET | `/aggregates` | Aggregate processed amounts by client |
| GET | `/attempts` | List processing attempts with pagination |

### Example ingestion

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "source": "client_A",
      "payload": {
        "metric": "energy",
        "amount": "1200.00",
        "timestamp": "2026-10-06T10:00:00Z"
      }
    }
  }'
```

Example response:

```json
{
  "status": "processed",
  "message": "Event processed successfully"
}
```

Submitting the same normalized event again returns:

```json
{
  "status": "duplicate",
  "message": "Event has already been processed"
}
```

### Pagination

```text
GET /events?client_id=client_A&limit=50&offset=0
GET /attempts?limit=50&offset=0
```

Both endpoints cap `limit` at 100 and return a `has_more` flag.

## Database

The schema is versioned with **Alembic**.

Tables:

- `raw_events` — original incoming payload
- `processed_events` — canonical processed event
- `event_attempts` — processing/audit history

Important indexes:

- `processed_events(client_id, event_timestamp)`
- `processed_events(processed_at)`
- `event_attempts(created_at)`
- `event_attempts(fingerprint)`

## Running with Docker

Requirements:

- Docker
- Docker Compose

Start the application and PostgreSQL:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:8000
```

Migrations are applied automatically by the application container with:

```text
alembic upgrade head
```

To reset the development database completely:

```bash
docker compose down -v
docker compose up --build
```

## Configuration

Copy `.env.example` to `.env` for local development.

Important settings:

- `DATABASE_URL`
- `DB_POOL_MIN_SIZE`
- `DB_POOL_MAX_SIZE`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `APP_PORT`

The application uses a bounded Psycopg connection pool and returns connections to the pool after each operation.

## Testing

The test suite contains:

- normalizer unit tests
- fingerprint/idempotency tests
- API validation tests
- PostgreSQL integration tests
- concurrent duplicate-processing tests
- transaction rollback tests

Run locally against a PostgreSQL test database:

```bash
export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/carbon_crunch_test
pytest -q
```

The repository also includes GitHub Actions CI that runs:

- Ruff
- Python compilation checks
- pytest against PostgreSQL

## Operational behaviour

- `/health` checks that the application process is serving requests.
- `/ready` verifies PostgreSQL connectivity.
- Requests receive an `X-Request-ID` header.
- Structured JSON request logs include request ID, method, path, status code, and latency.
- Docker runs the application as a non-root user.

## Why PostgreSQL is currently the bottleneck

The current design uses one PostgreSQL database for ingestion, deduplication, audit records, and aggregation.

At larger scale, likely bottlenecks are:

- database connection capacity
- transaction contention
- index growth
- aggregation cost
- offset pagination at large offsets

A future scale-out design could separate ingestion from asynchronous processing with a durable queue and worker pool.

## Limitations

This is a backend engineering project, not a production multi-tenant platform. It currently does not implement:

- authentication/authorization
- rate limiting
- distributed queue-based retries
- database replication/failover
- cursor-based pagination
- multi-instance coordination beyond PostgreSQL's transactional guarantees

These are deliberate scope boundaries rather than hidden behaviour.

## Project structure

```text
.
├── alembic/
│   ├── env.py
│   └── versions/
├── backend/
│   ├── aggregation.py
│   ├── app.py
│   ├── database.py
│   ├── normalizer.py
│   ├── processor.py
│   └── requirements*.txt
├── frontend/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── README.md
```
