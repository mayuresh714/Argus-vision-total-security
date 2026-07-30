import pytest

from argus.domain import AnalysisUnit, Frame, SuspicionResult, utcnow


def _frame(camera_id="cam-01"):
    return Frame(b"x", "image/jpeg", 10, 10, camera_id, utcnow())


def test_analysis_unit_requires_frames():
    with pytest.raises(ValueError):
        AnalysisUnit(frames=(), camera_id="c", captured_at=utcnow())


def test_analysis_unit_from_frame_sets_primary_and_metadata():
    f = _frame()
    unit = AnalysisUnit.from_frame(f)
    assert unit.primary is f
    assert unit.camera_id == "cam-01"
    assert len(unit.frames) == 1


def test_suspicion_result_rejects_out_of_range_score():
    with pytest.raises(ValueError):
        SuspicionResult(1.5, "r", (), "m", 1)
    with pytest.raises(ValueError):
        SuspicionResult(-0.1, "r", (), "m", 1)


def test_suspicion_result_accepts_bounds():
    assert SuspicionResult(0.0, "r", (), "m", 1).score == 0.0
    assert SuspicionResult(1.0, "r", (), "m", 1).score == 1.0
