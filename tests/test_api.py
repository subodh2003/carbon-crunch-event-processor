from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_event_request_requires_source():
    response = client.post(
        "/events",
        json={
            "event": {
                "payload": {
                    "metric": "energy",
                    "amount": "10",
                    "timestamp": "2026-08-29",
                }
            }
        },
    )

    assert response.status_code == 422


def test_events_rejects_invalid_pagination():
    response = client.get("/events?limit=0")

    assert response.status_code == 422
