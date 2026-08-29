from datetime import datetime

from database import get_connection


def get_aggregates(
    client_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[dict]:
    query = """
        SELECT
            client_id,
            COUNT(*) AS count,
            COALESCE(SUM(amount), 0) AS total_amount
        FROM processed_events
        WHERE 1 = 1
    """

    params = []

    if client_id:
        query += " AND client_id = %s"
        params.append(client_id)

    if start_time:
        query += " AND event_timestamp >= %s"
        params.append(start_time)

    if end_time:
        query += " AND event_timestamp <= %s"
        params.append(end_time)

    query += """
        GROUP BY client_id
        ORDER BY client_id
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)

            rows = cur.fetchall()

    return [
        {
            "client_id": row[0],
            "count": row[1],
            "total_amount": str(row[2]),
        }
        for row in rows
    ]