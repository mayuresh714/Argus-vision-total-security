import pytest

from argus.domain import Alert, Event, Severity, utcnow
from argus.storage.evidence import FileEvidenceWriter
from argus.storage.memory_repository import InMemoryRepository
from argus.storage.sqlite_repository import SqliteRepository
from argus.domain import Frame


def _event(camera_id="cam-01", score=0.5) -> Event:
    return Event(
        camera_id=camera_id,
        captured_at=utcnow(),
        score=score,
        severity=Severity.REVIEW,
        reason="r",
        tags=("a", "b"),
        model="mock",
        vlm_latency_ms=7,
    )


def _alert(event: Event) -> Alert:
    return Alert(
        event_id=event.id,
        camera_id=event.camera_id,
        captured_at=event.captured_at,
        score=event.score,
        severity=event.severity,
        reason=event.reason,
        tags=event.tags,
        notified_channels=("console",),
    )


@pytest.fixture(params=["memory", "sqlite"])
def repo(request, tmp_path):
    if request.param == "memory":
        yield InMemoryRepository()
    else:
        r = SqliteRepository(str(tmp_path / "t.db"))
        yield r
        r.close()


def test_event_roundtrip(repo):
    e = _event()
    repo.save_event(e)
    got = repo.get_event(e.id)
    assert got is not None
    assert got.reason == "r"
    assert got.tags == ("a", "b")
    assert got.severity is Severity.REVIEW


def test_alert_roundtrip(repo):
    e = _event()
    repo.save_event(e)
    a = _alert(e)
    repo.save_alert(a)
    got = repo.get_alert(a.id)
    assert got is not None
    assert got.notified_channels == ("console",)


def test_list_events_most_recent_first_and_limit(repo):
    for i in range(5):
        repo.save_event(_event(score=i / 10))
    events = repo.list_events(limit=3)
    assert len(events) == 3
    # Most recent (last saved, score 0.4) comes first.
    assert events[0].score == pytest.approx(0.4)


def test_list_filters_by_camera(repo):
    repo.save_event(_event(camera_id="a"))
    repo.save_event(_event(camera_id="b"))
    assert len(repo.list_events(camera_id="a")) == 1


def test_missing_ids_return_none(repo):
    assert repo.get_event("nope") is None
    assert repo.get_alert("nope") is None


def test_file_evidence_writer(tmp_path):
    w = FileEvidenceWriter(str(tmp_path))
    frame = Frame(b"jpegbytes", "image/jpeg", 10, 10, "cam-01", utcnow())
    path = w.write(frame, event_id="abcd1234ef")
    assert path is not None
    with open(path, "rb") as fh:
        assert fh.read() == b"jpegbytes"
