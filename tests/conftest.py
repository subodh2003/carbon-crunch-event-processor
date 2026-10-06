import os
from pathlib import Path

import psycopg
import pytest


@pytest.fixture(scope="session", autouse=True)
def test_database():
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        pytest.fail(
            "Set TEST_DATABASE_URL (preferred) or DATABASE_URL to a PostgreSQL test database."
        )

    os.environ["DATABASE_URL"] = database_url

    schema_path = Path(__file__).resolve().parents[1] / "database" / "schema.sql"
    schema = schema_path.read_text(encoding="utf-8")

    with psycopg.connect(database_url) as conn:
        conn.execute(schema)
        conn.commit()

    yield

    with psycopg.connect(database_url) as conn:
        conn.execute(
            """
            TRUNCATE
                processed_events,
                raw_events,
                event_attempts
            RESTART IDENTITY CASCADE
            """
        )
        conn.commit()


@pytest.fixture(autouse=True)
def clean_database():
    database_url = os.environ["DATABASE_URL"]

    with psycopg.connect(database_url) as conn:
        conn.execute(
            """
            TRUNCATE
                processed_events,
                raw_events,
                event_attempts
            RESTART IDENTITY CASCADE
            """
        )
        conn.commit()

    yield
