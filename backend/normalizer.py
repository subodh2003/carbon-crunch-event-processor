from datetime import timezone
from decimal import Decimal, InvalidOperation

from dateutil import parser


def get_first(payload: dict, *names):
    for name in names:
        if name in payload:
            return payload[name]

    return None


def normalize_event(raw_event: dict) -> dict:
    source = raw_event.get("source")

    if not source:
        raise ValueError("Missing source")

    payload = raw_event.get("payload")

    if not isinstance(payload, dict):
        raise ValueError("Payload must be an object")

    client_id = get_first(payload, "client_id", "client")
    metric = get_first(payload, "metric", "type")
    amount = get_first(payload, "amount", "value")
    timestamp = get_first(payload, "timestamp", "time")

    # The source field is also accepted as the client identifier.
    if client_id is None:
        client_id = source

    if metric is None:
        raise ValueError("Missing metric/type")

    if amount is None:
        raise ValueError("Missing amount/value")

    if timestamp is None:
        raise ValueError("Missing timestamp/time")

    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        raise ValueError("Amount must be numeric")

    try:
        timestamp = parser.parse(str(timestamp))
    except (ValueError, TypeError, OverflowError):
        raise ValueError("Invalid timestamp")

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    timestamp = timestamp.astimezone(timezone.utc)

    return {
        "client_id": str(client_id),
        "metric": str(metric),
        "amount": amount,
        "timestamp": timestamp,
    }