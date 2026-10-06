import os
from threading import Lock

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool


load_dotenv()


POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "10"))

if POOL_MIN_SIZE < 1 or POOL_MAX_SIZE < POOL_MIN_SIZE:
    raise RuntimeError(
        "DB_POOL_MAX_SIZE must be greater than or equal to DB_POOL_MIN_SIZE"
    )


_pool: ConnectionPool | None = None
_pool_lock = Lock()


def get_pool() -> ConnectionPool:
    global _pool

    if _pool is None:
        with _pool_lock:
            if _pool is None:
                database_url = os.getenv("DATABASE_URL")

                if not database_url:
                    raise RuntimeError(
                        "DATABASE_URL environment variable is not set"
                    )

                _pool = ConnectionPool(
                    conninfo=database_url,
                    min_size=POOL_MIN_SIZE,
                    max_size=POOL_MAX_SIZE,
                    timeout=10,
                    open=False,
                )

    return _pool


def open_pool() -> None:
    get_pool().open(wait=False)


def get_connection():
    return get_pool().connection()


def close_pool() -> None:
    global _pool

    if _pool is not None:
        _pool.close()
        _pool = None
