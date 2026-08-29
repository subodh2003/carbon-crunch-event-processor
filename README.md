# Carbon Crunch Event Processor

## Assumptions

- PostgreSQL is used as the persistent database.
- Each event contains a `source` and `payload`.
- The payload may use aliases such as `metric`/`type`, `amount`/`value`, and `timestamp`/`time`.
- The `source` is used as the client identifier when `client` or `client_id` is not provided.
- Events with the same normalized client, metric, amount, and timestamp are considered duplicates.
- Amounts are treated as decimal values and timestamps are normalized to UTC.
- The frontend is served directly by FastAPI to keep the deployment simple.

## How does your system prevent double counting?

Each normalized event is converted into a deterministic fingerprint using SHA-256.

The fingerprint is generated from:

- client ID
- metric
- amount
- normalized timestamp

The fingerprint has a database-level `UNIQUE` constraint in `processed_events`.

Therefore, even if the same event is submitted multiple times or multiple identical requests arrive concurrently, PostgreSQL allows only one processed record for that fingerprint. Duplicate attempts are detected through the unique constraint and are not included in aggregation.

I also tested 10 concurrent submissions of the same event. Only one was processed and the remaining requests were treated as duplicates.

## What happens if the database fails mid-request?

The raw event insertion and processed event insertion are performed inside the same PostgreSQL transaction.

The flow is:

1. Insert the raw event.
2. Normalize and insert the processed event.
3. Commit the transaction.

If an error occurs before the commit, the transaction is rolled back. Therefore, a partially processed event does not remain in `processed_events` and cannot affect aggregation.

The failure is recorded separately in `event_attempts`, so the failed attempt remains visible without corrupting the processed data.

The system also supports simulated database failures for testing.

## What would break first at scale?

The PostgreSQL database would likely become the first bottleneck because all event ingestion, deduplication, and aggregation currently depend on a single database.

At higher throughput, database connections, transaction contention, indexes, and aggregation queries would become increasingly expensive.

The next improvements would be connection pooling, better indexing/query optimization, batching, and eventually separating ingestion from asynchronous processing using a queue.