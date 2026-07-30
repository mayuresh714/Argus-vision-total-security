"""The debounce/hysteresis logic is trust-critical, so it gets the most tests."""

from argus.config import DecisionConfig
from argus.decision.engine import DecisionEngine
from argus.domain import Severity, SuspicionResult
from tests.fakes import FakeClock

CAM = "cam-01"


def _result(score: float) -> SuspicionResult:
    return SuspicionResult(score, "r", (), "mock", 1)


def _engine(clock=None, **overrides) -> DecisionEngine:
    cfg = DecisionConfig(**overrides)
    return DecisionEngine(cfg, clock=clock or FakeClock())


def test_severity_tiers():
    eng = _engine()
    assert eng.severity_for(0.1) is Severity.INFO
    assert eng.severity_for(0.5) is Severity.REVIEW
    assert eng.severity_for(0.75) is Severity.NOTIFY
    assert eng.severity_for(0.95) is Severity.URGENT


def test_below_threshold_never_alerts():
    eng = _engine()
    d = eng.evaluate(_result(0.3), CAM)
    assert d.should_alert is False
    assert d.suppressed_by == "below_threshold"


def test_single_over_threshold_alerts_when_consecutive_n_is_one():
    eng = _engine(consecutive_n=1)
    d = eng.evaluate(_result(0.8), CAM)
    assert d.should_alert is True
    assert d.severity is Severity.NOTIFY


def test_consecutive_n_requires_multiple_samples():
    eng = _engine(consecutive_n=3)
    assert eng.evaluate(_result(0.8), CAM).suppressed_by == "awaiting_consecutive"
    assert eng.evaluate(_result(0.8), CAM).suppressed_by == "awaiting_consecutive"
    assert eng.evaluate(_result(0.8), CAM).should_alert is True


def test_consecutive_counter_resets_below_clear_threshold():
    eng = _engine(consecutive_n=2, clear_threshold=0.4)
    assert eng.evaluate(_result(0.8), CAM).suppressed_by == "awaiting_consecutive"
    # A clearly-normal frame resets the run.
    assert eng.evaluate(_result(0.1), CAM).suppressed_by == "below_threshold"
    # So we must build the run up again from scratch.
    assert eng.evaluate(_result(0.8), CAM).suppressed_by == "awaiting_consecutive"
    assert eng.evaluate(_result(0.8), CAM).should_alert is True


def test_cooldown_suppresses_then_allows_after_window():
    clock = FakeClock()
    eng = _engine(clock=clock, consecutive_n=1, cooldown_seconds=60)

    assert eng.evaluate(_result(0.9), CAM).should_alert is True  # first fires
    clock.advance(30)
    assert eng.evaluate(_result(0.9), CAM).suppressed_by == "cooldown"  # within window
    clock.advance(31)  # now 61s since first alert
    assert eng.evaluate(_result(0.9), CAM).should_alert is True  # cooldown elapsed


def test_per_camera_state_is_isolated():
    eng = _engine(consecutive_n=2)
    assert eng.evaluate(_result(0.8), "a").suppressed_by == "awaiting_consecutive"
    # Different camera starts its own run, not inheriting camera "a".
    assert eng.evaluate(_result(0.8), "b").suppressed_by == "awaiting_consecutive"
