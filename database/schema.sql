CREATE TABLE IF NOT EXISTS raw_events (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS processed_events (
    id BIGSERIAL PRIMARY KEY,
    raw_event_id BIGINT NOT NULL REFERENCES raw_events(id),
    client_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    fingerprint CHAR(64) NOT NULL UNIQUE,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS event_attempts (
    id BIGSERIAL PRIMARY KEY,
    source TEXT,
    payload JSONB,
    fingerprint CHAR(64),
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_processed_events_client_timestamp
    ON processed_events (client_id, event_timestamp);

CREATE INDEX IF NOT EXISTS idx_processed_events_processed_at
    ON processed_events (processed_at DESC);

CREATE INDEX IF NOT EXISTS idx_event_attempts_created_at
    ON event_attempts (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_event_attempts_fingerprint
    ON event_attempts (fingerprint);
