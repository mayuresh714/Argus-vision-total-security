"""Service factory wiring + API surface.

The threaded service is smoke-tested (starts, produces events on a fake source,
stops cleanly); the API is tested against a service whose repository we seed
directly, so the HTTP layer is verified without depending on thread timing.
"""

import time

from fastapi.testclient import TestClient

from argus.api.app import create_app
from argus.config import AppConfig
from argus.domain import Event, Severity, utcnow
from argus.pipeline.service import build_service


def _fake_service():
    cfg = AppConfig.from_dict(
        {
            "camera": {"id": "cam-01", "source": "fake", "sample_interval_seconds": 0.01},
            "vlm": {"backend": "mock"},
            "storage": {"backend": "memory"},
            "notifiers": [{"type": "console"}],
        }
    )
    return build_service(cfg)


def test_build_service_smoke_start_stop():
    service = _fake_service()
    assert service.is_running is False
    service.start()
    assert service.is_running is True
    time.sleep(0.2)  # let a few samples flow
    service.stop()
    assert service.is_running is False
    # The default mock scores ~0.1, so events accrue but no alerts.
    assert service.metrics_snapshot()["counters"].get("frames_sampled", 0) >= 1


def test_healthz_and_metrics():
    service = _fake_service()
    client = TestClient(create_app(service))
    health = client.get("/healthz").json()
    assert health["status"] == "ok"
    assert health["camera_id"] == "cam-01"
    assert client.get("/metrics").status_code == 200


def test_events_and_alerts_endpoints_read_repository():
    service = _fake_service()
    event = Event(
        camera_id="cam-01",
        captured_at=utcnow(),
        score=0.9,
        severity=Severity.URGENT,
        reason="concealment near exit",
        tags=("concealment",),
        model="mock",
        vlm_latency_ms=5,
        became_alert=True,
    )
    service.repository.save_event(event)

    client = TestClient(create_app(service))
    events = client.get("/events").json()
    assert len(events) == 1
    assert events[0]["reason"] == "concealment near exit"

    got = client.get(f"/events/{event.id}").json()
    assert got["id"] == event.id
    assert client.get("/events/does-not-exist").status_code == 404


def test_control_endpoints_toggle_running():
    service = _fake_service()
    client = TestClient(create_app(service))
    assert client.post("/control/start").json()["running"] is True
    assert client.post("/control/stop").json()["running"] is False
