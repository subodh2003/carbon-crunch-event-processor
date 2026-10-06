import os
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config

from database import close_pool, open_pool


ROOT = Path(__file__).resolve().parents[1]


def truncate_database(database_url: str) -> None:
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


@pytest.fixture(scope="session", autouse=True)
def test_database():
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        pytest.fail(
            "Set TEST_DATABASE_URL or DATABASE_URL to a PostgreSQL test database."
        )

    os.environ["DATABASE_URL"] = database_url

    config = Config(str(ROOT / "alembic.ini"))
    command.upgrade(config, "head")

    truncate_database(database_url)
    open_pool()

    yield

    close_pool()
    truncate_database(database_url)


@pytest.fixture(autouse=True)
def clean_database():
    database_url = os.environ["DATABASE_URL"]

    close_pool()
    truncate_database(database_url)
    open_pool()

    yield

    close_pool()
