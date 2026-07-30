"""SQLite-backed Repository — zero-ops persistence for a single camera (docs/01 §4.6).

Uses the stdlib ``sqlite3`` with a connection guarded by a lock (v0 is a single
process with a couple of threads). Datetimes are stored as ISO-8601 UTC strings;
tags as JSON. Straightforward to migrate to Postgres at scale (Phase 3).
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime

from argus.domain import Alert, Event, Severity
from argus.storage.base import Repository

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    camera_id TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    score REAL NOT NULL,
    severity TEXT NOT NULL,
    reason TEXT NOT NULL,
    tags TEXT NOT NULL,
    model TEXT NOT NULL,
    vlm_latency_ms INTEGER NOT NULL,
    became_alert INTEGER NOT NULL,
    evidence_path TEXT,
    raw_model_output TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    camera_id TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    score REAL NOT NULL,
    severity TEXT NOT NULL,
    reason TEXT NOT NULL,
    tags TEXT NOT NULL,
    evidence_path TEXT,
    notified_channels TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);
"""


class SqliteRepository(Repository):
    def __init__(self, path: str) -> None:
        self._lock = threading.Lock()
        # check_same_thread=False because sampler/worker/API threads share it;
        # every access is serialised by our own lock.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ---- writes --------------------------------------------------------------

    def save_event(self, event: Event) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO events VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    event.id,
                    event.camera_id,
                    _iso(event.captured_at),
                    event.score,
                    event.severity.value,
                    event.reason,
                    json.dumps(list(event.tags)),
                    event.model,
                    event.vlm_latency_ms,
                    1 if event.became_alert else 0,
                    event.evidence_path,
                    event.raw_model_output,
                    _iso(event.created_at),
                ),
            )
            self._conn.commit()

    def save_alert(self, alert: Alert) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO alerts VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    alert.id,
                    alert.event_id,
                    alert.camera_id,
                    _iso(alert.captured_at),
                    alert.score,
                    alert.severity.value,
                    alert.reason,
                    json.dumps(list(alert.tags)),
                    alert.evidence_path,
                    json.dumps(list(alert.notified_channels)),
                    _iso(alert.created_at),
                ),
            )
            self._conn.commit()

    # ---- reads ---------------------------------------------------------------

    def list_events(self, *, limit: int = 100, camera_id: str | None = None) -> list[Event]:
        rows = self._query("events", limit, camera_id)
        return [_row_to_event(r) for r in rows]

    def list_alerts(self, *, limit: int = 100, camera_id: str | None = None) -> list[Alert]:
        rows = self._query("alerts", limit, camera_id)
        return [_row_to_alert(r) for r in rows]

    def get_event(self, event_id: str) -> Event | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        return _row_to_event(row) if row else None

    def get_alert(self, alert_id: str) -> Alert | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
        return _row_to_alert(row) if row else None

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---- helpers -------------------------------------------------------------

    def _query(self, table: str, limit: int, camera_id: str | None):
        sql = f"SELECT * FROM {table}"  # table is a fixed literal, not user input
        params: list[object] = []
        if camera_id is not None:
            sql += " WHERE camera_id=?"
            params.append(camera_id)
        sql += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            return self._conn.execute(sql, params).fetchall()


def _iso(ts: datetime) -> str:
    return ts.isoformat()


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _row_to_event(r: sqlite3.Row) -> Event:
    return Event(
        id=r["id"],
        camera_id=r["camera_id"],
        captured_at=_parse(r["captured_at"]),
        score=r["score"],
        severity=Severity(r["severity"]),
        reason=r["reason"],
        tags=tuple(json.loads(r["tags"])),
        model=r["model"],
        vlm_latency_ms=r["vlm_latency_ms"],
        became_alert=bool(r["became_alert"]),
        evidence_path=r["evidence_path"],
        raw_model_output=r["raw_model_output"],
        created_at=_parse(r["created_at"]),
    )


def _row_to_alert(r: sqlite3.Row) -> Alert:
    return Alert(
        id=r["id"],
        event_id=r["event_id"],
        camera_id=r["camera_id"],
        captured_at=_parse(r["captured_at"]),
        score=r["score"],
        severity=Severity(r["severity"]),
        reason=r["reason"],
        tags=tuple(json.loads(r["tags"])),
        evidence_path=r["evidence_path"],
        notified_channels=tuple(json.loads(r["notified_channels"])),
        created_at=_parse(r["created_at"]),
    )
