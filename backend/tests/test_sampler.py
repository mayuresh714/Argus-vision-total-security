from argus.domain import AnalysisUnit
from argus.metrics import Metrics
from argus.pipeline.latest_slot import LatestSlot
from argus.pipeline.sampler import Sampler
from argus.sources.fake_source import FakeSource
from tests.fakes import FakeClock


def _sampler(frames, interval=5.0):
    source = FakeSource(frames)
    source.open()
    slot: LatestSlot[AnalysisUnit] = LatestSlot()
    metrics = Metrics()
    s = Sampler(
        source=source,
        slot=slot,
        interval_seconds=interval,
        metrics=metrics,
        clock=FakeClock(),
    )
    return s, slot, metrics


def test_sample_once_enqueues_frame():
    frame = FakeSource.solid_frame("cam-01")
    s, slot, metrics = _sampler([frame])
    unit = s.sample_once()
    assert unit is not None
    assert unit.camera_id == "cam-01"
    assert slot.get(timeout=0.1) is unit
    assert metrics.snapshot()["counters"]["frames_sampled"] == 1


def test_sample_once_returns_none_at_eof():
    s, slot, _ = _sampler([])
    assert s.sample_once() is None


def test_run_drains_finite_source_and_stops():
    frames = [FakeSource.solid_frame("cam-01") for _ in range(3)]
    s, slot, metrics = _sampler(frames, interval=0.0)
    s.run()  # finite FakeSource -> EOF stops the loop
    assert metrics.snapshot()["counters"]["frames_sampled"] == 3
