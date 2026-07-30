"""FastAPI application factory.

The API is intentionally thin: it reads Events/Alerts from the repository and
exposes health/metrics + start/stop control. All the real work happens in the
service's background threads. This separation means the UI (frontend/) talks to
a stable, storage-backed API and never to the pipeline internals.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from argus.api.schemas import AlertOut, ControlOut, EventOut, HealthOut
from argus.pipeline.service import ArgusService


def create_app(service: ArgusService) -> FastAPI:
    app = FastAPI(
        title="Argus v0 — Single Camera",
        version="0.1.0",
        description="Suspicious-activity detection for one CCTV feed.",
    )

    @app.get("/healthz", response_model=HealthOut, tags=["system"])
    def healthz() -> HealthOut:
        return HealthOut(
            status="ok",
            running=service.is_running,
            camera_id=service.config.camera.id,
            sample_interval_seconds=service.config.camera.sample_interval_seconds,
        )

    @app.get("/metrics", tags=["system"])
    def metrics() -> dict:
        return service.metrics_snapshot()

    @app.get("/events", response_model=list[EventOut], tags=["events"])
    def list_events(
        limit: int = Query(100, ge=1, le=1000),
        camera_id: str | None = None,
    ) -> list[EventOut]:
        return [EventOut.of(e) for e in service.repository.list_events(limit=limit, camera_id=camera_id)]

    @app.get("/events/{event_id}", response_model=EventOut, tags=["events"])
    def get_event(event_id: str) -> EventOut:
        event = service.repository.get_event(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="event not found")
        return EventOut.of(event)

    @app.get("/alerts", response_model=list[AlertOut], tags=["alerts"])
    def list_alerts(
        limit: int = Query(100, ge=1, le=1000),
        camera_id: str | None = None,
    ) -> list[AlertOut]:
        return [AlertOut.of(a) for a in service.repository.list_alerts(limit=limit, camera_id=camera_id)]

    @app.get("/alerts/{alert_id}", response_model=AlertOut, tags=["alerts"])
    def get_alert(alert_id: str) -> AlertOut:
        alert = service.repository.get_alert(alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail="alert not found")
        return AlertOut.of(alert)

    @app.post("/control/start", response_model=ControlOut, tags=["control"])
    def start() -> ControlOut:
        service.start()
        return ControlOut(running=service.is_running)

    @app.post("/control/stop", response_model=ControlOut, tags=["control"])
    def stop() -> ControlOut:
        service.stop()
        return ControlOut(running=service.is_running)

    return app
