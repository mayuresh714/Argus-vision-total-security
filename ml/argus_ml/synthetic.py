"""Synthetic CCTV-like videos to test the harness (not to prove anything about
real theft). Normal: slow wandering blobs. Event: one blob goes fast and
erratic and extra blobs appear."""
from pathlib import Path

import cv2
import numpy as np

from .manifest import Row


def make_video(path, site_seed, seed, secs=40, fps=8, event=None, size=(128, 96)):
    rng = np.random.default_rng(seed)
    bg_rng = np.random.default_rng(site_seed)
    w, h = size
    bg = (bg_rng.uniform(60, 180, 3) + bg_rng.normal(0, 6, (h, w, 3))).clip(0, 255).astype(np.uint8)
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    pos = rng.uniform([10, 10], [w - 10, h - 10], (3, 2))
    vel = rng.normal(0, 0.6, (3, 2))
    extra = rng.uniform([10, 10], [w - 10, h - 10], (3, 2))
    for f in range(secs * fps):
        t = f / fps
        in_ev = event is not None and event[0] <= t <= event[1]
        frame = bg.copy()
        pos += vel + rng.normal(0, 0.2, pos.shape)
        if in_ev:
            pos[0] += rng.normal(0, 6, 2)
            extra += rng.normal(0, 4, extra.shape)
        pos = pos.clip(5, [w - 5, h - 5])
        extra = extra.clip(5, [w - 5, h - 5])
        for i, p in enumerate(pos):
            cv2.circle(frame, tuple(int(v) for v in p), 6, (30 + 60 * i, 40, 200 - 50 * i), -1)
        if in_ev:
            for p in extra:
                cv2.circle(frame, tuple(int(v) for v in p), 5, (240, 240, 20), -1)
        noisy = (frame.astype(np.int16) + rng.normal(0, 3, frame.shape)).clip(0, 255).astype(np.uint8)
        vw.write(noisy)
    vw.release()


def make_dataset(out_dir, sites=5, normals_per_site=4, events_per_site=2):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows, n = [], 0
    for s in range(sites):
        for i in range(normals_per_site):
            p = out / f"site{s}_normal{i}.mp4"
            make_video(p, 1000 + s, n); n += 1
            rows.append(Row(str(p), "normal", f"site{s}", None, None, "synthetic", "n/a"))
        for i in range(events_per_site):
            ev = (14 + 4 * i, 24 + 4 * i)
            p = out / f"site{s}_event{i}.mp4"
            make_video(p, 1000 + s, n, event=ev); n += 1
            rows.append(Row(str(p), "theft", f"site{s}", ev[0], ev[1], "synthetic", "n/a"))
    return rows
