import json

from argus.alerting.manager import AlertManager
from argus.alerting.notifiers import FileNotifier, WebhookNotifier
from argus.domain import AnalysisUnit, Event, Frame, Severity, utcnow
from argus.storage.evidence import NullEvidenceWriter
from argus.storage.memory_repository import InMemoryRepository
from tests.fakes import RecordingNotifier


def _event(score=0.9) -> Event:
    return Event(
        camera_id="cam-01",
        captured_at=utcnow(),
        score=score,
        severity=Severity.URGENT,
        reason="item concealed",
        tags=("concealment",),
        model="mock",
        vlm_latency_ms=5,
        became_alert=True,
    )


def _unit() -> AnalysisUnit:
    return AnalysisUnit.from_frame(Frame(b"x", "image/jpeg", 10, 10, "cam-01", utcnow()))


def test_file_notifier_writes_jsonl(tmp_path):
    path = tmp_path / "alerts.jsonl"
    repo = InMemoryRepository()
    mgr = AlertManager(
        repository=repo,
        notifiers=[FileNotifier(str(path))],
        evidence_writer=NullEvidenceWriter(),
    )
    mgr.raise_alert(_event(), _unit())
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["reason"] == "item concealed"
    assert record["severity"] == "urgent"


def test_webhook_notifier_posts_payload():
    posted = {}

    def poster(url, payload, timeout):
        posted["url"] = url
        posted["payload"] = payload

    n = WebhookNotifier("https://hook.example", poster=poster)
    repo = InMemoryRepository()
    AlertManager(
        repository=repo, notifiers=[n], evidence_writer=NullEvidenceWriter()
    ).raise_alert(_event(), _unit())
    assert posted["url"] == "https://hook.example"
    assert posted["payload"]["score"] == 0.9


def test_manager_records_delivered_channels_and_persists_alert():
    repo = InMemoryRepository()
    rec = RecordingNotifier(channel="rec")
    mgr = AlertManager(repository=repo, notifiers=[rec], evidence_writer=NullEvidenceWriter())
    alert = mgr.raise_alert(_event(), _unit())
    assert alert.notified_channels == ("rec",)
    assert len(rec.delivered) == 1
    assert repo.get_alert(alert.id) is not None


def test_failing_notifier_is_isolated_and_others_still_fire():
    repo = InMemoryRepository()
    bad = RecordingNotifier(channel="bad", fail=True)
    good = RecordingNotifier(channel="good")
    mgr = AlertManager(
        repository=repo,
        notifiers=[bad, good],
        evidence_writer=NullEvidenceWriter(),
        max_notify_retries=1,
    )
    alert = mgr.raise_alert(_event(), _unit())
    # bad failed (and was retried), good still delivered; alert still persisted.
    assert alert.notified_channels == ("good",)
    assert bad.attempts == 2  # 1 try + 1 retry
    assert len(good.delivered) == 1
