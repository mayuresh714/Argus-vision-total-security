"""Manifest: one CSV row per video.

columns: video_path,label,site_id,event_start,event_end,source,license
- label: `normal` or a class name (theft, robbery, burglary, snatching, ...)
- site_id: camera/site the footage came from. Test splits are made by site.
- event_start/event_end: seconds; leave blank if you only know the video
  contains an event (weak label).
"""
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Row:
    video_path: str
    label: str
    site_id: str
    event_start: float | None
    event_end: float | None
    source: str = ""
    license: str = ""

    @property
    def is_normal(self):
        return self.label.lower() == "normal"


def _f(x):
    x = (x or "").strip()
    return float(x) if x else None


def load_manifest(path):
    base = Path(path).parent
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            p = Path(r["video_path"])
            rows.append(
                Row(
                    video_path=str(p if p.is_absolute() else base / p),
                    label=r["label"].strip(),
                    site_id=r["site_id"].strip(),
                    event_start=_f(r.get("event_start")),
                    event_end=_f(r.get("event_end")),
                    source=r.get("source", ""),
                    license=r.get("license", ""),
                )
            )
    return rows


def write_manifest(rows, path):
    cols = ["video_path", "label", "site_id", "event_start", "event_end", "source", "license"]
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([r.video_path, r.label, r.site_id,
                        "" if r.event_start is None else r.event_start,
                        "" if r.event_end is None else r.event_end, r.source, r.license])
