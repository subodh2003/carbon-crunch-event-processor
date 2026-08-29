import hashlib
import json

from psycopg.errors import UniqueViolation

from database import get_connection
from normalizer import normalize_event


def create_fingerprint(event: dict) -> str:
    canonical_event = {
    "client_id": event["client_id"],
    "metric": event["metric"],
    "amount": str(event["amount"]),
    "timestamp": event["timestamp"].isoformat(),
    }

    serialized = json.dumps(
        canonical_event,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def record_attempt(
    raw_event: dict,
    fingerprint: str | None,
    status: str,
    error_message: str | None = None,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO event_attempts (
                    source,
                    payload,
                    fingerprint,
                    status,
                    error_message
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    raw_event.get("source"),
                    json.dumps(raw_event.get("payload")),
                    fingerprint,
                    status,
                    error_message,
                ),
            )


def process_event(
    raw_event: dict,
    simulate_failure: bool = False,
) -> dict:

    # Normalize before touching the database.
    try:
        normalized = normalize_event(raw_event)

    except ValueError as exc:
        record_attempt(
            raw_event=raw_event,
            fingerprint=None,
            status="rejected",
            error_message=str(exc),
        )
        raise

    fingerprint = create_fingerprint(normalized)

    with get_connection() as conn:
        try:
            with conn.cursor() as cur:

                # Store the original event.
                cur.execute(
                    """
                    INSERT INTO raw_events (source, payload)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (
                        raw_event.get("source"),
                        json.dumps(raw_event.get("payload")),
                    ),
                )

                raw_event_id = cur.fetchone()[0]

                # Simulate a failure before the processed event is committed.
                if simulate_failure:
                    raise RuntimeError(
                        "Simulated database failure"
                    )

                # Store the normalized event.
                cur.execute(
                    """
                    INSERT INTO processed_events (
                        raw_event_id,
                        client_id,
                        metric,
                        amount,
                        event_timestamp,
                        fingerprint
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        raw_event_id,
                        normalized["client_id"],
                        normalized["metric"],
                        normalized["amount"],
                        normalized["timestamp"],
                        fingerprint,
                    ),
                )

            # Both inserts succeed together.
            conn.commit()

        except UniqueViolation:
            conn.rollback()

            record_attempt(
                raw_event=raw_event,
                fingerprint=fingerprint,
                status="duplicate",
            )

            return {
                "status": "duplicate",
                "message": "Event has already been processed",
            }

        except RuntimeError as exc:
            conn.rollback()

            record_attempt(
                raw_event=raw_event,
                fingerprint=fingerprint,
                status="failed",
                error_message=str(exc),
            )

            raise

        except Exception as exc:
            conn.rollback()

            record_attempt(
                raw_event=raw_event,
                fingerprint=fingerprint,
                status="failed",
                error_message="Unexpected processing error",
            )

            raise

    # Record success only after the transaction has committed.
    record_attempt(
        raw_event=raw_event,
        fingerprint=fingerprint,
        status="processed",
    )

    return {
        "status": "processed",
        "message": "Event processed successfully",
    }