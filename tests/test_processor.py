from datetime import datetime, timezone
from decimal import Decimal

from processor import create_fingerprint


def make_event(
    *,
    client_id="client-A",
    metric="energy",
    amount=Decimal("10.50"),
    timestamp=datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
):
    return {
        "client_id": client_id,
        "metric": metric,
        "amount": amount,
        "timestamp": timestamp,
    }


def test_fingerprint_is_deterministic():
    event = make_event()

    assert create_fingerprint(event) == create_fingerprint(event)


def test_fingerprint_changes_when_event_identity_changes():
    original = make_event()

    assert create_fingerprint(original) != create_fingerprint(
        make_event(amount=Decimal("11.50"))
    )
    assert create_fingerprint(original) != create_fingerprint(
        make_event(metric="water")
    )
    assert create_fingerprint(original) != create_fingerprint(
        make_event(client_id="client-B")
    )


def test_fingerprint_is_sha256_hex():
    fingerprint = create_fingerprint(make_event())

    assert len(fingerprint) == 64
    int(fingerprint, 16)
