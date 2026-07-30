"""Worker unit tests: one unit in, correct Event/Alert out — no threads."""

from argus.alerting.manager import AlertManager
from argus.config import DecisionConfig
from argus.decision.engine import DecisionEngine
from argus.domain import AnalysisUnit, Frame, utcnow
from argus.pipeline.latest_slot import LatestSlot
from argus.pipeline.worker import InferenceWorker
from argus.storage.evidence import NullEvidenceWriter
from argus.storage.memory_repository import InMemoryRepository
from argus.vlm.mock_backend import MockVlmBackend
from tests.fakes import FakeClock, RecordingNotifier


def _unit() -> AnalysisUnit:
    return AnalysisUnit.from_frame(Frame(b"x", "image/jpeg", 10, 10, "cam-01", utcnow()))


def _build(vlm, *, consecutive_n=1):
    repo = InMemoryRepository()
    rec = RecordingNotifier(channel="rec")
    engine = DecisionEngine(
        DecisionConfig(alert_threshold=0.7, consecutive_n=consecutive_n), clock=FakeClock()
    )
    mgr = AlertManager(repository=repo, notifiers=[rec], evidence_writer=NullEvidenceWriter())
    worker = InferenceWorker(
        slot=LatestSlot(),
        vlm=vlm,
        decision_engine=engine,
        alert_manager=mgr,
        repository=repo,
    )
    return worker, repo, rec


def test_low_score_records_event_but_no_alert():
    worker, repo, rec = _build(MockVlmBackend(scores=[0.2]))
    event = worker.process(_unit())
    assert event is not None
    assert event.became_alert is False
    assert repo.list_events()[0].score == 0.2
    assert rec.delivered == []


def test_high_score_records_event_and_alert():
    worker, repo, rec = _build(MockVlmBackend(scores=[0.95]))
    event = worker.process(_unit())
    assert event.became_alert is True
    assert len(repo.list_alerts()) == 1
    assert len(rec.delivered) == 1
    assert rec.delivered[0].reason == event.reason


def test_vlm_error_skips_sample_gracefully():
    worker, repo, rec = _build(MockVlmBackend(scores=[0.9], raise_on=0))
    event = worker.process(_unit())
    assert event is None  # skipped, not crashed
    assert repo.list_events() == []
    assert rec.delivered == []


def test_consecutive_n_delays_alert_across_units():
    worker, repo, rec = _build(MockVlmBackend(scores=[0.9, 0.9], loop=True), consecutive_n=2)
    worker.process(_unit())
    assert len(repo.list_alerts()) == 0  # first over-threshold: awaiting
    worker.process(_unit())
    assert len(repo.list_alerts()) == 1  # second: fires
