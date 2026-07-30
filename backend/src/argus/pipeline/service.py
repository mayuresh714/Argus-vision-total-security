"""ArgusService — the composition root.

This is the single place that knows how to turn an ``AppConfig`` into concrete
collaborators (Factory functions) and wire them together (Dependency Injection).
Every other module depends only on abstractions; the coupling to concrete
classes lives here and nowhere else.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Sequence

from argus.alerting.manager import AlertManager
from argus.alerting.notifiers import (
    ConsoleNotifier,
    FileNotifier,
    Notifier,
    WebhookNotifier,
)
from argus.clock import Clock, SystemClock
from argus.config import AppConfig, NotifierConfig
from argus.decision.engine import DecisionEngine
from argus.domain import AnalysisUnit
from argus.metrics import Metrics
from argus.pipeline.latest_slot import LatestSlot
from argus.pipeline.sampler import Sampler
from argus.pipeline.worker import InferenceWorker
from argus.sources.base import FrameSource
from argus.sources.fake_source import FakeSource
from argus.storage.base import EvidenceWriter, Repository
from argus.storage.evidence import FileEvidenceWriter, NullEvidenceWriter
from argus.storage.memory_repository import InMemoryRepository
from argus.storage.sqlite_repository import SqliteRepository
from argus.vlm.base import VlmBackend
from argus.vlm.mock_backend import MockVlmBackend

log = logging.getLogger("argus.service")


# --- factories ---------------------------------------------------------------


def create_source(config: AppConfig) -> FrameSource:
    cam = config.camera
    if cam.source == "fake":
        # A looping single placeholder frame; real demos pass a FakeSource in.
        return FakeSource([FakeSource.solid_frame(cam.id)], loop=True)
    # Lazy import keeps OpenCV optional (docs: requirements-video.txt).
    from argus.sources.opencv_source import FileVideoSource, RtspSource

    if cam.source == "file":
        return FileVideoSource(cam.uri, cam.id)
    if cam.source == "rtsp":
        return RtspSource(cam.uri, cam.id)
    raise ValueError(f"unknown source type: {cam.source}")  # pragma: no cover


def create_vlm(config: AppConfig) -> VlmBackend:
    vlm = config.vlm
    if vlm.backend == "mock":
        # Deterministic gentle default so a mock run is quiet, not alarmist.
        return MockVlmBackend(scorer=lambda _u: (0.1, "mock: nominal scene", ("mock",)))
    from argus.vlm.openai_compatible_backend import OpenAiCompatibleVlmBackend

    return OpenAiCompatibleVlmBackend(
        endpoint=vlm.endpoint,
        model=vlm.model,
        api_key_env=vlm.api_key_env,
        timeout_seconds=vlm.timeout_seconds,
    )


def create_repository(config: AppConfig) -> Repository:
    st = config.storage
    if st.backend == "memory":
        return InMemoryRepository()
    return SqliteRepository(st.path)


def create_evidence_writer(config: AppConfig) -> EvidenceWriter:
    st = config.storage
    if st.backend == "memory":
        return NullEvidenceWriter()
    return FileEvidenceWriter(st.evidence_dir)


def create_notifiers(configs: Sequence[NotifierConfig]) -> list[Notifier]:
    notifiers: list[Notifier] = []
    for nc in configs:
        if nc.type == "console":
            notifiers.append(ConsoleNotifier())
        elif nc.type == "file":
            notifiers.append(FileNotifier(nc.options["path"]))
        elif nc.type == "webhook":
            notifiers.append(
                WebhookNotifier(nc.options["url"], timeout=float(nc.options.get("timeout", 5.0)))
            )
        else:  # pragma: no cover - validated upstream
            raise ValueError(f"unknown notifier type: {nc.type}")
    return notifiers


# --- service -----------------------------------------------------------------


class ArgusService:
    """Owns the wired-together pipeline and its two threads (sampler + worker).

    Constructed via :func:`build_service`. Exposes ``start``/``stop`` and the
    repository/metrics for the API layer to read.
    """

    def __init__(
        self,
        *,
        config: AppConfig,
        source: FrameSource,
        vlm: VlmBackend,
        decision_engine: DecisionEngine,
        alert_manager: AlertManager,
        repository: Repository,
        metrics: Metrics,
        clock: Clock,
    ) -> None:
        self.config = config
        self.repository = repository
        self.metrics = metrics
        self._source = source
        self._slot: LatestSlot[AnalysisUnit] = LatestSlot()
        self._sampler = Sampler(
            source=source,
            slot=self._slot,
            interval_seconds=config.camera.sample_interval_seconds,
            metrics=metrics,
            clock=clock,
        )
        self._worker = InferenceWorker(
            slot=self._slot,
            vlm=vlm,
            decision_engine=decision_engine,
            alert_manager=alert_manager,
            repository=repository,
            metrics=metrics,
        )
        self._threads: list[threading.Thread] = []
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._threads = [
            threading.Thread(target=self._worker.run, name="argus-worker", daemon=True),
            threading.Thread(target=self._sampler.run, name="argus-sampler", daemon=True),
        ]
        for t in self._threads:
            t.start()
        log.info("Argus service started (k=%.1fs)", self.config.camera.sample_interval_seconds)

    def stop(self, timeout: float = 5.0) -> None:
        if not self._running:
            return
        self._sampler.stop()
        self._worker.stop()
        self._slot.close()
        for t in self._threads:
            t.join(timeout=timeout)
        try:
            self._source.close()
        except Exception:  # best-effort
            pass
        self._running = False
        log.info("Argus service stopped")

    def metrics_snapshot(self) -> dict:
        snap = self.metrics.snapshot()
        snap.setdefault("counters", {})["frames_dropped"] = self._slot.dropped
        return snap


def build_service(config: AppConfig, *, clock: Clock | None = None) -> ArgusService:
    """Factory: construct a fully-wired service from configuration."""
    config.validate()
    clock = clock or SystemClock()
    metrics = Metrics()
    repository = create_repository(config)
    alert_manager = AlertManager(
        repository=repository,
        notifiers=create_notifiers(config.notifiers),
        evidence_writer=create_evidence_writer(config),
        metrics=metrics,
    )
    return ArgusService(
        config=config,
        source=create_source(config),
        vlm=create_vlm(config),
        decision_engine=DecisionEngine(config.decision, clock=clock),
        alert_manager=alert_manager,
        repository=repository,
        metrics=metrics,
        clock=clock,
    )
