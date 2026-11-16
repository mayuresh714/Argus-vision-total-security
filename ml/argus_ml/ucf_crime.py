"""Build a manifest from a downloaded UCF-Crime tree.

UCF-Crime only has video-level labels (plus a temporal annotation file for the
test split), no site/camera ids. Each video therefore becomes its own pseudo
site, which means: use the `global` protocol and treat results as 'unseen
camera' generalisation, not per-site calibration.
"""
import re
from pathlib import Path

import cv2

from .manifest import Row

VIDEO_EXT = {".mp4", ".avi", ".mkv", ".mov"}


def _label_for(path):
    for part in reversed(path.parts[:-1]):
        low = part.lower()
        if "normal" in low:
            return "normal"
        if re.match(r"(anomaly[-_ ]?videos|training|testing|part)", low):
            continue
        return low.replace(" ", "_")
    return "unknown"


def parse_temporal(txt_path):
    """Lines like: `Abuse028_x264.mp4  Abuse  165  240  -1  -1` (frame indices;
    -1 = none). Format recalled from the dataset release: verify on your copy."""
    out = {}
    for line in Path(txt_path).read_text().splitlines():
        t = line.split()
        if len(t) >= 4 and t[2].lstrip("-").isdigit():
            a, b = int(t[2]), int(t[3])
            if a >= 0 and b >= 0:
                out[Path(t[0]).stem] = (a, b)
    return out


def build(root, temporal_txt=None):
    temporal = parse_temporal(temporal_txt) if temporal_txt else {}
    rows = []
    for p in sorted(Path(root).rglob("*")):
        if p.suffix.lower() not in VIDEO_EXT:
            continue
        label = _label_for(p)
        es = ee = None
        if p.stem in temporal:
            cap = cv2.VideoCapture(str(p)); fps = cap.get(cv2.CAP_PROP_FPS) or 30.0; cap.release()
            es, ee = temporal[p.stem][0] / fps, temporal[p.stem][1] / fps
        rows.append(Row(str(p.resolve()), label, f"{label}:{p.stem}", es, ee, "UCF-Crime",
                        "check original terms"))
    return rows
