from datetime import timezone
from decimal import Decimal, InvalidOperation

from dateutil import parser


MAX_IDENTIFIER_LENGTH = 255


def get_first(payload: dict, *names):
    for name in names:
        if name in payload and payload[name] is not None:
            return payload[name]

    return None


def validate_identifier(value, field_name: str) -> str:
    value = str(value).strip()

    if not value:
        raise ValueError(f"Missing {field_name}")

    if len(value) > MAX_IDENTIFIER_LENGTH:
        raise ValueError(f"{field_name} is too long")

    return value


def parse_amount(value) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Amount must be numeric")

    if not amount.is_finite():
        raise ValueError("Amount must be finite")

    return amount


def normalize_event(raw_event: dict) -> dict:
    source = raw_event.get("source")

    if source is None:
        raise ValueError("Missing source")

    source = validate_identifier(source, "source")

    payload = raw_event.get("payload")

    if not isinstance(payload, dict):
        raise ValueError("Payload must be an object")

    client_id = get_first(payload, "client_id", "client")
    metric = get_first(payload, "metric", "type")
    amount = get_first(payload, "amount", "value")
    timestamp = get_first(payload, "timestamp", "time")

    if client_id is None:
        client_id = source

    if metric is None:
        raise ValueError("Missing metric/type")

    if amount is None:
        raise ValueError("Missing amount/value")

    if timestamp is None:
        raise ValueError("Missing timestamp/time")

    client_id = validate_identifier(client_id, "client_id")
    metric = validate_identifier(metric, "metric")
    amount = parse_amount(amount)

    try:
        timestamp = parser.parse(str(timestamp))
    except (ValueError, TypeError, OverflowError):
        raise ValueError("Invalid timestamp")

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    timestamp = timestamp.astimezone(timezone.utc)

    return {
        "client_id": client_id,
        "metric": metric,
        "amount": amount,
        "timestamp": timestamp,
    }
