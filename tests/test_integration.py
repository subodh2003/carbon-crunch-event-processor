import concurrent.futures
import os

import psycopg

from processor import process_event


EVENT = {
    "source": "integration-test",
    "payload": {
        "metric": "energy",
        "amount": "100.00",
        "timestamp": "2026-08-29T10:00:00Z",
    },
}


def database_url() -> str:
    return os.environ["TEST_DATABASE_URL"]


def count_rows(table: str) -> int:
    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            return cur.fetchone()[0]


def test_concurrent_duplicate_submissions_process_exactly_once():
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda _: process_event(EVENT), range(10)))

    statuses = [result["status"] for result in results]

    assert statuses.count("processed") == 1
    assert statuses.count("duplicate") == 9
    assert count_rows("processed_events") == 1
    assert count_rows("raw_events") == 1
    assert count_rows("event_attempts") == 10


def test_failed_processing_does_not_commit_partial_event():
    try:
        process_event(EVENT, simulate_failure=True)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected simulated failure")

    assert count_rows("raw_events") == 0
    assert count_rows("processed_events") == 0
    assert count_rows("event_attempts") == 1

    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, error_message
                FROM event_attempts
                LIMIT 1
                """
            )
            status, error_message = cur.fetchone()

    assert status == "failed"
    assert error_message == "Simulated database failure"
