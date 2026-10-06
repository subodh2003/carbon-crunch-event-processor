from datetime import timezone
from decimal import Decimal

import pytest

from normalizer import normalize_event


def test_normalize_aliases_and_defaults_to_source():
    event = {
        "source": "client-A",
        "payload": {
            "type": "energy",
            "value": "12.50",
            "time": "2026-08-29T10:00:00+05:30",
        },
    }

    result = normalize_event(event)

    assert result["client_id"] == "client-A"
    assert result["metric"] == "energy"
    assert result["amount"] == Decimal("12.50")
    assert result["timestamp"].tzinfo == timezone.utc
    assert result["timestamp"].isoformat() == "2026-08-29T04:30:00+00:00"


@pytest.mark.parametrize(
    ("event", "message"),
    [
        ({"payload": {}}, "Missing source"),
        ({"source": "client-A"}, "Payload must be an object"),
        (
            {
                "source": "client-A",
                "payload": {"amount": "10", "timestamp": "2026-08-29"},
            },
            "Missing metric/type",
        ),
        (
            {
                "source": "client-A",
                "payload": {"metric": "energy", "timestamp": "2026-08-29"},
            },
            "Missing amount/value",
        ),
        (
            {
                "source": "client-A",
                "payload": {"metric": "energy", "amount": "10"},
            },
            "Missing timestamp/time",
        ),
    ],
)
def test_normalize_rejects_invalid_events(event, message):
    with pytest.raises(ValueError, match=message):
        normalize_event(event)


def test_normalize_rejects_non_numeric_amount():
    event = {
        "source": "client-A",
        "payload": {
            "metric": "energy",
            "amount": "not-a-number",
            "timestamp": "2026-08-29",
        },
    }

    with pytest.raises(ValueError, match="Amount must be numeric"):
        normalize_event(event)


def test_normalize_rejects_invalid_timestamp():
    event = {
        "source": "client-A",
        "payload": {
            "metric": "energy",
            "amount": "10",
            "timestamp": "not-a-timestamp",
        },
    }

    with pytest.raises(ValueError, match="Invalid timestamp"):
        normalize_event(event)


def test_normalize_rejects_non_finite_amounts():
    base_event = {
        "source": "client-A",
        "payload": {
            "metric": "energy",
            "timestamp": "2026-08-29",
        },
    }

    for value in ("NaN", "Infinity", "-Infinity"):
        event = {
            **base_event,
            "payload": {
                **base_event["payload"],
                "amount": value,
            },
        }

        with pytest.raises(ValueError, match="Amount must be finite"):
            normalize_event(event)


@pytest.mark.parametrize("field", ["source", "metric", "client_id"])
def test_normalize_rejects_blank_identifiers(field):
    if field == "source":
        event = {
            "source": "   ",
            "payload": {
                "metric": "energy",
                "amount": "10",
                "timestamp": "2026-08-29",
            },
        }
    elif field == "metric":
        event = {
            "source": "client-A",
            "payload": {
                "metric": "   ",
                "amount": "10",
                "timestamp": "2026-08-29",
            },
        }
    else:
        event = {
            "source": "client-A",
            "payload": {
                "client_id": "   ",
                "metric": "energy",
                "amount": "10",
                "timestamp": "2026-08-29",
            },
        }

    with pytest.raises(ValueError, match=f"Missing {field}"):
        normalize_event(event)


def test_get_first_uses_alias_when_primary_value_is_null():
    event = {
        "source": "client-A",
        "payload": {
            "metric": None,
            "type": "energy",
            "amount": "10",
            "timestamp": "2026-08-29",
        },
    }

    result = normalize_event(event)

    assert result["metric"] == "energy"
