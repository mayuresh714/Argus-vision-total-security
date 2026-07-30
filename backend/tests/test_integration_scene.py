"""End-to-end scene replay through the real wiring (sampler + slot + worker +
decision + alert manager + repository), driven synchronously for determinism.

This is the v0 acceptance test from docs/01 §11: feed a source with known
"normal" and "theft" segments and assert alerts fire on the latter, debounced.
"""

from argus.alerting.manager import AlertManager
from argus.config import DecisionConfig
from argus.decision.engine import DecisionEngine
from argus.pipeline.latest_slot import LatestSlot
from argus.pipeline.sampler import Sampler
from argus.pipeline.worker import InferenceWorker
from argus.sources.fake_source import FakeSource
from argus.storage.evidence import NullEvidenceWriter
from argus.storage.memory_repository import InMemoryRepository
from argus.vlm.mock_backend import MockVlmBackend
from tests.fakes import FakeClock, RecordingNotifier


def _replay(scene_scores, *, decision_cfg):
    """Wire the real pipeline and push each frame through synchronously,
    returning (events, alerts, notifier)."""
    clock = FakeClock()
    frames = [FakeSource.solid_frame("cam-01") for _ in scene_scores]
    source = FakeSource(frames)
    source.open()
    slot = LatestSlot()
    repo = InMemoryRepository()
    rec = RecordingNotifier(channel="rec")

    sampler = Sampler(source=source, slot=slot, interval_seconds=5.0, clock=clock)
    worker = InferenceWorker(
        slot=slot,
        vlm=MockVlmBackend(scores=scene_scores),
        decision_engine=DecisionEngine(decision_cfg, clock=clock),
        alert_manager=AlertManager(
            repository=repo, notifiers=[rec], evidence_writer=NullEvidenceWriter()
        ),
        repository=repo,
    )

    while True:
        unit = sampler.sample_once()
        if unit is None:
            break
        worker.process(slot.get(timeout=0.1))
        clock.advance(5.0)  # simulate k seconds passing between samples

    return repo.list_events(limit=100), repo.list_alerts(limit=100), rec


def test_theft_segment_alerts_and_normal_does_not():
    # normal, normal, THEFT, THEFT, normal, normal
    scene = [0.1, 0.2, 0.85, 0.9, 0.15, 0.1]
    cfg = DecisionConfig(alert_threshold=0.7, consecutive_n=1, cooldown_seconds=60)
    events, alerts, rec = _replay(scene, decision_cfg=cfg)

    assert len(events) == 6  # every sample recorded
    # cooldown=60s > k=5s, so the two adjacent theft frames collapse to ONE alert
    assert len(alerts) == 1
    assert len(rec.delivered) == 1
    assert rec.delivered[0].score == 0.85  # first over-threshold frame fired it


def test_two_separated_incidents_fire_twice():
    # theft ... long gap of normal ... theft again
    scene = [0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.9]
    # cooldown 20s; k=5s. 12 normal samples = 60s > cooldown, so 2nd theft re-fires.
    cfg = DecisionConfig(alert_threshold=0.7, consecutive_n=1, cooldown_seconds=20)
    _events, alerts, _rec = _replay(scene, decision_cfg=cfg)
    assert len(alerts) == 2


def test_all_normal_scene_is_silent():
    scene = [0.1, 0.2, 0.3, 0.25, 0.1]
    cfg = DecisionConfig(alert_threshold=0.7)
    events, alerts, rec = _replay(scene, decision_cfg=cfg)
    assert len(events) == 5
    assert alerts == []
    assert rec.delivered == []
