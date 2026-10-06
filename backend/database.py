import os

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")


POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "10"))

if POOL_MIN_SIZE < 1 or POOL_MAX_SIZE < POOL_MIN_SIZE:
    raise RuntimeError(
        "DB_POOL_MAX_SIZE must be greater than or equal to DB_POOL_MIN_SIZE"
    )


pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=POOL_MIN_SIZE,
    max_size=POOL_MAX_SIZE,
    timeout=10,
    open=True,
)


def get_connection():
    return pool.connection()


def close_pool():
    pool.close()
